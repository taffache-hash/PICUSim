"""
Ventilator Waveforms
====================
Classi di forma d'onda per ogni modalità ventilatoria.
Ogni classe espone:
  compute(t_phase, T_insp, T_exp, params, patient) → (Paw, Flow_target)

dove:
  t_phase  : tempo nella fase corrente del ciclo [s]
  T_insp   : durata inspirazione [s]
  T_exp    : durata espirazione [s]
  params   : dict parametri ventilatore
  patient  : dict stato paziente (C_rs, R_rs, V_current, Pmus)

Output:
  Paw          : pressione vie aeree [cmH2O]
  Flow_target  : flow target [mL/s] (None = pressure-driven, flow calcolato dall'equazione del moto)

Fisica di riferimento:
  Equazione del moto: Paw + Pmus = E·V + R·dV/dt
  dove E = 1/C_rs [cmH2O/mL], R = R_rs/1000 [cmH2O·s/mL]
"""

from __future__ import annotations
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple


PatientState = Dict[str, float]   # {C_rs, R_rs, V_current, Pmus, PEEP}


class VentilatorWaveform(ABC):
    """Classe base per tutte le modalità ventilatorie."""

    @abstractmethod
    def compute_inspiratory(
        self,
        t_phase: float,          # tempo nella fase inspiratoria [s]
        T_insp: float,           # durata totale inspirazione [s]
        patient: PatientState,
        params: Dict[str, Any],
    ) -> Tuple[float, Optional[float]]:
        """
        Restituisce (Paw_eff, Flow_target) durante l'inspirazione.
        Flow_target=None → pressure-driven (calcolo implicito).
        """
        ...

    def compute_expiratory(
        self,
        t_phase: float,
        T_exp: float,
        patient: PatientState,
        params: Dict[str, Any],
    ) -> Tuple[float, Optional[float]]:
        """
        Default espirazione: Paw = PEEP (espirazione passiva).
        """
        return float(params.get("PEEP", 5.0)), None


# ---------------------------------------------------------------------------
# VCV — Volume Controlled Ventilation
# ---------------------------------------------------------------------------

class VCVWaveform(VentilatorWaveform):
    """
    Volume Controllato con flow quadra (square wave).

    Fisica:
      Q_insp = Vt / T_insp   (costante per tutta l'inspirazione)
      V(t)   = Q_insp × t    (rampa lineare)
      Paw(t) = PEEP + Q·R + V(t)·E    (resistivo + elastico)

    Con pausa inspiratoria (T_pause > 0):
      Flow = 0 durante la pausa
      Paw = Pplat = PEEP + Vt·E       (solo elastico → misura compliance)

    Variante flow decelerante (ramp):
      Q(t) = Q_peak × (1 - t/T_insp)
      V(t) = Q_peak × t × (1 - t/(2·T_insp))
    """

    def compute_inspiratory(self, t_phase, T_insp, patient, params):
        Vt      = float(params["Vt_set_mL"])
        PEEP    = float(params.get("PEEP", 5.0))
        T_pause = float(params.get("T_pause_s", 0.0))
        flow_shape = params.get("flow_shape", "square")   # "square" | "ramp"
        C_rs    = float(patient.get("C_rs", 10.0))
        R_rs    = float(patient.get("R_rs", 10.0))

        E = 1.0 / (C_rs + 1e-9)       # cmH2O/mL
        R = R_rs / 1000.0              # cmH2O·s/mL

        T_insp_flow = max(T_insp - T_pause, 0.01)

        if t_phase < T_insp_flow:
            # Fase di flusso
            if flow_shape == "ramp":
                # Flow decelerante: Q(t) = Q_peak × (1 - t/T_insp_flow)
                Q_peak = 2 * Vt / T_insp_flow   # per conservare il volume
                Q = Q_peak * max(1.0 - t_phase / T_insp_flow, 0.0)
                V  = Q_peak * t_phase * (1.0 - t_phase / (2 * T_insp_flow))
            else:
                # Square wave
                Q = Vt / T_insp_flow
                V = Q * t_phase

            Paw = PEEP + Q * R + V * E
            return float(Paw), float(Q)

        else:
            # Pausa inspiratoria: flow = 0, Paw = Pplat
            Pplat = PEEP + Vt * E
            return float(Pplat), 0.0


# ---------------------------------------------------------------------------
# PCV — Pressure Controlled Ventilation
# ---------------------------------------------------------------------------

class PCVWaveform(VentilatorWaveform):
    """
    Pressione Controllata con pressione a gradino (square pressure).

    Fisica:
      Paw(t) = PEEP + Pinsp   durante T_insp (rise time incluso)
      V(t)   = (Paw-PEEP)/E × (1 - exp(-t/τ))
      Vt     = Pdriving × C_rs × (1 - exp(-T_insp/τ))

    Con rise time (T_rise):
      Paw(t) = PEEP + Pinsp × (t/T_rise)   per t < T_rise
      Paw(t) = PEEP + Pinsp                 per t ≥ T_rise
    """

    def compute_inspiratory(self, t_phase, T_insp, patient, params):
        Pinsp  = float(params.get("Pinsp_cmH2O", 20.0))
        PEEP   = float(params.get("PEEP", 5.0))
        T_rise = float(params.get("T_rise_s", 0.1))

        if t_phase < T_rise:
            ramp = t_phase / T_rise
            Paw_eff = PEEP + Pinsp * ramp
        else:
            Paw_eff = PEEP + Pinsp

        return float(Paw_eff), None   # pressure-driven → flow calcolato esternamente

    def expiratory_Paw(self, params):
        return float(params.get("PEEP", 5.0))


# ---------------------------------------------------------------------------
# PSV — Pressure Support Ventilation
# ---------------------------------------------------------------------------

class PSVWaveform(VentilatorWaveform):
    """
    Pressure Support: triggerata dal paziente, ciclata su flow.

    Trigger (pressure):
      paziente abbassa Paw < PEEP - trigger_thresh [cmH2O]
      → ventilatore eroga PS

    Cycling (flow):
      quando Flow < cycling_frac × Flow_peak → end inspiration
      di default cycling_frac = 0.25 (25% del picco)
      Max safety: T_insp_max limita durata massima

    Pressione erogata:
      Paw = PEEP + PS × sigmoid(t/T_rise)   (rampa sigmoide)
    """

    def __init__(self):
        self._flow_peak: float = 0.0
        self._triggered: bool  = False

    def check_trigger(self, Pmus: float, Paw_current: float,
                      PEEP: float, thresh: float) -> bool:
        """
        Verifica il trigger.
        Pressure trigger: paziente genera sforzo → Pmus > thresh
        Flow trigger: non implementato qui (richiede flow sensor separato)
        """
        # Pmus > trigger_thresh → paziente inspira
        return float(Pmus) > float(thresh)

    def check_cycling(self, flow_current: float, cycling_frac: float) -> bool:
        """Termina inspirazione quando flow < cycling_frac × peak."""
        if self._flow_peak > 0.1:
            return flow_current < cycling_frac * self._flow_peak
        return False

    def compute_inspiratory(self, t_phase, T_insp, patient, params):
        PS      = float(params.get("PS_cmH2O", 10.0))
        PEEP    = float(params.get("PEEP", 5.0))
        T_rise  = float(params.get("T_rise_s", 0.1))

        # Rampa di pressione
        ramp   = float(np.clip(t_phase / T_rise, 0.0, 1.0))
        Paw    = PEEP + PS * ramp

        return float(Paw), None   # flow dalla equazione del moto

    def update_peak_flow(self, flow: float) -> None:
        if flow > self._flow_peak:
            self._flow_peak = flow

    def reset_cycle(self) -> None:
        self._flow_peak = 0.0
        self._triggered = False


# ---------------------------------------------------------------------------
# CPAP — Continuous Positive Airway Pressure
# ---------------------------------------------------------------------------

class CPAPWaveform(VentilatorWaveform):
    """
    CPAP: pressione costante, nessun supporto aggiuntivo.
    Paziente respira spontaneamente con CPAP come baseline.
    Paw = CPAP = PEEP durante tutto il ciclo.
    """

    def compute_inspiratory(self, t_phase, T_insp, patient, params):
        CPAP = float(params.get("PEEP", 5.0))
        return CPAP, None

    def compute_expiratory(self, t_phase, T_exp, patient, params):
        CPAP = float(params.get("PEEP", 5.0))
        return CPAP, None


# ---------------------------------------------------------------------------
# HFOV — High Frequency Oscillatory Ventilation
# ---------------------------------------------------------------------------

class HFOVWaveform(VentilatorWaveform):
    """
    HFOV: oscillazioni sinusoidali ad alta frequenza attorno a MAP.

    Fisica:
      Paw(t) = MAP + (Amplitude/2) × sin(2π × f × t)
      Vt_osc = (Amplitude/2) × C_rs × η(f)   [piccolo]
      dove η(f) = 1/sqrt(1 + (2πf·τ_mech)²)  (filtro passa-basso)

      Meccanismo di scambio gassoso in HFOV:
        - Diffusione asimmetrica (Pendelluft)
        - Taylor dispersion
        - Convezione asimmetrica
        → approssimato qui come VA_eff = frequenza × Vt_osc × k_hfov

    Non ha fasi ins/esp distinte → override dell'interfaccia.
    """

    def compute_inspiratory(self, t_phase, T_insp, patient, params):
        MAP_hfov  = float(params.get("MAP_hfov", 18.0))
        amplitude = float(params.get("HFOV_amplitude", 30.0))
        freq_hz   = float(params.get("HFOV_freq_Hz", 10.0))
        C_rs      = float(patient.get("C_rs", 10.0))
        R_rs      = float(patient.get("R_rs", 10.0))
        tau_mech  = R_rs / 1000 * C_rs

        # Oscillazione sinusoidale
        omega = 2 * np.pi * freq_hz
        # t_phase qui è il tempo assoluto (usato per l'oscillazione)
        Paw = MAP_hfov + (amplitude / 2) * np.sin(omega * t_phase)
        return float(Paw), None

    def compute_expiratory(self, t_phase, T_exp, patient, params):
        # In HFOV non c'è distinzione insp/esp → stesso calcolo
        return self.compute_inspiratory(t_phase, 0.0, patient, params)

    @staticmethod
    def effective_VA(freq_hz: float, amplitude: float,
                     C_rs: float, R_rs: float) -> float:
        """
        Ventilazione alveolare efficace approssimata in HFOV [mL/s].
        Basata su: Slutsky 1981, Permutt 1985.
        """
        tau = R_rs / 1000 * C_rs
        omega = 2 * np.pi * freq_hz
        eta = 1.0 / np.sqrt(1 + (omega * tau) ** 2)
        Vt_osc = (amplitude / 2) * C_rs * eta
        # k_hfov ≈ 0.4 (fattore empirico: non tutto Vt_osc contribuisce)
        VA_eff = freq_hz * Vt_osc * 0.4
        return float(VA_eff)

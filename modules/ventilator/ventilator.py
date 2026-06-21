"""
VentilatorModule
================
Modulo ventilatore completo con 5 modalità ventilatorie.

Modalità implementate:
  VCV  — Volume Controlled Ventilation (flow quadra o ramp decelerante)
  PCV  — Pressure Controlled Ventilation (default corrente → rinominato da PC)
  PSV  — Pressure Support Ventilation (trigger paziente + cycling flow)
  SIMV — Synchronized IMV (atti mandatori VCV/PCV + spontanei PSV)
  CPAP — Continuous Positive Airway Pressure (solo spontaneo)
  HFOV — High Frequency Oscillatory Ventilation
  NONE/UNASSISTED — no active ventilator pressure; spontaneous Pmus-only breathing

Architettura:
  Il modulo gestisce:
    1. Macchina a stati del ciclo respiratorio (insp/esp/pausa/trigger_wait)
    2. Forma d'onda Paw(t) per la modalità selezionata
    3. Trigger paziente (pressure trigger su Pmus)
    4. Cycling criterion (PSV: flow < 25% picco)
    5. Protezioni di sicurezza (Ppeak max, Vt max)
    6. Auto-PEEP (PEEP intrinseca da espirazione incompleta)
    7. Allarmi: Ppeak, Vt, RR, Apnea, Pplat
    8. Metriche monitoraggio: compliance dinamica, resistenza, WOB

Il modulo scrive Paw nel Bus → RespiratoryMechanicsModule la usa
per calcolare V(t) via equazione del moto.
"""

from __future__ import annotations
import numpy as np
from typing import List, Dict, Any
from enum import Enum, auto

from core.base_module import BaseModule
from core.bus import PhysiologicalBus
from .waveforms import (VCVWaveform, PCVWaveform, PSVWaveform,
                        CPAPWaveform, HFOVWaveform)


# ---------------------------------------------------------------------------
# Stati del ciclo respiratorio
# ---------------------------------------------------------------------------

class CyclePhase(Enum):
    INSP          = auto()   # inspirazione attiva
    INSP_PAUSE    = auto()   # pausa inspiratoria (misura Pplat)
    EXP           = auto()   # espirazione
    TRIGGER_WAIT  = auto()   # attesa trigger paziente (PSV/CPAP)


class VentMode(Enum):
    VCV  = "VCV"
    PCV  = "PCV"
    PSV  = "PSV"
    SIMV = "SIMV"
    CPAP = "CPAP"
    HFOV = "HFOV"
    NONE = "NONE"
    UNASSISTED = "UNASSISTED"


# ---------------------------------------------------------------------------
# Modulo principale
# ---------------------------------------------------------------------------

class VentilatorModule(BaseModule):
    """
    Ventilatore meccanico multi-modalità.

    Parametri principali
    --------------------
    mode : str
        Modalità: VCV | PCV | PSV | SIMV | CPAP | HFOV | NONE | UNASSISTED
    RR : float
        Frequenza respiratoria impostata [atti/min]
    Vt_set_mL : float
        Volume tidal impostato (VCV) [mL]
    Pinsp_cmH2O : float
        Pressione inspiratoria (PCV) [cmH2O]
    PS_cmH2O : float
        Pressure Support (PSV/SIMV) [cmH2O]
    PEEP : float
        PEEP [cmH2O]
    FiO2 : float
        FiO2 [0-1]
    IE_ratio : float
        Rapporto I:E (default 0.5 → 1:2)
    T_rise_s : float
        Rise time [s] (default 0.08)
    T_pause_s : float
        Pausa inspiratoria [s] (default 0.0)
    trigger_thresh : float
        Soglia trigger pressure [cmH2O] (default 2.0)
    cycling_frac : float
        PSV cycling threshold (default 0.25)
    flow_shape : str
        VCV flow shape: "square" | "ramp" (default "square")

    SIMV-specifici:
    RR_set : float
        RR mandatoria in SIMV [atti/min]

    HFOV-specifici:
    HFOV_freq_Hz : float
        Frequenza oscillazioni [Hz] (default 10)
    HFOV_amplitude : float
        Ampiezza [cmH2O] (default 30)
    MAP_hfov : float
        Pressione media [cmH2O] (default 18)

    Allarmi (limiti di sicurezza):
    alarm_Ppeak_max : float    [cmH2O] (default 45)
    alarm_Vt_min    : float    [mL]    (default 50)
    alarm_Vt_max    : float    [mL]    (default auto: 12 mL/kg)
    alarm_RR_max    : float    [/min]  (default 80)
    alarm_apnea_s   : float    [s]     (default 20)
    """

    DEFAULT_PARAMS = {
        "mode":             "PCV",
        "RR":               25.0,
        "Vt_set_mL":        150.0,    # mL (per VCV; scalato per peso in initialize)
        "Pinsp_cmH2O":      20.0,     # cmH2O (PCV)
        "PS_cmH2O":         10.0,     # cmH2O (PSV)
        "PEEP":              5.0,
        "FiO2":              0.30,
        "IE_ratio":          0.50,    # TI/(TI+TE) → 0.33=1:2, 0.5=1:1
        "T_rise_s":          0.08,    # s
        "T_pause_s":         0.0,     # s (pausa inspiratoria per Pplat)
        "trigger_thresh":    2.0,     # cmH2O (Pmus minima per trigger)
        "cycling_frac":      0.25,    # PSV cycling threshold
        "flow_shape":       "square", # VCV: "square" | "ramp"
        # SIMV
        "RR_set":           15.0,     # atti mandatori/min
        # HFOV
        "HFOV_freq_Hz":     10.0,
        "HFOV_amplitude":   30.0,
        "MAP_hfov":         18.0,
        # Allarmi
        "alarm_Ppeak_max":  45.0,
        "alarm_Vt_min":     30.0,
        "alarm_Vt_max":     500.0,
        "alarm_RR_max":     80.0,
        "alarm_apnea_s":    20.0,
        # Peso paziente (per scaling automatico Vt in initialize)
        "weight_kg":        20.0,
    }

    def __init__(self, params: dict | None = None):
        merged = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(name="Ventilator", params=merged)

        # Stato ciclo
        self._phase:        CyclePhase = CyclePhase.EXP
        self._t_phase:      float = 0.0    # tempo nella fase corrente [s]
        self._t_abs:        float = 0.0    # tempo assoluto [s]
        self._T_insp:       float = 0.0    # durata inspirazione [s]
        self._T_exp:        float = 0.0    # durata espirazione [s]
        self._T_pause:      float = 0.0    # durata pausa [s]

        # Waveform objects
        self._waveform_vcv  = VCVWaveform()
        self._waveform_pcv  = PCVWaveform()
        self._waveform_psv  = PSVWaveform()
        self._waveform_cpap = CPAPWaveform()
        self._waveform_hfov = HFOVWaveform()

        # Tracciamento ciclo
        self._Ppeak:        float = 0.0
        self._Pplat:        float = 0.0
        self._Vt_measured:  float = 0.0
        self._V_at_insp_start: float = 0.0
        self._flow_current: float = 0.0
        self._flow_prev:    float = 0.0
        self._auto_PEEP:    float = 0.0
        self._V_at_exp_start: float = 0.0
        self._compliance_dyn: float = 0.0
        self._resistance_meas: float = 0.0

        # Contatori cicli
        self._breath_count:     int = 0
        self._triggered_breaths: int = 0
        self._t_last_breath:    float = -999.0  # per apnea alarm

        # SIMV: gestione atti mandatori vs spontanei
        self._next_mandatory_t: float = 0.0
        self._in_mandatory:     bool  = False

        # Allarmi attivi
        self._alarms: Dict[str, bool] = {
            "Ppeak_high":    False,
            "Vt_low":        False,
            "Vt_high":       False,
            "RR_high":       False,
            "apnea":         False,
            "circuit_disc":  False,
        }

    # ------------------------------------------------------------------
    # Proprietà
    # ------------------------------------------------------------------

    @property
    def input_keys(self) -> List[str]:
        return ["Pmus", "V_lung", "C_rs", "R_rs", "PEEP",
                "drug_NMB_frac", "auto_PEEP_obstructive"]

    @property
    def output_keys(self) -> List[str]:
        return [
            "Paw", "Paw_current", "Flow_current_mL_s",
            "Ppeak", "Pplat", "auto_PEEP",
            "patient_triggered", "RR_total", "MV_L_min",
            "compliance_dyn", "resistance_meas",
            "vent_mode", "alarm_active",
        ]

    # ------------------------------------------------------------------
    # Initialize
    # ------------------------------------------------------------------

    def initialize(self, bus: PhysiologicalBus) -> None:
        wt   = self.params["weight_kg"]
        mode_name = str(self.params["mode"]).upper()
        if mode_name not in {m.value for m in VentMode}:
            mode_name = "PCV"
        self.params["mode"] = mode_name
        mode = VentMode(mode_name)

        # Aggiorna PEEP e FiO2 dal bus se lo scenario li ha impostati
        bus_PEEP = bus.get("PEEP")
        bus_FiO2 = bus.get("FiO2")
        if bus_PEEP:
            self.params["PEEP"] = bus_PEEP
        if bus_FiO2:
            self.params["FiO2"] = bus_FiO2

        # Auto-scaling Vt per VCV (6 mL/kg se non specificato in modo assoluto)
        if self.params["Vt_set_mL"] < 50 and wt > 0:
            self.params["Vt_set_mL"] = 6.0 * wt

        # Calcola TI e TE da RR e IE_ratio
        self._update_timing()

        # Stato iniziale: fine espirazione (pronto per nuovo ciclo)
        self._phase = CyclePhase.EXP
        self._t_phase = self._T_exp   # inizia immediatamente un nuovo ciclo
        self._next_mandatory_t = 0.0

        init_paw = 0.0 if self.params["mode"] in ("NONE", "UNASSISTED") else float(self.params["PEEP"])
        if self.params["mode"] in ("NONE", "UNASSISTED"):
            bus.set("PEEP", 0.0)
        bus.update({
            "Paw":               init_paw,
            "Paw_current":       init_paw,
            "Paw_mean":          init_paw,
            "Paw_display":       init_paw,
            "Flow_current_mL_s": 0.0,
            "Ppeak":             0.0,
            "Pplat":             0.0,
            "auto_PEEP":         0.0,
            "patient_triggered": False,
            "RR_total":          float(self.params["RR"]),
            "MV_L_min":          0.0,
            "compliance_dyn":    0.0,
            "resistance_meas":   0.0,
            "vent_mode":         "NONE" if self.params["mode"] == "UNASSISTED" else self.params["mode"],
            "alarm_active":      False,
        })

    # ------------------------------------------------------------------
    # Timing
    # ------------------------------------------------------------------

    def _update_timing(self) -> None:
        """Ricalcola TI e TE da RR e IE_ratio."""
        RR     = max(float(self.params["RR"]), 1.0)
        IE_r   = float(np.clip(self.params["IE_ratio"], 0.1, 0.9))
        T_tot  = 60.0 / RR
        self._T_insp  = T_tot * IE_r
        self._T_pause = float(self.params.get("T_pause_s", 0.0))
        self._T_exp   = T_tot * (1.0 - IE_r) - self._T_pause
        self._T_exp   = max(self._T_exp, 0.1)

    # ------------------------------------------------------------------
    # Trigger paziente
    # ------------------------------------------------------------------

    def _patient_triggered(self, Pmus: float, NMB_frac: float) -> bool:
        """
        Trigger pressure: true only if motor effort is available.
        Step 3.5 contract: neuromuscular blockade blocks patient triggering; it
        does not improve gas exchange by itself.
        """
        if NMB_frac >= 0.9:
            return False   # paziente paralizzato → no trigger
        return float(Pmus) > float(self.params["trigger_thresh"])

    # ------------------------------------------------------------------
    # HFOV: ventilazione alveolare effettiva
    # ------------------------------------------------------------------

    def _hfov_VA(self) -> float:
        return HFOVWaveform.effective_VA(
            self.params["HFOV_freq_Hz"],
            self.params["HFOV_amplitude"],
            self._patient_C_rs,
            self._patient_R_rs,
        )

    # ------------------------------------------------------------------
    # Calcolo flow da V_lung
    # ------------------------------------------------------------------

    def _estimate_flow(self, V_current: float, dt: float) -> float:
        """Stima il flow come dV/dt."""
        if dt > 0:
            dV = V_current - getattr(self, "_V_prev", V_current)
            flow = dV / dt
        else:
            flow = 0.0
        self._V_prev = V_current
        return float(flow)

    # ------------------------------------------------------------------
    # Auto-PEEP
    # ------------------------------------------------------------------

    def _compute_auto_PEEP(self, V_end_exp: float,
                            C_rs: float, PEEP_set: float) -> float:
        """
        Auto-PEEP = pressione residua a fine espirazione.
        Se V non è tornato allo zero: P_auto = V_end * E - PEEP_set
        """
        E = 1.0 / (C_rs + 1e-9)
        P_alv_end = V_end_exp * E
        return float(max(P_alv_end - PEEP_set, 0.0))

    # ------------------------------------------------------------------
    # Compliance e resistenza dinamica
    # ------------------------------------------------------------------

    def _update_mechanics_measures(self, Ppeak: float, Pplat: float,
                                   Vt: float, PEEP: float,
                                   flow_peak: float) -> None:
        """
        Compliance dinamica = Vt / (Pplat - PEEP)
        Resistenza dinamica = (Ppeak - Pplat) / flow_peak_L_s
        """
        if Pplat > PEEP + 0.5 and Vt > 0:
            self._compliance_dyn = Vt / (Pplat - PEEP)
        flow_L_s = abs(flow_peak) / 1000.0
        if Ppeak > Pplat + 0.5 and flow_L_s > 0.01:
            self._resistance_meas = (Ppeak - Pplat) / flow_L_s

    # ------------------------------------------------------------------
    # Allarmi
    # ------------------------------------------------------------------

    def _check_alarms(self, Ppeak: float, Vt: float,
                      RR: float, t_abs: float) -> bool:
        self._alarms["Ppeak_high"]  = Ppeak > self.params["alarm_Ppeak_max"]
        self._alarms["Vt_low"]      = 0 < Vt < self.params["alarm_Vt_min"]
        self._alarms["Vt_high"]     = Vt > self.params["alarm_Vt_max"]
        self._alarms["RR_high"]     = RR  > self.params["alarm_RR_max"]
        self._alarms["apnea"]       = (t_abs - self._t_last_breath >
                                        self.params["alarm_apnea_s"])
        return any(self._alarms.values())

    # ------------------------------------------------------------------
    # Macchina a stati — transizioni ciclo
    # ------------------------------------------------------------------

    def _start_breath(self, triggered: bool = False) -> None:
        """Inizia un nuovo ciclo inspiratorio."""
        self._phase   = CyclePhase.INSP
        self._t_phase = 0.0
        self._Ppeak   = 0.0
        self._V_at_insp_start = getattr(self, "_V_lung_current", 0.0)
        self._t_last_breath   = self._t_abs
        self._breath_count   += 1
        if triggered:
            self._triggered_breaths += 1
        if hasattr(self, '_psv') or self.params["mode"] in ("PSV", "SIMV", "CPAP"):
            self._waveform_psv.reset_cycle()

    def _transition_to_exp(self) -> None:
        self._V_at_exp_start = getattr(self, "_V_lung_current", 0.0)
        self._Vt_measured    = max(self._V_at_exp_start - self._V_at_insp_start, 0.0)
        self._phase   = CyclePhase.EXP
        self._t_phase = 0.0

    # ------------------------------------------------------------------
    # Step — cuore del modulo
    # ------------------------------------------------------------------

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        # Leggi stato paziente dal bus
        Pmus      = float(bus.get("Pmus"))
        V_lung    = float(bus.get("V_lung"))
        C_rs      = float(bus.get("C_rs"))
        R_rs      = float(bus.get("R_rs"))
        NMB_frac  = float(bus.get("drug_NMB_frac"))

        # Sincronizzazione parametri dal Bus (permette switch on-the-fly)
        mode_bus = bus.get("vent_mode") if hasattr(bus.state, "vent_mode") else None
        if mode_bus:
            mode_candidate = str(mode_bus).upper()
            if mode_candidate not in {m.value for m in VentMode}:
                mode_candidate = "PCV"
            if mode_candidate != self.params["mode"]:
                self.params["mode"] = mode_candidate
                self._phase = CyclePhase.EXP   # reset ciclo al cambio modalità
                self._t_phase = 0.0

        bus_PEEP = bus.get("PEEP")
        if bus_PEEP:
            self.params["PEEP"] = float(bus_PEEP)
        if hasattr(bus.state, "Pinsp_cmH2O") and bus.get("Pinsp_cmH2O") > 0:
            self.params["Pinsp_cmH2O"] = float(bus.get("Pinsp_cmH2O"))
        if hasattr(bus.state, "PS_cmH2O") and bus.get("PS_cmH2O") > 0:
            self.params["PS_cmH2O"] = float(bus.get("PS_cmH2O"))
        if hasattr(bus.state, "Vt_set_mL") and bus.get("Vt_set_mL") > 10:
            self.params["Vt_set_mL"] = float(bus.get("Vt_set_mL"))
        if hasattr(bus.state, "ventilator_RR_set") and bus.get("ventilator_RR_set") > 0:
            self.params["RR"] = float(bus.get("ventilator_RR_set"))
        elif hasattr(bus.state, "RR"):
            self.params["RR"] = float(bus.get("RR"))

        PEEP_set = float(self.params["PEEP"])

        # Cache per auto-PEEP e compliance
        self._V_lung_current = V_lung
        self._patient_C_rs   = C_rs
        self._patient_R_rs   = R_rs

        # Flow corrente
        flow = self._estimate_flow(V_lung, dt)
        self._flow_current = flow
        self._flow_prev    = flow

        # Aggiorna timing (permette cambio RR on-the-fly)
        self._update_timing()

        self._t_abs   += dt
        self._t_phase += dt

        mode = self.params["mode"]

        # ---- NONE/UNASSISTED: no active ventilator pressure ----
        # The patient can still breathe through Pmus generated by ChemoreflexModule.
        # v1.23.1 preserves non-invasive oxygen interfaces such as HFNC: the
        # ventilator remains disconnected, but a small external distending-pressure
        # proxy may be provided by the AirwayInterfaceModule.
        if mode in ("NONE", "UNASSISTED"):
            ambient = float(bus.get("ambient_airway_pressure_cmH2O")) if hasattr(bus.state, "ambient_airway_pressure_cmH2O") else 0.0
            iface = str(bus.get("airway_interface")).upper() if hasattr(bus.state, "airway_interface") else "UNASSISTED"
            ext_peep = float(bus.get("effective_external_PEEP_cmH2O")) if hasattr(bus.state, "effective_external_PEEP_cmH2O") else 0.0
            if iface not in ("HFNC", "LOW_FLOW_OXYGEN", "SIMPLE_MASK"):
                iface = "UNASSISTED"
                ext_peep = 0.0
            pressure_source = str(bus.get("airway_pressure_source")) if hasattr(bus.state, "airway_pressure_source") else "ambient"
            if iface == "UNASSISTED":
                pressure_source = "ambient"
            RR_spont = float(bus.get("RR")) if hasattr(bus.state, "RR") else float(self.params["RR"])
            Vt_prev = float(bus.get("Vt")) if hasattr(bus.state, "Vt") else max(float(V_lung), 0.0)
            bus.update({
                "PEEP": float(ext_peep),
                "Paw": float(ambient + ext_peep),
                "Paw_current": float(ambient + ext_peep),
                "Flow_current_mL_s": float(flow),
                "Ppeak": float(ambient + ext_peep),
                "Pplat": float(ambient + ext_peep),
                "auto_PEEP": 0.0,
                "patient_triggered": False,
                "RR_total": float(RR_spont),
                "MV_L_min": float(max(Vt_prev, 0.0) * max(RR_spont, 0.0) / 1000.0),
                "compliance_dyn": float(C_rs),
                "resistance_meas": float(R_rs),
                "vent_mode": "NONE",
                "alarm_active": False,
                "airway_interface": iface,
                "intubated": False,
                "ventilator_connected": False,
                "airway_pressure_delivery_enabled": False,
                "unassisted_breathing_active": True,
                "spontaneous_airway_mode": True,
                "effective_external_PEEP_cmH2O": float(ext_peep),
                "airway_pressure_source": pressure_source,
                "airway_interface_revision": 1231 if iface in ("HFNC", "LOW_FLOW_OXYGEN", "SIMPLE_MASK") else 123,
            })
            self._t_last_breath = self._t_abs if Pmus > 0.5 else self._t_last_breath
            return

        # ---- HFOV: caso speciale (no distinzione fasi) ----
        if mode == "HFOV":
            patient_state = {"C_rs": C_rs, "R_rs": R_rs}
            Paw, _ = self._waveform_hfov.compute_inspiratory(
                self._t_abs, 0.0, patient_state, self.params
            )
            # Gas exchange in HFOV: approssima PaCO2 da VA_eff
            VA_eff = self._hfov_VA()   # mL/s
            # Sovrascrive Vt con equivalente volumetrico
            Vt_equiv = VA_eff / max(float(self.params["HFOV_freq_Hz"]), 1.0)

            bus.update({
                "Paw":               float(Paw),
                "Paw_current":       float(Paw),
                "Flow_current_mL_s": float(self._t_abs * 0),  # oscillatorio
                "Ppeak":             float(Paw + self.params["HFOV_amplitude"]/2),
                "Pplat":             float(self.params["MAP_hfov"]),
                "auto_PEEP":         0.0,
                "patient_triggered": False,
                "RR_total":          float(self.params["HFOV_freq_Hz"] * 60),
                "MV_L_min":          float(VA_eff * 60 / 1000),
                "compliance_dyn":    float(C_rs),
                "resistance_meas":   float(R_rs),
                "vent_mode":         "HFOV",
                "alarm_active":      False,
                "Vt":                float(Vt_equiv),
            })
            self._t_last_breath = self._t_abs
            return

        # ---- Modalità con cicli discrit ----
        patient_state = {
            "C_rs": C_rs, "R_rs": R_rs,
            "V_current": V_lung, "Pmus": Pmus,
            "PEEP": PEEP_set,
        }

        triggered = self._patient_triggered(Pmus, NMB_frac)
        Paw_out   = PEEP_set
        is_triggered_breath = False

        # ===================== MACCHINA A STATI =====================

        if self._phase == CyclePhase.INSP:
            # ---- Fase inspiratoria ----
            T_insp_eff = self._T_insp - self._T_pause

            if mode == "VCV":
                Paw_out, flow_target = self._waveform_vcv.compute_inspiratory(
                    self._t_phase, T_insp_eff, patient_state, self.params
                )
            elif mode == "PCV":
                Paw_out, _ = self._waveform_pcv.compute_inspiratory(
                    self._t_phase, T_insp_eff, patient_state, self.params
                )
            elif mode == "PSV":
                Paw_out, _ = self._waveform_psv.compute_inspiratory(
                    self._t_phase, T_insp_eff, patient_state, self.params
                )
                self._waveform_psv.update_peak_flow(abs(flow))

            elif mode == "CPAP":
                Paw_out, _ = self._waveform_cpap.compute_inspiratory(
                    self._t_phase, T_insp_eff, patient_state, self.params
                )

            elif mode == "SIMV":
                if self._in_mandatory:
                    # Atto mandatorio (PCV o VCV)
                    Paw_out, _ = self._waveform_pcv.compute_inspiratory(
                        self._t_phase, T_insp_eff, patient_state, self.params
                    )
                else:
                    # Atto spontaneo (PSV)
                    Paw_out, _ = self._waveform_psv.compute_inspiratory(
                        self._t_phase, T_insp_eff, patient_state, self.params
                    )
                    self._waveform_psv.update_peak_flow(abs(flow))

            # Aggiorna Ppeak
            self._Ppeak = max(self._Ppeak, Paw_out)

            # Transizioni: fine inspirazione
            if mode in ("PSV", "SIMV") and not self._in_mandatory:
                # Cycling criterion (flow)
                if self._waveform_psv.check_cycling(
                    abs(flow), self.params["cycling_frac"]
                ):
                    self._transition_to_exp()
                elif self._t_phase >= T_insp_eff * 3.0:
                    # Safety: max TI = 3× TI_set
                    self._transition_to_exp()
            else:
                if self._t_phase >= T_insp_eff:
                    if self._T_pause > 0:
                        self._phase   = CyclePhase.INSP_PAUSE
                        self._t_phase = 0.0
                    else:
                        self._transition_to_exp()

        elif self._phase == CyclePhase.INSP_PAUSE:
            # ---- Pausa inspiratoria (Pplat) ----
            Paw_out = PEEP_set + self._Vt_measured / (C_rs + 1e-9)
            self._Pplat = Paw_out

            if self._t_phase >= self._T_pause:
                self._transition_to_exp()
                self._update_mechanics_measures(
                    self._Ppeak, self._Pplat,
                    self._Vt_measured, PEEP_set,
                    abs(self._flow_current)
                )

        elif self._phase == CyclePhase.EXP:
            # ---- Fase espiratoria ----
            Paw_out = PEEP_set

            # Auto-PEEP
            if self._t_phase > self._T_exp * 0.8:
                mech_auto = self._compute_auto_PEEP(
                    V_lung, C_rs, PEEP_set
                )
                obs_auto = bus.get("auto_PEEP_obstructive") if hasattr(bus.state, "auto_PEEP_obstructive") else 0.0
                self._auto_PEEP = max(float(mech_auto), float(obs_auto))

            # Transizioni
            if mode in ("VCV", "PCV", "SIMV") and not (mode == "SIMV" and not self._in_mandatory):
                # Atti time-triggered
                if self._t_phase >= self._T_exp:
                    # SIMV: controlla se è ora di atto mandatorio
                    if mode == "SIMV":
                        if self._t_abs >= self._next_mandatory_t:
                            self._in_mandatory = True
                            self._next_mandatory_t = self._t_abs + 60.0 / self.params["RR_set"]
                        else:
                            self._in_mandatory = False
                    self._start_breath(triggered=False)

            elif mode in ("PSV", "CPAP") or (mode == "SIMV" and not self._in_mandatory):
                # Trigger-triggered: aspetta sforzo paziente
                if triggered:
                    self._start_breath(triggered=True)
                    is_triggered_breath = True
                elif self._t_phase >= self._T_exp * 4.0:
                    # Safety: apnea backup → eroga atto mandatorio
                    self._start_breath(triggered=False)

        # ===================== OUTPUT =====================

        # PEEP minima garantita
        Paw_out = max(float(Paw_out), PEEP_set)

        # Sicurezza Ppeak max
        if Paw_out > self.params["alarm_Ppeak_max"]:
            Paw_out = float(self.params["alarm_Ppeak_max"])
            self._alarms["Ppeak_high"] = True

        # RR totale
        T_tot = self._T_insp + self._T_exp + self._T_pause
        RR_tot = 60.0 / (T_tot + 1e-3)
        MV_L = self._Vt_measured * RR_tot / 1000.0   # L/min

        # v3.2 public-polish deviation fix:
        # `Paw` remains the instantaneous waveform pressure used by mechanics.
        # For numeric monitor/CLI display, expose a cycle-level mean estimate so
        # sampled snapshots do not appear to oscillate between inspiratory and
        # expiratory values.
        if mode == "HFOV":
            paw_mean = float(self.params.get("MAP_hfov", Paw_out))
        elif mode in ("CPAP", "NONE", "UNASSISTED"):
            paw_mean = float(Paw_out)
        else:
            duty = float(np.clip(self._T_insp / max(T_tot, 1e-6), 0.10, 0.90))
            paw_mean = float(PEEP_set + max(self._Ppeak - PEEP_set, 0.0) * duty)
        paw_display = paw_mean

        # Allarmi
        alarm_any = self._check_alarms(
            self._Ppeak, self._Vt_measured, RR_tot, self._t_abs
        )

        bus.update({
            "Paw":               float(Paw_out),
            "Paw_current":       float(Paw_out),
            "Paw_mean":          float(paw_mean),
            "Paw_display":       float(paw_display),
            "Flow_current_mL_s": float(flow),
            "Ppeak":             float(self._Ppeak),
            "Pplat":             float(self._Pplat),
            "auto_PEEP":         float(self._auto_PEEP),
            "patient_triggered": bool(is_triggered_breath),
            "RR_total":          float(RR_tot),
            "MV_L_min":          float(MV_L),
            "compliance_dyn":    float(self._compliance_dyn),
            "resistance_meas":   float(self._resistance_meas),
            "vent_mode":         str(mode),
            "alarm_active":      bool(alarm_any),
            "nmb_trigger_block_active": bool(NMB_frac >= 0.90),
        })


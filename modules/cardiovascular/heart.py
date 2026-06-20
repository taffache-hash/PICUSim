"""
Heart Model
===========
Modello cardiaco a 4 camere con elastanza variante nel tempo (Suga-Sagawa).
Parametri normalizzati per bambino pediatrico (default 20 kg, 5 anni).

Fisica:
  E(t) = (Emax - Emin)/2 · [1 - cos(π·t/Ts)] + Emin   per t ≤ Ts (sistole)
  E(t) = Emin                                            per t > Ts (diastole)
  P(t) = E(t) · (V(t) - V0)

Frank-Starling implicito: Emax modulata dal preload (EDV).
Afterload: MAP e PAP vincolano SV via curva P-V.
Accoppiamento ventricolo-vascolare (Ventriculo-Arterial Coupling).

Camere:
  LV (left ventricle): espelle nel circolo sistemico
  RV (right ventricle): espelle nel circolo polmonare
  LA, RA: camere di riempimento (semplici cisterne con compliance)
"""

from __future__ import annotations
import numpy as np
from typing import List

from core.base_module import BaseModule
from core.bus import PhysiologicalBus


class HeartModule(BaseModule):
    """
    Cuore a 4 camere con elastanza variante nel tempo.

    Parametri LV
    ------------
    Emax_lv : float    Elastanza sistolica max [mmHg/mL]
    Emin_lv : float    Elastanza diastolica [mmHg/mL]
    V0_lv   : float    Volume a pressione zero [mL]
    Ts_frac  : float   Durata sistolica come fraz. del ciclo (default 0.4)

    Parametri RV (elastanze ~1/3 del LV)
    --------------------------------------
    Emax_rv, Emin_rv, V0_rv

    Frank-Starling
    --------------
    frank_starling_gain : float
        Modulazione di Emax per EDV: Emax_eff = Emax · (1 + FS·(EDV/EDV0 - 1))
    """

    DEFAULT_PARAMS = {
        # LV — auto-consistenti: MAP=68, CO=3.85 L/min, HR=105, EDV=55, ESV=18.3
        # Emax = MAP/(ESV-V0) = 68/(18.3-5) = 5.10 mmHg/mL
        "Emax_lv":          5.10,    # mmHg/mL
        "Emin_lv":          0.08,    # mmHg/mL
        "V0_lv":            5.0,     # mL
        "EDV0_lv":          55.0,    # mL

        # RV — auto-consistenti: PAP=15, ESV_rv=23.3, V0_rv=8
        # Emax_rv = PAP/(ESV-V0) = 15/(23.3-8) = 0.98 mmHg/mL
        "Emax_rv":          0.978,   # mmHg/mL
        "Emin_rv":          0.03,    # mmHg/mL
        "V0_rv":            8.0,     # mL
        "EDV0_rv":          60.0,    # mL

        # Atri (compliance semplice)
        "C_la":             8.0,     # mL/mmHg
        "C_ra":             10.0,    # mL/mmHg

        # Timing
        "Ts_frac":          0.38,    # sistole = 38% del ciclo cardiaco

        # Frank-Starling gain
        "frank_starling_gain": 0.5,

        # Valve pressures (semplificazione: valvole ideali con isteresi minima)
        "P_open_mitral":    0.0,     # mmHg (apre se P_LA > P_LV)
        "P_open_aortic":    0.0,     # mmHg (apre se P_LV > MAP)
    }

    def __init__(self, params: dict | None = None):
        merged = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(name="Heart", params=merged)

        # Stato interno
        self._t_phase:  float = 0.0   # tempo nel ciclo cardiaco corrente [s]
        self._T_cycle:  float = 0.55  # durata ciclo [s] = 60/HR
        self._EDV_lv:   float = 55.0
        self._ESV_lv:   float = 20.0
        self._EDV_rv:   float = 60.0
        self._ESV_rv:   float = 20.0
        self._in_systole: bool = False
        self._SV_lv:    float = 35.0
        self._SV_rv:    float = 35.0

    @property
    def input_keys(self) -> List[str]:
        return ["HR", "MAP", "CVP", "PAP_mean", "PAWP", "Ppl", "SvO2", "drug_HR_mod", "drug_inotropy_mod", "shock_contractility_mod"]

    @property
    def output_keys(self) -> List[str]:
        return ["SV", "CO", "EDV_lv", "ESV_lv", "EF_lv",
                "SAP", "DAP", "SBP", "DBP", "arterial_pulse_pressure", "MAP"]

    def _elastance(self, t_phase: float, T_cycle: float,
                   Emax: float, Emin: float, Ts: float) -> float:
        """Elastanza istantanea (modello Suga-Sagawa)."""
        if t_phase <= Ts:
            return Emin + (Emax - Emin) / 2.0 * (1.0 - np.cos(np.pi * t_phase / Ts))
        else:
            # Rilassamento isovolumetrico e diastole
            T_relax = min(0.15 * T_cycle, T_cycle - Ts)
            t_rel = t_phase - Ts
            if t_rel < T_relax:
                frac = 1.0 - t_rel / T_relax
                return Emin + (Emax - Emin) / 2.0 * frac * 0.3
            return Emin

    def _frank_starling_Emax(self, EDV: float, EDV0: float,
                              Emax: float) -> float:
        """Modulazione di Emax per preload (Frank-Starling)."""
        gain = self.params["frank_starling_gain"]
        ratio = EDV / (EDV0 + 1e-6)
        mod = 1.0 + gain * (ratio - 1.0)
        return float(Emax * np.clip(mod, 0.3, 2.0))

    def _edv_bounds(self, side: str = "lv") -> tuple[float, float]:
        edv0 = float(self.params["EDV0_lv" if side == "lv" else "EDV0_rv"])
        return max(0.35 * edv0, 0.5), max(1.85 * edv0, 1.0)

    def _esv_lower(self, side: str = "lv") -> float:
        v0 = float(self.params["V0_lv" if side == "lv" else "V0_rv"])
        edv0 = float(self.params["EDV0_lv" if side == "lv" else "EDV0_rv"])
        return max(v0 * 1.03, 0.04 * edv0, 0.15)

    def initialize(self, bus: PhysiologicalBus) -> None:
        HR = bus.get("HR")
        self._T_cycle = 60.0 / (max(HR, 30.0))
        self._t_phase = 0.0
        self._EDV_lv  = bus.get("EDV_lv")
        self._ESV_lv  = bus.get("ESV_lv")
        self._SV_lv   = self._EDV_lv - self._ESV_lv
        CO_init = self._SV_lv * HR / 1000.0
        bus.update({"CO": CO_init, "SV": self._SV_lv})

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        HR      = bus.get("HR")
        MAP     = bus.get("MAP")
        CVP     = bus.get("CVP")
        PAP     = bus.get("PAP_mean")
        PAWP    = bus.get("PAWP")
        Ppl     = bus.get("Ppl")

        self._T_cycle = 60.0 / (max(HR, 30.0))
        Ts = self.params["Ts_frac"] * self._T_cycle

        # --- Frank-Starling: EDV dipende dal preload ---
        # Preload LV: usa PAWP transmurale
        PAWP_tm = max(PAWP - Ppl * 0.05, 0.0)   # Ppl in cmH2O, effetto ridotto
        # EDV_lv: risposta Frank-Starling con guadagno limitato
        # ΔEDV = k * (PAWP_tm - PAWP_ref) con k piccolo per stabilità
        EDV_lv_target = self.params["EDV0_lv"] * (
            1.0 + 0.010 * (PAWP_tm - 8.0)
        )
        EDV_lv_target = float(np.clip(EDV_lv_target, *self._edv_bounds("lv")))

        # Preload RV = CVP
        EDV_rv_target = self.params["EDV0_rv"] * (
            1.0 + 0.008 * (CVP - 5.0)
        )
        EDV_rv_target = float(np.clip(EDV_rv_target, *self._edv_bounds("rv")))

        # ESV_lv: calcolato sulla Emax sistolica (non sull'istantanea)
        # Evita oscillazioni: usiamo Emax come proxy della contrattilità peak
        inotropy_mod = float(bus.get("drug_inotropy_mod")) if hasattr(bus.state, "drug_inotropy_mod") else 1.0
        shock_contractility_mod = float(bus.get("shock_contractility_mod")) if hasattr(bus.state, "shock_contractility_mod") else 1.0
        inotropy_mod = float(np.clip(inotropy_mod * shock_contractility_mod, 0.35, 1.60))
        Emax_lv_eff = self._frank_starling_Emax(
            self._EDV_lv, self.params["EDV0_lv"], self.params["Emax_lv"] * inotropy_mod
        )
        # ESV = V0 + MAP/Emax  (Suga-Sagawa steady-state)
        ESV_lv = self.params["V0_lv"] + MAP / (Emax_lv_eff + 1e-6)
        ESV_lv = float(np.clip(ESV_lv, self._esv_lower("lv"), EDV_lv_target * 0.85))

        # Elastanza istantanea (per output futuro, non usata per SV)
        E_lv = self._elastance(self._t_phase, self._T_cycle,
                               Emax_lv_eff, self.params["Emin_lv"], Ts)

        # SV e CO
        SV_lv = max(EDV_lv_target - ESV_lv, 0.0)
        # HR pharmacology is now expressed in BaroreflexModule so that the
        # displayed bedside HR and cardiac output stay aligned.
        HR_eff = float(np.clip(HR, 30.0, 220.0))
        CO    = SV_lv * HR_eff / 1000.0   # L/min

        # EF
        EF_lv = SV_lv / (EDV_lv_target + 1e-6)
        EF_lv = float(np.clip(EF_lv, 0.1, 0.85))

        # Elastanza RV (usa Emax_rv, non istantanea)
        Emax_rv_eff = self._frank_starling_Emax(
            self._EDV_rv, self.params["EDV0_rv"], self.params["Emax_rv"] * inotropy_mod
        )
        E_rv = self._elastance(self._t_phase, self._T_cycle,
                               Emax_rv_eff, self.params["Emin_rv"], Ts)
        ESV_rv = self.params["V0_rv"] + PAP / (Emax_rv_eff + 1e-6)
        ESV_rv = float(np.clip(ESV_rv, self._esv_lower("rv"), EDV_rv_target * 0.85))
        SV_rv  = max(EDV_rv_target - ESV_rv, 0.0)

        # Pressioni aortiche (sistolica/diastolica)
        # SAP ≈ MAP + Pper (pressione pulsatile proporzionale a SV e SVR)
        PP   = SV_lv * (bus.get("SVR") / 1333.0) * 0.3   # pressione pulsatile
        SAP  = MAP + 0.67 * PP
        DAP  = MAP - 0.33 * PP
        SAP  = float(np.clip(SAP, DAP + 5.0, 200.0))
        DAP  = float(np.clip(DAP, 20.0, SAP - 5.0))

        # Avanza la fase del ciclo cardiaco
        self._t_phase += dt
        if self._t_phase >= self._T_cycle:
            self._t_phase -= self._T_cycle
            self._EDV_lv = EDV_lv_target
            self._ESV_lv = ESV_lv
            self._EDV_rv = EDV_rv_target
            self._ESV_rv = ESV_rv
            self._SV_lv  = SV_lv

        bus.update({
            "SV":     float(SV_lv),
            "CO":     float(CO),
            "EDV_lv": float(EDV_lv_target),
            "ESV_lv": float(ESV_lv),
            "EF_lv":  float(EF_lv),
            "SAP":    float(SAP),
            "DAP":    float(DAP),
            "SBP":    float(SAP),
            "DBP":    float(DAP),
            "arterial_pulse_pressure": float(max(SAP - DAP, 5.0)),
            "arterial_pressure_source": "heart_pressure_envelope",
        })

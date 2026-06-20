"""
Respiratory Mechanics Module
============================
Public educational respiratory-mechanics model for pediatric critical-care simulation.

This module implements a compact, lumped patient-response model:
  - pressure-driven tidal volume from a single-compartment equation of motion;
  - size-scaled compliance and airway resistance;
  - a bounded qualitative recruitment state driven by distending pressure and disease severity;
  - bedside-like outputs for tidal volume, compliance, driving pressure, work of breathing,
    mechanical power, and qualitative lung-stress indices.

The module is intentionally strategy-agnostic: it receives airway pressure and muscular
pressure from the shared physiological bus and does not implement specific ventilatory
strategy-control logic.
"""

from __future__ import annotations
import numpy as np
from typing import List

from core.base_module import BaseModule
from core.bus import PhysiologicalBus
from core.profile_scaling import bus_patient_scalars


class RespiratoryMechanicsModule(BaseModule):
    """
    Lumped respiratory mechanics model.

    Parameters
    ----------
    C_rs_max : float
        Compliance at best recruitment [mL/cmH2O].
    C_rs_min : float
        Compliance at severe loss of aerated lung volume [mL/cmH2O].
    R_rs : float
        Baseline airway resistance [cmH2O·s/L].
    FRC_ml : float
        Functional residual capacity anchor [mL].
    non_recruitable_frac : float
        Fixed fraction of lung units represented as non-responsive to pressure [0-1].
    baseline_recruitment : float
        Initial recruitment anchor before disease/pressure adjustment [0-1].
    recruitment_tau_s : float
        Time constant of the lumped recruitment state [s].
    recruitment_pressure_mid_cmH2O : float
        Distending-pressure midpoint for the smooth recruitment response [cmH2O].
    recruitment_pressure_slope_cmH2O : float
        Smoothness of the pressure-recruitment response [cmH2O].
    """

    DEFAULT_PARAMS = {
        "C_rs_max": 2.0,
        "C_rs_min": 0.4,
        "R_rs": 8.0,
        "FRC_ml": 320.0,
        "weight_kg": 20.0,
        "non_recruitable_frac": 0.0,
        "baseline_recruitment": 0.88,
        "recruitment_tau_s": 8.0,
        "recruitment_pressure_mid_cmH2O": 4.0,
        "recruitment_pressure_slope_cmH2O": 3.5,
        "overdistension_start_ml_kg": 8.0,
        "overdistension_full_ml_kg": 14.0,
    }

    def __init__(self, params: dict | None = None):
        merged = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(name="RespiratoryMechanics", params=merged)
        self._recruited_frac: float = float(merged["baseline_recruitment"])
        self._V_current: float = 0.0
        self._Vt_peak: float = 0.0
        self._Vt_last: float = 0.0
        self._was_insp: bool = False
        self._RR: float = 25.0

    @property
    def input_keys(self) -> List[str]:
        return ["Paw", "Pmus", "PEEP", "RR", "FRC", "airway_resistance_mod", "auto_PEEP_obstructive"]

    @property
    def output_keys(self) -> List[str]:
        return ["V_lung", "EELV", "Palv", "Ppl", "recruited_frac",
                "C_rs", "E_rs", "R_rs", "Vt", "Pdriving", "WOB", "MP",
                "MP_applicable", "MP_method", "HFOV_power_proxy",
                "overdistension_index", "atelectrauma_index", "VILI_risk"]

    def initialize(self, bus: PhysiologicalBus) -> None:
        info = bus_patient_scalars(bus, self.params)
        wt = info["weight_kg"]
        prof = info["profile"]
        c_kg = float(prof.get("C_rs_ml_cmH2O_kg", 0.8))
        frc_kg = float(prof.get("FRC_ml_kg", 30.0))

        scenario_c = max(float(bus.get("C_rs")), 0.05)
        self.params["weight_kg"] = wt
        self.params["FRC_ml"] = float(bus.get("FRC") or frc_kg * wt)
        provided_cmax = float(self.params.get("C_rs_max", scenario_c * 1.25))
        provided_cmin = float(self.params.get("C_rs_min", max(0.15 * wt, 0.05)))
        self.params["C_rs_max"] = max(provided_cmax, scenario_c * 1.25, c_kg * wt * 0.55, 0.2)
        self.params["C_rs_min"] = max(min(provided_cmin, self.params["C_rs_max"] * 0.45), 0.05)
        self.params["R_rs"] = float(self.params.get("R_rs", 8.0)) * float((20.0 / wt) ** 0.25)

        PEEP = float(bus.get("PEEP"))
        self._recruited_frac = self._target_recruitment(PEEP)
        self._V_current = 0.0
        self._Vt_peak = 0.0
        self._Vt_last = 0.0
        self._was_insp = False
        self._RR = float(bus.get("RR"))

        C_eff = self._effective_compliance(self._recruited_frac)
        bus.update({
            "recruited_frac": float(self._recruited_frac),
            "EELV": float(bus.get("FRC")),
            "V_lung": 0.0,
            "C_rs": float(C_eff),
            "E_rs": float(1000.0 / C_eff if C_eff > 0 else 100.0),
            "R_rs": float(self.params["R_rs"]),
        })

    def _effective_compliance(self, rec_frac: float) -> float:
        return float(self.params["C_rs_min"] + rec_frac * (self.params["C_rs_max"] - self.params["C_rs_min"]))

    def _target_recruitment(self, distending_pressure: float) -> float:
        non_rec = float(np.clip(self.params.get("non_recruitable_frac", 0.0), 0.0, 0.9))
        max_rec = 1.0 - non_rec
        mid = float(self.params.get("recruitment_pressure_mid_cmH2O", 4.0)) + 6.0 * non_rec
        slope = max(float(self.params.get("recruitment_pressure_slope_cmH2O", 3.5)), 0.5)
        pressure_term = 1.0 / (1.0 + np.exp(-(float(distending_pressure) - mid) / slope))
        baseline = float(np.clip(self.params.get("baseline_recruitment", 0.88), 0.45, 0.97))
        target = max_rec * (0.72 * baseline + 0.28 * pressure_term)
        return float(np.clip(target, 0.02, max_rec))

    def _update_recruitment(self, distending_pressure: float, dt: float) -> float:
        target = self._target_recruitment(distending_pressure)
        tau = max(float(self.params.get("recruitment_tau_s", 8.0)), dt)
        alpha = 1.0 - np.exp(-dt / tau)
        self._recruited_frac += alpha * (target - self._recruited_frac)
        non_rec = float(np.clip(self.params.get("non_recruitable_frac", 0.0), 0.0, 0.9))
        self._recruited_frac = float(np.clip(self._recruited_frac, 0.0, 1.0 - non_rec))
        return self._recruited_frac

    def _current_pressures(self, bus: PhysiologicalBus) -> tuple[float, float]:
        Paw_eff = bus.get("Paw_current") if hasattr(bus.state, "Paw_current") else bus.get("Paw")
        return float(Paw_eff), float(bus.get("Pmus"))

    def _motion_equation_volume(self, bus: PhysiologicalBus, Paw: float, Pmus: float, PEEP: float,
                                C_eff: float, dt: float) -> tuple[float, float]:
        R_base = self.params["R_rs"]
        R_mod = bus.get("airway_resistance_mod") if hasattr(bus.state, "airway_resistance_mod") else 1.0
        R = R_base * max(float(R_mod), 1.0)
        E = 1.0 / (C_eff + 1e-9)
        R_ml = R / 1000.0

        P_drive = max(Paw - PEEP, 0.0) + max(Pmus, 0.0)
        V_eq = P_drive / E
        tau_mech = max(R_ml / E, dt * 0.5)
        V_new = V_eq + (self._V_current - V_eq) * np.exp(-dt / tau_mech)
        V_new = max(V_new, 0.0)

        dV = (V_new - self._V_current) / (dt + 1e-9)
        Palv_rel = E * V_new + R_ml * dV
        return float(V_new), float(Palv_rel)

    def _compute_MP(self, RR: float, Vt: float, Paw_peak: float, PEEP: float,
                    mode: str, bus: PhysiologicalBus) -> tuple[float, bool, str, float]:
        """Return conventional mechanical power and HFOV applicability metadata.

        The usual bedside mechanical-power approximation is defined for conventional
        cyclic ventilation. HFOV reports RR_total as frequency * 60, so applying the
        conventional formula to HFOV would create a numerically large but physically
        meaningless value. For HFOV, MP is therefore flagged as not applicable and a
        separate qualitative power proxy is exported for audit/debriefing only.
        """
        mode_u = str(mode).upper()
        if mode_u == "HFOV":
            amp = float(bus.get("HFOV_amplitude")) if hasattr(bus.state, "HFOV_amplitude") else 0.0
            freq = float(bus.get("HFOV_freq_Hz")) if hasattr(bus.state, "HFOV_freq_Hz") else max(RR / 60.0, 0.0)
            vt_L = max(float(Vt), 0.0) / 1000.0
            proxy = max(0.10 * amp * freq * vt_L, 0.0)
            return 0.0, False, "not_applicable_HFOV", float(proxy)

        Vt_L = Vt / 1000.0
        mp = float(max(0.098 * RR * Vt_L * max(Paw_peak - PEEP / 2.0, 0.0), 0.0))
        return mp, True, "conventional_bedside_approximation", 0.0

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        PEEP = float(bus.get("PEEP"))
        FRC = float(bus.get("FRC"))
        RR = max(bus.get("RR_total") if hasattr(bus.state, "RR_total") and bus.get("RR_total") > 0 else bus.get("RR"), 1.0)
        self._RR = float(RR)

        Paw, Pmus = self._current_pressures(bus)
        mode = str(bus.get("vent_mode")) if hasattr(bus.state, "vent_mode") else "PCV"
        if mode in ("PCV", "VCV", "HFOV"):
            Pmus = 0.20 * Pmus

        C_eff = self._effective_compliance(self._recruited_frac)
        auto_obs = bus.get("auto_PEEP_obstructive") if hasattr(bus.state, "auto_PEEP_obstructive") else 0.0
        V_new, Palv_rel = self._motion_equation_volume(bus, Paw, Pmus, PEEP + 0.35 * auto_obs, C_eff, dt)
        Palv_abs = max(Palv_rel + PEEP, 0.0)

        distending_pressure = max(PEEP, 0.65 * Palv_abs + 0.35 * PEEP)
        rec_frac_new = self._update_recruitment(distending_pressure, dt)
        C_eff_new = self._effective_compliance(rec_frac_new)

        EELV_new = max(FRC + (rec_frac_new - 0.5) * C_eff_new * 10.0, FRC * 0.5)
        E_eff = 1.0 / (C_eff_new + 1e-9)
        Ppl = Palv_abs - E_eff * (V_new * 0.5)

        in_insp = Paw > (PEEP + 0.5)
        if in_insp and not self._was_insp:
            self._Vt_peak = max(V_new, 0.0)
        elif in_insp:
            self._Vt_peak = max(self._Vt_peak, V_new)
        elif self._was_insp and not in_insp:
            peak = max(self._Vt_peak, 0.0)
            if peak > 1.0:
                self._Vt_last = peak
            self._Vt_peak = 0.0
        self._was_insp = in_insp
        Vt_report = self._Vt_last if self._Vt_last > 0 else max(V_new, 0.0)

        Paw_peak = max(bus.get("Ppeak"), bus.get("Paw"))
        Pdriving = max(Paw_peak - PEEP, 0.0)
        WOB = Pmus * Vt_report / 1000.0 if Pmus > 0 else 0.0

        wt = max(float(self.params.get("weight_kg", 20.0)), 1.0)
        vt_ml_kg = Vt_report / wt
        od_start = float(self.params.get("overdistension_start_ml_kg", 8.0))
        od_full = float(self.params.get("overdistension_full_ml_kg", 14.0))
        overdistension_index = float(np.clip((vt_ml_kg - od_start) / (od_full - od_start + 1e-6), 0.0, 1.0))

        non_rec = float(np.clip(self.params.get("non_recruitable_frac", 0.0), 0.0, 0.9))
        max_rec = max(1.0 - non_rec, 1e-6)
        rec_deficit = float(np.clip((max_rec - rec_frac_new) / max_rec, 0.0, 1.0))
        atelectrauma_index = float(np.clip(0.65 * rec_deficit + 0.35 * np.clip(Pdriving / 35.0, 0.0, 1.0) * rec_deficit, 0.0, 1.0))

        MP, MP_applicable, MP_method, HFOV_power_proxy = self._compute_MP(
            RR=RR, Vt=Vt_report, Paw_peak=Paw_peak, PEEP=PEEP, mode=mode, bus=bus
        )
        MP_norm = MP / max(wt, 1.0)
        power_stress = float(np.clip((MP_norm - 0.35) / 1.4, 0.0, 1.0))
        VILI_risk = float(np.clip((overdistension_index + atelectrauma_index + power_stress) / 3.0, 0.0, 1.0))

        self._V_current = V_new
        R_mod = bus.get("airway_resistance_mod") if hasattr(bus.state, "airway_resistance_mod") else 1.0
        bus.update({
            "V_lung": float(V_new),
            "Palv": float(Palv_abs),
            "Ppl": float(Ppl),
            "EELV": float(EELV_new),
            "recruited_frac": float(rec_frac_new),
            "C_rs": float(C_eff_new),
            "E_rs": float(E_eff * 1000.0),
            "R_rs": float(self.params["R_rs"] * max(float(R_mod), 1.0)),
            "Vt": float(Vt_report),
            "Pdriving": float(Pdriving),
            "WOB": float(WOB),
            "MP": float(MP),
            "MP_applicable": bool(MP_applicable),
            "MP_method": str(MP_method),
            "HFOV_power_proxy": float(HFOV_power_proxy),
            "overdistension_index": float(overdistension_index),
            "atelectrauma_index": float(atelectrauma_index),
            "VILI_risk": float(VILI_risk),
        })

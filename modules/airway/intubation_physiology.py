"""
Intubation physiology — v3.1 Step 4.41
=======================================

Educational peri-intubation physiology scaffold.  The module tracks a bounded
preoxygenation reservoir, apnea duration, RSI-related respiratory motor
suppression and a qualitative desaturation trajectory around existing airway
interface/actions.

This is not a clinical calculator.  It is intentionally conservative and
bounded so that it can be used for simulation feedback without providing
patient-specific dosing, airway management, or medical advice.
"""

from __future__ import annotations

import math
from typing import List

import numpy as np

from core.base_module import BaseModule
from core.bus import PhysiologicalBus


class IntubationPhysiologyModule(BaseModule):
    """Peri-intubation oxygen reserve, apnea and RSI-effect coupling.

    Scenario/action layers remain responsible for declaring airway events. This
    module reads those state flags and writes bounded physiologic/audit fields:

    * preoxygenation reservoir [0-1]
    * apnea timer and apnea-active flag
    * predicted desaturation risk/slope
    * RSI drug-effect coupling from NMB/propofol/ketamine signals
    * optional bounded SaO2/PaO2 downward trajectory during apnea
    """

    REVISION = 441

    DEFAULT_PARAMS = {
        "reservoir_build_tau_s": 45.0,
        "reservoir_decay_tau_s": 18.0,
        "safe_apnea_base_s": 85.0,
        "critical_apnea_s": 140.0,
        "desat_gain": 0.030,
        "oxygenation_recovery_gain": 0.20,
    }

    def __init__(self, params: dict | None = None):
        super().__init__(name="IntubationPhysiology", params={**self.DEFAULT_PARAMS, **(params or {})})
        self._reservoir = 0.45
        self._apnea_s = 0.0

    @property
    def input_keys(self) -> List[str]:
        return [
            "t", "weight_kg", "FRC", "EELV", "FiO2", "FiO2_delivered", "SaO2", "PaO2", "PaCO2",
            "RR", "RR_total", "Vt", "intubated", "ventilator_connected", "manual_ventilation_active",
            "bag_mask_ventilation_active", "bag_mask_quality", "airway_interface", "airway_rescue_state",
            "airway_event_type", "airway_event_status", "airway_event_time_s", "failed_intubation_count",
            "sed_resp_mod", "drug_NMB_frac", "propofol_vasodilation_signal", "propofol_sedation_signal",
            "ketamine_dissociation_signal", "ketamine_resp_depression_signal", "upper_airway_obstruction_score",
            "laryngospasm_score", "airway_obstruction_index", "aspiration_risk",
        ]

    @property
    def output_keys(self) -> List[str]:
        return [
            "intubation_physiology_revision", "preoxygenation_active", "preoxygenation_reservoir",
            "apnea_active", "apnea_timer_s", "safe_apnea_time_remaining_s", "rsi_effect_active",
            "rsi_resp_suppression_index", "peri_intubation_desaturation_risk",
            "peri_intubation_desaturation_slope", "peri_intubation_phase",
            "peri_intubation_warning", "SaO2", "PaO2",
        ]

    @staticmethod
    def _clip(x: float, lo: float, hi: float) -> float:
        return float(np.clip(float(x), lo, hi))

    @staticmethod
    def _get(bus: PhysiologicalBus, key: str, default):
        return getattr(bus.state, key, default)

    def initialize(self, bus: PhysiologicalBus) -> None:
        self._reservoir = self._clip(self._get(bus, "preoxygenation_reservoir", 0.45), 0.0, 1.0)
        self._apnea_s = max(float(self._get(bus, "apnea_timer_s", 0.0)), 0.0)
        self.step(bus, 0.0)

    def _effective_ventilation(self, bus: PhysiologicalBus) -> tuple[bool, float]:
        intubated = bool(self._get(bus, "intubated", True))
        vent_connected = bool(self._get(bus, "ventilator_connected", True))
        manual = bool(self._get(bus, "manual_ventilation_active", False) or self._get(bus, "bag_mask_ventilation_active", False))
        bvm_quality = self._clip(self._get(bus, "bag_mask_quality", 0.0), 0.0, 1.0)
        rr = float(self._get(bus, "RR_total", self._get(bus, "RR", 0.0)))
        vt = max(float(self._get(bus, "Vt", 0.0)), 0.0)
        airway_block = self._clip(max(
            self._get(bus, "upper_airway_obstruction_score", 0.0),
            self._get(bus, "laryngospasm_score", 0.0),
            self._get(bus, "airway_obstruction_index", 0.0),
        ), 0.0, 1.0)

        circuit_quality = 1.0 if (intubated and vent_connected) else (0.25 + 0.75 * bvm_quality if manual else 0.0)
        minute_vent_proxy = self._clip((rr * vt) / max(150.0 * max(float(self._get(bus, "weight_kg", 20.0)), 1.0), 1.0), 0.0, 1.4)
        quality = self._clip(circuit_quality * minute_vent_proxy * (1.0 - 0.75 * airway_block), 0.0, 1.0)
        return quality > 0.18, quality

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        dt = max(float(dt), 0.0)
        fio2 = self._clip(self._get(bus, "FiO2_delivered", self._get(bus, "FiO2", 0.21)), 0.21, 1.0)
        sao2 = self._clip(self._get(bus, "SaO2", 0.97), 0.05, 1.0)
        pao2 = self._clip(self._get(bus, "PaO2", 90.0), 10.0, 560.0)
        wt = max(float(self._get(bus, "weight_kg", 20.0)), 1.0)
        frc = max(float(self._get(bus, "FRC", self._get(bus, "EELV", 30.0 * wt))), 10.0)

        ventilation_ok, ventilation_quality = self._effective_ventilation(bus)
        nmb = self._clip(self._get(bus, "drug_NMB_frac", 0.0), 0.0, 1.0)
        sed_resp = self._clip(self._get(bus, "sed_resp_mod", 1.0), 0.0, 1.5)
        propofol = self._clip(max(self._get(bus, "propofol_sedation_signal", 0.0), self._get(bus, "propofol_vasodilation_signal", 0.0)), 0.0, 1.0)
        ketamine_resp = self._clip(self._get(bus, "ketamine_resp_depression_signal", 0.0), 0.0, 1.0)
        ketamine_diss = self._clip(self._get(bus, "ketamine_dissociation_signal", 0.0), 0.0, 1.0)

        rsi_suppression = self._clip(0.58 * nmb + 0.28 * (1.0 - min(sed_resp, 1.0)) + 0.18 * propofol + 0.08 * ketamine_resp, 0.0, 1.0)
        rsi_active = bool(rsi_suppression >= 0.35 or str(self._get(bus, "airway_event_type", "none")) in {"perform_intubation", "failed_intubation_attempt"})

        # Apnea is a physiologic state, not just an event label.
        rr = float(self._get(bus, "RR_total", self._get(bus, "RR", 0.0)))
        apnea = bool((not ventilation_ok and (rr < 4.0 or rsi_suppression > 0.45)) or (rsi_suppression > 0.80 and ventilation_quality < 0.35))
        if apnea:
            self._apnea_s += dt
        else:
            self._apnea_s = max(0.0, self._apnea_s - 2.5 * dt)

        preox_active = bool(fio2 >= 0.80 and ventilation_ok and not apnea)
        if preox_active:
            target_reservoir = self._clip(0.40 + 0.60 * fio2 * ventilation_quality, 0.0, 1.0)
            tau = max(float(self.params["reservoir_build_tau_s"]), 1.0)
        else:
            target_reservoir = self._clip(0.18 + 0.35 * fio2 * max(ventilation_quality, 0.10), 0.0, 1.0)
            tau = max(float(self.params["reservoir_decay_tau_s"]), 1.0)
        self._reservoir += (target_reservoir - self._reservoir) * min(dt / tau, 1.0) if dt > 0.0 else 0.0
        self._reservoir = self._clip(self._reservoir, 0.0, 1.0)

        frc_factor = self._clip(frc / max(30.0 * wt, 1.0), 0.45, 1.6)
        safe_apnea = float(self.params["safe_apnea_base_s"]) * (0.45 + 0.90 * self._reservoir) * frc_factor
        safe_remaining = max(safe_apnea - self._apnea_s, 0.0)

        obstruction = self._clip(max(
            self._get(bus, "upper_airway_obstruction_score", 0.0),
            self._get(bus, "laryngospasm_score", 0.0),
            self._get(bus, "airway_obstruction_index", 0.0),
        ), 0.0, 1.0)
        aspiration = self._clip(self._get(bus, "aspiration_risk", 0.0), 0.0, 1.0)
        burden = self._clip((self._apnea_s - 0.50 * safe_apnea) / max(float(self.params["critical_apnea_s"]), 1.0), 0.0, 1.0)
        desat_risk = self._clip(0.55 * burden + 0.22 * (1.0 - self._reservoir) + 0.16 * obstruction + 0.10 * aspiration + 0.10 * rsi_suppression, 0.0, 1.0)
        desat_slope = self._clip(float(self.params["desat_gain"]) * desat_risk * (1.15 - 0.60 * self._reservoir), 0.0, 0.08)

        if apnea and dt > 0.0 and desat_risk > 0.05:
            sao2 = self._clip(sao2 - desat_slope * dt, 0.35, 1.0)
            pao2 = self._clip(pao2 - (2.0 + 10.0 * desat_risk) * dt, 18.0, 560.0)
        elif ventilation_ok and fio2 >= 0.50 and dt > 0.0:
            recovery = float(self.params["oxygenation_recovery_gain"]) * ventilation_quality * dt
            sao2 = self._clip(sao2 + recovery * max(0.985 - sao2, 0.0), 0.05, 1.0)
            pao2 = self._clip(pao2 + 0.30 * recovery * max(120.0 * fio2 - pao2, 0.0), 10.0, 560.0)

        if apnea:
            phase = "apnea"
        elif preox_active:
            phase = "preoxygenation"
        elif rsi_active:
            phase = "rsi_recovery"
        elif str(self._get(bus, "airway_rescue_state", "stable")) in {"failed_attempt", "rescued_BVM"}:
            phase = "airway_rescue"
        else:
            phase = "stable"

        if desat_risk >= 0.70:
            warning = "high peri-intubation desaturation risk"
        elif apnea and safe_remaining <= 15.0:
            warning = "apnea reservoir nearly exhausted"
        elif rsi_active and not ventilation_ok:
            warning = "RSI suppression with ineffective ventilation"
        else:
            warning = "none"

        bus.update({
            "intubation_physiology_revision": self.REVISION,
            "preoxygenation_active": bool(preox_active),
            "preoxygenation_reservoir": float(self._reservoir),
            "apnea_active": bool(apnea),
            "apnea_timer_s": float(self._apnea_s),
            "safe_apnea_time_remaining_s": float(safe_remaining),
            "rsi_effect_active": bool(rsi_active),
            "rsi_resp_suppression_index": float(rsi_suppression),
            "peri_intubation_desaturation_risk": float(desat_risk),
            "peri_intubation_desaturation_slope": float(desat_slope),
            "peri_intubation_phase": phase,
            "peri_intubation_warning": warning,
            "SaO2": float(sao2),
            "PaO2": float(pao2),
        })

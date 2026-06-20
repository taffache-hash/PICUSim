"""
Shock Engine — v3.1 Step 4.39
================================

Educational pediatric shock phenotype module.  It converts scenario-level
shock drivers into coupled modifiers for circulation, heart rate/contractility,
preload, sympathetic compensation and lactate kinetics.

This is a simulation scaffold, not a clinical decision tool.  Values are
qualitative and bounded to preserve numerical stability.
"""

from __future__ import annotations

import numpy as np
from typing import List

from core.base_module import BaseModule
from core.bus import PhysiologicalBus


class ShockModule(BaseModule):
    """Composite pediatric shock phenotype engine.

    Supported phenotypes
    --------------------
    * distributive: vasoplegia + capillary leak + warm/cold sepsis coupling
    * hypovolemic: preload loss with compensatory SVR/HR rise
    * cardiogenic: contractility loss with low-output lactate signal
    * obstructive: preload/venous-return impairment and RV-afterload coupling
    * mixed: weighted blend driven by the individual indices

    Scenario authors can set ``shock_type`` and ``shock_severity`` directly,
    or set phenotype-specific indices. The module writes only modifier fields;
    Circulation/Heart/metabolic modules remain owners of final MAP/CO/lactate.
    """

    DEFAULT_PARAMS = {
        "MAP_low_threshold": 55.0,
        "perfusion_pressure_low_threshold": 45.0,
        "sympathetic_gain": 0.75,
        "lactate_gain": 2.2,
        "decompensation_tau_s": 25.0,
    }

    def __init__(self, params: dict | None = None):
        super().__init__(name="ShockEngine", params={**self.DEFAULT_PARAMS, **(params or {})})
        self._decomp = 0.0

    @property
    def input_keys(self) -> List[str]:
        return [
            "shock_type", "shock_severity", "shock_vasoplegia_index",
            "shock_hypovolemia_index", "shock_low_output_index", "shock_obstruction_index",
            "MAP", "CVP", "CO", "SV", "HR", "lactate",
            "infection_load", "vasoplegia_index", "myocardial_depression_index",
            "endothelial_leak_index", "capillary_leak_index", "fluid_balance",
            "RV_afterload_index", "PEEP_hemodynamic_penalty", "cardiac_arrest_active",
        ]

    @property
    def output_keys(self) -> List[str]:
        return [
            "shock_engine_revision", "shock_type", "shock_severity", "shock_stage",
            "shock_SVR_mod", "shock_preload_mod", "shock_contractility_mod",
            "shock_HR_add", "shock_lactate_prod_mod", "shock_lactate_clearance_mod",
            "shock_sympathetic_tone", "shock_decompensation_index",
            "shock_vasoplegia_index", "shock_hypovolemia_index",
            "shock_low_output_index", "shock_obstruction_index",
            "shock_perfusion_pressure_mmHg",
        ]

    @staticmethod
    def _clip(x: float, lo: float, hi: float) -> float:
        return float(np.clip(float(x), lo, hi))

    def initialize(self, bus: PhysiologicalBus) -> None:
        self._decomp = self._clip(bus.get("shock_decompensation_index") if hasattr(bus.state, "shock_decompensation_index") else 0.0, 0.0, 1.0)

    def _infer_indices(self, bus: PhysiologicalBus, shock_type: str, severity: float) -> tuple[float, float, float, float]:
        vasoplegia = self._clip(bus.get("shock_vasoplegia_index"), 0.0, 1.0)
        hypovolemia = self._clip(bus.get("shock_hypovolemia_index"), 0.0, 1.0)
        low_output = self._clip(bus.get("shock_low_output_index"), 0.0, 1.0)
        obstruction = self._clip(bus.get("shock_obstruction_index"), 0.0, 1.0)

        infection = self._clip(bus.get("infection_load") if hasattr(bus.state, "infection_load") else 0.0, 0.0, 1.0)
        sepsis_vaso = self._clip(bus.get("vasoplegia_index") if hasattr(bus.state, "vasoplegia_index") else 0.0, 0.0, 1.0)
        septic_myocardial = self._clip(bus.get("myocardial_depression_index") if hasattr(bus.state, "myocardial_depression_index") else 0.0, 0.0, 1.0)
        leak = self._clip(max(
            bus.get("endothelial_leak_index") if hasattr(bus.state, "endothelial_leak_index") else 0.0,
            bus.get("capillary_leak_index") if hasattr(bus.state, "capillary_leak_index") else 0.0,
        ), 0.0, 1.0)
        rv_afterload = self._clip(bus.get("RV_afterload_index") if hasattr(bus.state, "RV_afterload_index") else 0.0, 0.0, 1.0)
        peep_penalty = self._clip(bus.get("PEEP_hemodynamic_penalty") if hasattr(bus.state, "PEEP_hemodynamic_penalty") else 0.0, 0.0, 1.0)
        fluid_balance = float(bus.get("fluid_balance") if hasattr(bus.state, "fluid_balance") else 0.0)
        dehydration = self._clip(-fluid_balance / max(bus.get("blood_volume_mL") if hasattr(bus.state, "blood_volume_mL") else 1600.0, 100.0), 0.0, 1.0)

        if shock_type in ("distributive", "septic"):
            vasoplegia = max(vasoplegia, severity, infection, sepsis_vaso)
            hypovolemia = max(hypovolemia, 0.45 * leak)
            low_output = max(low_output, 0.45 * septic_myocardial)
        elif shock_type in ("hypovolemic", "hemorrhagic"):
            hypovolemia = max(hypovolemia, severity, dehydration)
        elif shock_type == "cardiogenic":
            low_output = max(low_output, severity, septic_myocardial)
        elif shock_type == "obstructive":
            obstruction = max(obstruction, severity, rv_afterload, peep_penalty)
            hypovolemia = max(hypovolemia, 0.35 * severity)
        elif shock_type == "mixed":
            vasoplegia = max(vasoplegia, 0.55 * severity, infection, sepsis_vaso)
            hypovolemia = max(hypovolemia, 0.45 * severity, dehydration, 0.35 * leak)
            low_output = max(low_output, 0.45 * severity, septic_myocardial)
            obstruction = max(obstruction, 0.35 * severity, rv_afterload)

        return tuple(self._clip(x, 0.0, 1.0) for x in (vasoplegia, hypovolemia, low_output, obstruction))

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        shock_type = str(bus.get("shock_type") if hasattr(bus.state, "shock_type") else "none").lower()
        severity_in = self._clip(bus.get("shock_severity") if hasattr(bus.state, "shock_severity") else 0.0, 0.0, 1.0)
        if shock_type in ("", "none", "normal") and severity_in <= 0.0:
            # decay previous decompensation rather than abruptly zeroing it
            tau = max(float(self.params["decompensation_tau_s"]), 1.0)
            self._decomp += (0.0 - self._decomp) * min(dt / tau, 1.0)
            bus.update({
                "shock_engine_revision": 439,
                "shock_type": "none",
                "shock_severity": 0.0,
                "shock_stage": "none",
                "shock_SVR_mod": 1.0,
                "shock_preload_mod": 1.0,
                "shock_contractility_mod": 1.0,
                "shock_HR_add": 0.0,
                "shock_lactate_prod_mod": 1.0,
                "shock_lactate_clearance_mod": 1.0,
                "shock_sympathetic_tone": 1.0,
                "shock_decompensation_index": float(self._decomp),
                "shock_perfusion_pressure_mmHg": float(bus.get("MAP") - bus.get("CVP")),
            })
            return

        vasoplegia, hypovolemia, low_output, obstruction = self._infer_indices(bus, shock_type, severity_in)
        severity = self._clip(max(severity_in, vasoplegia, hypovolemia, low_output, obstruction), 0.0, 1.0)

        MAP = float(bus.get("MAP"))
        CVP = float(bus.get("CVP"))
        perfusion_pressure = MAP - CVP
        pressure_deficit = self._clip((self.params["perfusion_pressure_low_threshold"] - perfusion_pressure) / 30.0, 0.0, 1.0)
        lactate = float(bus.get("lactate") if hasattr(bus.state, "lactate") else 1.0)
        lactate_signal = self._clip((lactate - 2.0) / 6.0, 0.0, 1.0)
        target_decomp = self._clip(0.55 * severity + 0.30 * pressure_deficit + 0.15 * lactate_signal, 0.0, 1.0)
        tau = max(float(self.params["decompensation_tau_s"]), 1.0)
        self._decomp += (target_decomp - self._decomp) * min(dt / tau, 1.0)
        decomp = self._clip(self._decomp, 0.0, 1.0)

        sympathetic = 1.0 + self.params["sympathetic_gain"] * severity * (1.0 - 0.45 * decomp)
        HR_add = 55.0 * severity * (1.0 - 0.35 * decomp)

        SVR_mod = (1.0 - 0.62 * vasoplegia) * (1.0 + 0.45 * hypovolemia) * (1.0 + 0.25 * low_output)
        preload_mod = (1.0 - 0.55 * hypovolemia) * (1.0 - 0.48 * obstruction)
        contractility_mod = (1.0 - 0.50 * low_output) * (1.0 - 0.22 * decomp)

        lactate_prod = 1.0 + self.params["lactate_gain"] * (0.45 * hypovolemia + 0.45 * low_output + 0.35 * obstruction + 0.30 * vasoplegia + 0.35 * decomp)
        lactate_clear = 1.0 - 0.38 * decomp - 0.18 * low_output

        if decomp < 0.25:
            stage = "compensated" if severity > 0.05 else "none"
        elif decomp < 0.60:
            stage = "decompensated"
        else:
            stage = "critical"

        bus.update({
            "shock_engine_revision": 439,
            "shock_type": shock_type if shock_type not in ("septic", "hemorrhagic") else {"septic": "distributive", "hemorrhagic": "hypovolemic"}[shock_type],
            "shock_severity": float(severity),
            "shock_stage": stage,
            "shock_SVR_mod": self._clip(SVR_mod, 0.25, 2.4),
            "shock_preload_mod": self._clip(preload_mod, 0.25, 1.15),
            "shock_contractility_mod": self._clip(contractility_mod, 0.25, 1.10),
            "shock_HR_add": self._clip(HR_add, 0.0, 70.0),
            "shock_lactate_prod_mod": self._clip(lactate_prod, 1.0, 4.5),
            "shock_lactate_clearance_mod": self._clip(lactate_clear, 0.35, 1.0),
            "shock_sympathetic_tone": self._clip(sympathetic, 1.0, 1.75),
            "shock_decompensation_index": float(decomp),
            "shock_vasoplegia_index": float(vasoplegia),
            "shock_hypovolemia_index": float(hypovolemia),
            "shock_low_output_index": float(low_output),
            "shock_obstruction_index": float(obstruction),
            "shock_perfusion_pressure_mmHg": float(perfusion_pressure),
        })

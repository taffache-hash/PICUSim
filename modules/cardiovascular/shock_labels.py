"""
ShockLabelModule — v3.2 public-polish
=====================================

Lightweight educational shock-label module.

It updates shock_type/shock_stage/shock_severity from scenario metadata and
current physiology, but deliberately does not write hemodynamic modifiers.
The existing ShockModule remains available for explicit mechanistic shock
experiments; this label module is safer for public scenarios where the
cardiovascular physiology is already produced by sepsis, circulation,
ventilator and recovery modules.
"""

from __future__ import annotations

from typing import List
import numpy as np

from core.base_module import BaseModule
from core.bus import PhysiologicalBus


class ShockLabelModule(BaseModule):
    DEFAULT_PARAMS = {
        "MAP_low_threshold": 55.0,
        "MAP_critical_threshold": 35.0,
        "lactate_compensated": 2.0,
        "lactate_critical": 5.0,
    }

    def __init__(self, params: dict | None = None):
        super().__init__(name="ShockLabels", params={**self.DEFAULT_PARAMS, **(params or {})})

    @property
    def input_keys(self) -> List[str]:
        return [
            "shock_type", "shock_severity", "MAP", "CVP", "CO", "HR", "lactate",
            "infection_load", "sepsis_severity_score", "SaO2", "cardiac_arrest_active", "age_y", "weight_kg",
        ]

    @property
    def output_keys(self) -> List[str]:
        return ["shock_type", "shock_stage", "shock_severity", "shock_perfusion_pressure_mmHg"]

    def initialize(self, bus: PhysiologicalBus) -> None:
        self.step(bus, 0.0)

    @staticmethod
    def _clip(x: float, lo: float, hi: float) -> float:
        return float(np.clip(float(x), lo, hi))

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        shock_type = str(bus.get("shock_type") if hasattr(bus.state, "shock_type") else "none").lower()
        if shock_type in ("", "normal"):
            shock_type = "none"

        MAP = float(bus.get("MAP")) if hasattr(bus.state, "MAP") else 70.0
        age_y = float(bus.get("age_y")) if hasattr(bus.state, "age_y") else 6.0
        weight_kg = float(bus.get("weight_kg")) if hasattr(bus.state, "weight_kg") else 20.0
        if weight_kg <= 4.5 or age_y < 0.25:
            map_low_threshold = 38.0
            map_critical_threshold = 28.0
        elif age_y < 1.0:
            map_low_threshold = 45.0
            map_critical_threshold = 32.0
        else:
            map_low_threshold = float(self.params["MAP_low_threshold"])
            map_critical_threshold = float(self.params["MAP_critical_threshold"])
        CVP = float(bus.get("CVP")) if hasattr(bus.state, "CVP") else 5.0
        CO = float(bus.get("CO")) if hasattr(bus.state, "CO") else 4.0
        lactate = float(bus.get("lactate")) if hasattr(bus.state, "lactate") else 1.0
        infection = float(bus.get("infection_load")) if hasattr(bus.state, "infection_load") else 0.0
        sepsis_score = float(bus.get("sepsis_severity_score")) if hasattr(bus.state, "sepsis_severity_score") else 0.0
        sao2 = float(bus.get("SaO2")) if hasattr(bus.state, "SaO2") else 0.98
        arrest = bool(bus.get("cardiac_arrest_active")) if hasattr(bus.state, "cardiac_arrest_active") else False

        map_deficit = self._clip((map_low_threshold - MAP) / max(map_low_threshold - map_critical_threshold, 10.0), 0.0, 1.0)
        lactate_signal = self._clip((lactate - float(self.params["lactate_compensated"])) / max(float(self.params["lactate_critical"]) - float(self.params["lactate_compensated"]), 0.1), 0.0, 1.0)
        hypoxemia_signal = self._clip((0.90 - sao2) / 0.20, 0.0, 1.0)
        expected_co = max(0.18 * max(weight_kg, 1.0), 0.55)
        low_co_signal = self._clip((0.55 * expected_co - CO) / max(0.55 * expected_co, 0.1), 0.0, 1.0)
        scenario_severity = self._clip(bus.get("shock_severity") if hasattr(bus.state, "shock_severity") else 0.0, 0.0, 1.0)

        if shock_type == "none" and (infection >= 0.4 or sepsis_score >= 0.25):
            shock_type = "distributive"
        elif shock_type == "none" and (map_deficit > 0.25 or lactate_signal > 0.25 or low_co_signal > 0.30):
            shock_type = "mixed"

        severity = self._clip(max(
            scenario_severity * 0.75,
            map_deficit,
            0.75 * lactate_signal,
            0.65 * low_co_signal,
            0.45 * hypoxemia_signal,
            0.45 * infection,
            0.60 * sepsis_score,
        ), 0.0, 1.0)

        if shock_type == "none" and severity < 0.30 and not arrest:
            stage = "none"
            severity = 0.0
        elif shock_type == "none":
            shock_type = "mixed"
            stage = "critical" if (arrest or MAP <= map_critical_threshold or severity >= 0.75) else "decompensated"
        elif shock_type == "mixed" and severity < 0.30 and not arrest:
            shock_type = "none"
            stage = "none"
            severity = 0.0
        elif arrest or MAP <= map_critical_threshold or severity >= 0.75:
            stage = "critical"
        elif severity >= 0.45 or MAP < map_low_threshold:
            stage = "decompensated"
        else:
            stage = "compensated"

        bus.update({
            "shock_type": shock_type,
            "shock_stage": stage,
            "shock_severity": float(severity),
            "shock_perfusion_pressure_mmHg": float(MAP - CVP),
        })

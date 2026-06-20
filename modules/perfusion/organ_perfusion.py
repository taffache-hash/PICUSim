"""
Organ Perfusion Model — v3.1 Step 4.42
=======================================

Educational pediatric organ-perfusion layer coupling systemic pressure/flow,
shock state and venous congestion to renal and hepatic perfusion surrogates.

The module writes bounded, qualitative modifiers and slow-moving lab proxies:
renal perfusion, hepatic perfusion, urine output, creatinine trajectory and
lactate clearance. It is not a diagnostic, dosing, or clinical decision tool.
"""

from __future__ import annotations

from typing import List
import numpy as np

from core.base_module import BaseModule
from core.bus import PhysiologicalBus


class OrganPerfusionModule(BaseModule):
    """MAP-threshold adjusted renal/hepatic perfusion and output model."""

    REVISION = 442

    DEFAULT_PARAMS = {
        "renal_autoreg_width_mmHg": 28.0,
        "hepatic_autoreg_width_mmHg": 34.0,
        "creatinine_tau_s": 7200.0,
        "urine_tau_s": 240.0,
        "lactate_clearance_min": 0.35,
        "lactate_clearance_max": 1.10,
    }

    def __init__(self, params: dict | None = None):
        super().__init__(name="OrganPerfusion", params={**self.DEFAULT_PARAMS, **(params or {})})
        self._creatinine = 0.35
        self._urine_mL_kg_h = 1.0
        self._hypoperfusion_burden = 0.0

    @property
    def input_keys(self) -> List[str]:
        return [
            "age_y", "weight_kg", "MAP", "CVP", "CO", "SaO2", "PaO2", "lactate",
            "shock_severity", "shock_stage", "shock_low_output_index", "shock_hypovolemia_index",
            "shock_vasoplegia_index", "shock_obstruction_index", "shock_lactate_clearance_mod",
            "microcirculatory_failure_index", "infection_load", "sepsis_GFR_mod",
            "renal_hypoperfusion_index", "hepatic_perfusion_index", "hepatic_lactate_clearance_mod",
            "creatinine_mg_dL", "creatinine_baseline_mg_dL", "urine_output_mL_kg_h", "urine_rate_mL_h",
            "furosemide_urine_gain", "CRRT_active", "cardiac_arrest_active", "CPR_active", "CPR_quality",
        ]

    @property
    def output_keys(self) -> List[str]:
        return [
            "organ_perfusion_revision", "organ_perfusion_pressure_mmHg",
            "pediatric_MAP_low_threshold_mmHg", "renal_perfusion_index", "hepatic_perfusion_index",
            "renal_hypoperfusion_index", "hepatic_hypoperfusion_index", "organ_hypoperfusion_burden",
            "urine_output_mL_kg_h", "urine_rate_mL_h", "creatinine_mg_dL", "creatinine_ratio",
            "organ_lactate_clearance_mod", "hepatic_lactate_clearance_mod", "GFR_mod_from_perfusion",
            "renal_warning", "hepatic_warning",
        ]

    @staticmethod
    def _clip(x: float, lo: float, hi: float) -> float:
        return float(np.clip(float(x), lo, hi))

    @staticmethod
    def _get(bus: PhysiologicalBus, key: str, default):
        return getattr(bus.state, key, default)

    def _map_threshold(self, age_y: float) -> float:
        # Conservative educational lower MAP anchor: neonates/infants lower,
        # school-age children/adolescents progressively closer to adult values.
        if age_y < 0.08:   # ~first month
            return 38.0
        if age_y < 1.0:
            return 45.0
        if age_y < 5.0:
            return 50.0
        if age_y < 12.0:
            return 55.0
        return 60.0

    def initialize(self, bus: PhysiologicalBus) -> None:
        self._creatinine = self._clip(self._get(bus, "creatinine_mg_dL", 0.35), 0.10, 6.0)
        self._urine_mL_kg_h = self._clip(self._get(bus, "urine_output_mL_kg_h", 1.0), 0.0, 8.0)
        self._hypoperfusion_burden = self._clip(self._get(bus, "organ_hypoperfusion_burden", 0.0), 0.0, 1.0)
        self.step(bus, 0.0)

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        dt = max(float(dt), 0.0)
        age = max(float(self._get(bus, "age_y", 6.0)), 0.0)
        wt = max(float(self._get(bus, "weight_kg", 20.0)), 1.0)
        MAP = float(self._get(bus, "MAP", 65.0))
        CVP = float(self._get(bus, "CVP", 5.0))
        CO = max(float(self._get(bus, "CO", 0.18 * wt)), 0.05)
        SaO2 = self._clip(self._get(bus, "SaO2", 0.97), 0.05, 1.0)
        PaO2 = max(float(self._get(bus, "PaO2", 90.0)), 10.0)
        lactate = max(float(self._get(bus, "lactate", 1.0)), 0.2)

        map_low = self._map_threshold(age)
        perf_pressure = MAP - CVP
        pressure_score = self._clip((perf_pressure - (map_low - 8.0)) / max(float(self.params["renal_autoreg_width_mmHg"]), 1.0), 0.0, 1.25)
        flow_score = self._clip(CO / max(0.12 * wt, 0.5), 0.05, 1.35)
        oxygen_score = self._clip(0.70 * SaO2 + 0.30 * self._clip(PaO2 / 90.0, 0.2, 1.2), 0.1, 1.15)
        congestion_penalty = self._clip((CVP - 8.0) / 14.0, 0.0, 0.55)

        shock_sev = self._clip(self._get(bus, "shock_severity", 0.0), 0.0, 1.0)
        low_output = self._clip(self._get(bus, "shock_low_output_index", 0.0), 0.0, 1.0)
        hypo = self._clip(self._get(bus, "shock_hypovolemia_index", 0.0), 0.0, 1.0)
        vaso = self._clip(self._get(bus, "shock_vasoplegia_index", 0.0), 0.0, 1.0)
        obstruction = self._clip(self._get(bus, "shock_obstruction_index", 0.0), 0.0, 1.0)
        micro = self._clip(self._get(bus, "microcirculatory_failure_index", 0.0), 0.0, 1.0)
        arrest_penalty = 0.55 if bool(self._get(bus, "cardiac_arrest_active", False)) else 0.0
        if bool(self._get(bus, "CPR_active", False)):
            arrest_penalty *= 1.0 - 0.55 * self._clip(self._get(bus, "CPR_quality", 0.0), 0.0, 1.0)

        systemic = self._clip(0.52 * pressure_score + 0.33 * flow_score + 0.15 * oxygen_score - congestion_penalty, 0.0, 1.20)
        renal_penalty = 0.25 * hypo + 0.18 * low_output + 0.16 * vaso + 0.12 * micro + arrest_penalty
        hepatic_penalty = 0.18 * low_output + 0.16 * vaso + 0.14 * obstruction + 0.22 * micro + 0.10 * shock_sev + arrest_penalty
        renal_perf = self._clip(systemic - renal_penalty, 0.02, 1.15)
        hepatic_perf = self._clip(systemic - hepatic_penalty + 0.06 * (1.0 - hypo), 0.03, 1.15)

        renal_hypo = self._clip(1.0 - renal_perf, 0.0, 1.0)
        hepatic_hypo = self._clip(1.0 - hepatic_perf, 0.0, 1.0)
        target_burden = self._clip(0.55 * renal_hypo + 0.35 * hepatic_hypo + 0.10 * self._clip((lactate - 2.0) / 6.0, 0.0, 1.0), 0.0, 1.0)
        self._hypoperfusion_burden += (target_burden - self._hypoperfusion_burden) * min(dt / 180.0, 1.0) if dt > 0 else 0.0

        # Urine output is pressure/flow dependent, with furosemide allowed only
        # to express if renal perfusion remains adequate.
        diuretic_gain = self._clip(self._get(bus, "furosemide_urine_gain", 1.0), 0.3, 4.0)
        target_urine = self._clip(1.25 * renal_perf * diuretic_gain * (1.0 - 0.55 * renal_hypo), 0.0, 6.0)
        self._urine_mL_kg_h += (target_urine - self._urine_mL_kg_h) * min(dt / max(float(self.params["urine_tau_s"]), 1.0), 1.0) if dt > 0 else 0.0
        urine_rate = self._urine_mL_kg_h * wt

        # Creatinine rises slowly with hypoperfusion and low urine output;
        # CRRT caps visible rise in this educational layer.
        baseline_creat = self._clip(self._get(bus, "creatinine_baseline_mg_dL", 0.35), 0.10, 2.0)
        crrt_active = bool(self._get(bus, "CRRT_active", False))
        target_creat = baseline_creat * (1.0 + 2.7 * renal_hypo + 0.6 * self._clip(0.5 - self._urine_mL_kg_h, 0.0, 0.5))
        if crrt_active:
            target_creat = min(target_creat, max(self._creatinine, baseline_creat * 1.15))
        self._creatinine += (target_creat - self._creatinine) * min(dt / max(float(self.params["creatinine_tau_s"]), 1.0), 1.0) if dt > 0 else 0.0
        self._creatinine = self._clip(self._creatinine, 0.10, 8.0)
        creat_ratio = self._clip(self._creatinine / max(baseline_creat, 0.05), 0.2, 12.0)

        shock_lac_clear = self._clip(self._get(bus, "shock_lactate_clearance_mod", 1.0), 0.30, 1.20)
        hepatic_lac = self._clip(0.40 + 0.65 * hepatic_perf - 0.22 * micro - 0.10 * low_output, 0.25, 1.10)
        organ_lac_clear = self._clip(shock_lac_clear * hepatic_lac, float(self.params["lactate_clearance_min"]), float(self.params["lactate_clearance_max"]))
        gfr_mod = self._clip(0.20 + 0.90 * renal_perf - 0.18 * micro, 0.10, 1.20)

        renal_warning = "none"
        if renal_hypo >= 0.65 or self._urine_mL_kg_h < 0.3:
            renal_warning = "severe renal hypoperfusion/oliguria risk"
        elif renal_hypo >= 0.35 or self._urine_mL_kg_h < 0.5:
            renal_warning = "renal perfusion reduced"

        hepatic_warning = "none"
        if hepatic_hypo >= 0.65:
            hepatic_warning = "severe hepatic hypoperfusion/lactate clearance risk"
        elif hepatic_hypo >= 0.35:
            hepatic_warning = "hepatic perfusion reduced"

        bus.update({
            "organ_perfusion_revision": self.REVISION,
            "organ_perfusion_pressure_mmHg": float(perf_pressure),
            "pediatric_MAP_low_threshold_mmHg": float(map_low),
            "renal_perfusion_index": float(renal_perf),
            "hepatic_perfusion_index": float(hepatic_perf),
            "renal_hypoperfusion_index": float(renal_hypo),
            "hepatic_hypoperfusion_index": float(hepatic_hypo),
            "organ_hypoperfusion_burden": float(self._hypoperfusion_burden),
            "urine_output_mL_kg_h": float(self._urine_mL_kg_h),
            "urine_rate_mL_h": float(urine_rate),
            "creatinine_mg_dL": float(self._creatinine),
            "creatinine_ratio": float(creat_ratio),
            "organ_lactate_clearance_mod": float(organ_lac_clear),
            "hepatic_lactate_clearance_mod": float(organ_lac_clear),
            "GFR_mod_from_perfusion": float(gfr_mod),
            "renal_warning": renal_warning,
            "hepatic_warning": hepatic_warning,
        })

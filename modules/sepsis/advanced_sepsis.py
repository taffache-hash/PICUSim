"""
Advanced Sepsis Module — v0.14
==============================

Qualitative pediatric sepsis/shock phenotyping layer.

It does not replace the cardiovascular, metabolic, renal or coagulation
modules. It computes physiologic modifiers that are then consumed downstream:

  - vasoplegia_index / sepsis_SVR_mod
  - myocardial_depression_index / sepsis_CO_mod
  - endothelial_leak_index / capillary leak
  - microcirculatory_failure_index / lactate generation
  - sepsis_VO2_mod and sepsis_HR_add

Supported phenotypes:
  warm, cold, mixed, vasoplegic, myocardial

Interventions:
  source control / antibiotics as slow reduction of infection load,
  norepinephrine/adrenaline/vasopressin/hydrocortisone as modifiers.

This is intended for educational / exploratory simulation, not for prediction.
"""
from __future__ import annotations

import numpy as np
from typing import List

from core.base_module import BaseModule
from core.bus import PhysiologicalBus


class AdvancedSepsisModule(BaseModule):
    DEFAULT_PARAMS = {
        "infection_load": 0.0,          # [0-1]
        "phenotype": "mixed",          # warm|cold|mixed|vasoplegic|myocardial
        "source_control": 0.0,          # [0-1]
        "antibiotic_effect": 0.0,       # [0-1]
        "cytokine_tau_s": 420.0,        # inflammatory inertia
        "resolution_tau_s": 7200.0,     # slow infection resolution
        "baseline_cytokine": 0.0,
    }

    @property
    def input_keys(self) -> List[str]:
        return [
            "infection_load", "source_control", "antibiotic_effect", "T_core",
            "MAP", "lactate", "DO2", "VO2", "norad_mcg_kg_min",
            "adrenaline_mcg_kg_min", "vasopressin_mU_kg_min",
            "hydrocortisone_mg_kg_h", "hydrocortisone_antiinflammatory_signal",
            "hydrocortisone_vasopressor_sensitization_signal",
            "dexamethasone_antiinflammatory_signal", "milrinone_mcg_kg_min",
        ]

    @property
    def output_keys(self) -> List[str]:
        return [
            "cytokine_drive", "vasoplegia_index", "myocardial_depression_index",
            "endothelial_leak_index", "microcirculatory_failure_index",
            "sepsis_SVR_mod", "sepsis_CO_mod", "sepsis_HR_add", "sepsis_VO2_mod",
            "sepsis_lactate_prod_mod", "sepsis_GFR_mod", "sepsis_coag_mod",
            "sepsis_severity_score",
        ]

    def __init__(self, params: dict | None = None):
        merged = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(name="AdvancedSepsis", params=merged)
        self._infection_load = float(merged["infection_load"])
        self._cytokine = float(merged.get("baseline_cytokine", self._infection_load * 0.5))
        self._phenotype = str(merged.get("phenotype", "mixed")).lower()

    def initialize(self, bus: PhysiologicalBus) -> None:
        self._infection_load = float(bus.get("infection_load")) if hasattr(bus.state, "infection_load") else float(self.params["infection_load"])
        self._cytokine = float(np.clip(max(bus.get("cytokine_drive") if hasattr(bus.state, "cytokine_drive") else 0.0,
                                           self._infection_load * 0.45), 0.0, 1.0))
        bus.update({
            "infection_load": float(self._infection_load),
            "cytokine_drive": float(self._cytokine),
            "sepsis_phenotype_code": self._phenotype,
        })

    def _weights(self) -> tuple[float, float]:
        ph = self._phenotype
        if ph == "warm":
            return 0.85, 0.25
        if ph == "cold":
            return 0.35, 0.75
        if ph == "vasoplegic":
            return 1.00, 0.20
        if ph == "myocardial":
            return 0.30, 1.00
        return 0.65, 0.55

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        # Allow timeline perturbations to change infection/source-control.
        self._infection_load = float(np.clip(bus.get("infection_load"), 0.0, 1.0))
        source_control = float(np.clip(bus.get("source_control"), 0.0, 1.0))
        antibiotic_effect = float(np.clip(bus.get("antibiotic_effect"), 0.0, 1.0))

        # Slow infection resolution after antibiotics/source control.
        resolution = (0.15 + 0.85 * source_control) * antibiotic_effect
        if resolution > 0:
            tau_res = max(float(self.params["resolution_tau_s"]), 60.0)
            self._infection_load = float(np.clip(self._infection_load - self._infection_load * resolution * dt / tau_res, 0.0, 1.0))
            bus.set("infection_load", self._infection_load)

        T = float(bus.get("T_core"))
        MAP = float(bus.get("MAP"))
        lactate = float(bus.get("lactate"))
        DO2 = float(bus.get("DO2"))
        VO2 = float(bus.get("VO2"))
        norad = float(bus.get("norad_mcg_kg_min"))
        adr = float(bus.get("adrenaline_mcg_kg_min"))
        vaso = float(bus.get("vasopressin_mU_kg_min"))
        hydro = float(bus.get("hydrocortisone_mg_kg_h"))
        # Step 3.7 contract: steroids affect sepsis only through delayed PD
        # signals from SteroidsModule, not through the raw command dose.
        hydro_anti = float(bus.get("hydrocortisone_antiinflammatory_signal")) if hasattr(bus.state, "hydrocortisone_antiinflammatory_signal") else 0.0
        hydro_vaso_sens = float(bus.get("hydrocortisone_vasopressor_sensitization_signal")) if hasattr(bus.state, "hydrocortisone_vasopressor_sensitization_signal") else 0.0
        dexa_anti = float(bus.get("dexamethasone_antiinflammatory_signal")) if hasattr(bus.state, "dexamethasone_antiinflammatory_signal") else 0.0
        steroid_anti = float(np.clip(0.55 * hydro_anti + 0.45 * dexa_anti, 0.0, 1.0))
        milri = float(bus.get("milrinone_mcg_kg_min"))

        fever_drive = np.clip((T - 37.5) / 2.5, 0.0, 1.0)
        shock_drive = np.clip((60.0 - MAP) / 35.0, 0.0, 1.0)
        lact_drive = np.clip((lactate - 2.0) / 6.0, 0.0, 1.0)
        oxygen_debt = np.clip((VO2 - DO2 * 0.35) / max(VO2, 1.0), 0.0, 1.0)

        target_cyt = float(np.clip(
            0.68 * self._infection_load + 0.12 * fever_drive + 0.10 * shock_drive +
            0.06 * lact_drive + 0.04 * oxygen_debt,
            0.0, 1.0
        ))
        # Steroids blunt inflammatory drive slowly; no immediate cytokine drop
        # from the infusion command itself.
        steroid_blunt = 1.0 - 0.22 * steroid_anti
        target_cyt *= float(np.clip(steroid_blunt, 0.72, 1.0))

        alpha = 1.0 - np.exp(-dt / float(self.params["cytokine_tau_s"]))
        self._cytokine += alpha * (target_cyt - self._cytokine)
        self._cytokine = float(np.clip(self._cytokine, 0.0, 1.0))

        w_vaso, w_myo = self._weights()
        vaso_treat = 0.42 * vaso / (0.08 + max(vaso, 0.0)) if vaso > 0 else 0.0
        hydro_treat = 0.22 * hydro_vaso_sens
        catechol_treat = 0.12 * norad / (0.20 + max(norad, 0.0)) if norad > 0 else 0.0
        vasoplegia = self._cytokine * w_vaso * (1.0 - vaso_treat - hydro_treat - catechol_treat)
        vasoplegia = float(np.clip(vasoplegia, 0.0, 0.90))

        adr_support = 0.35 * adr / (0.12 + max(adr, 0.0)) if adr > 0 else 0.0
        milri_support = 0.18 * milri / (0.5 + max(milri, 0.0)) if milri > 0 else 0.0
        myocardial = self._cytokine * w_myo * (1.0 - adr_support - milri_support)
        myocardial = float(np.clip(myocardial, 0.0, 0.85))

        endothelial = float(np.clip(0.72 * self._cytokine + 0.15 * shock_drive + 0.08 * lact_drive, 0.0, 1.0))
        microcirc = float(np.clip(0.50 * self._cytokine + 0.25 * lact_drive + 0.15 * oxygen_debt + 0.10 * shock_drive, 0.0, 1.0))

        sepsis_SVR_mod = float(np.clip(1.0 - 0.62 * vasoplegia, 0.35, 1.10))
        sepsis_CO_mod = float(np.clip(1.0 - 0.45 * myocardial + 0.12 * adr + 0.04 * norad, 0.45, 1.35))
        sepsis_HR_add = float(np.clip(30.0 * self._cytokine + 18.0 * shock_drive + 8.0 * adr, 0.0, 65.0))
        sepsis_VO2_mod = float(np.clip(1.0 + 0.32 * self._cytokine + 0.10 * fever_drive - 0.10 * myocardial, 0.85, 1.65))
        sepsis_lactate_prod_mod = float(np.clip(1.0 + 1.25 * microcirc + 0.45 * shock_drive, 1.0, 3.0))
        sepsis_GFR_mod = float(np.clip(1.0 - 0.35 * microcirc - 0.20 * shock_drive, 0.35, 1.05))
        sepsis_coag_mod = float(np.clip(1.0 + 1.6 * self._cytokine + 1.0 * microcirc, 1.0, 4.0))
        severity = float(np.clip(0.30 * self._infection_load + 0.25 * self._cytokine + 0.18 * vasoplegia + 0.15 * myocardial + 0.12 * microcirc, 0.0, 1.0))

        bus.update({
            "cytokine_drive": self._cytokine,
            "vasoplegia_index": vasoplegia,
            "myocardial_depression_index": myocardial,
            "endothelial_leak_index": endothelial,
            "microcirculatory_failure_index": microcirc,
            "sepsis_SVR_mod": sepsis_SVR_mod,
            "sepsis_CO_mod": sepsis_CO_mod,
            "sepsis_HR_add": sepsis_HR_add,
            "sepsis_VO2_mod": sepsis_VO2_mod,
            "sepsis_lactate_prod_mod": sepsis_lactate_prod_mod,
            "sepsis_GFR_mod": sepsis_GFR_mod,
            "sepsis_coag_mod": sepsis_coag_mod,
            "sepsis_severity_score": severity,
        })

"""
Endocrine Stress Axis Module — v0.19
====================================

Qualitative pediatric endocrine stress-axis layer for PICU simulation.

Scope
-----
This module models the fast/slow endocrine response to critical illness:

* HPA axis / cortisol activity
* relative adrenal insufficiency during septic shock
* endogenous catecholamine tone
* insulin resistance and stress hyperglycemia
* thyroid / non-thyroidal illness severity marker
* sodium/water tendency from ADH-like stress response

It does NOT attempt to predict laboratory hormone concentrations accurately.
It produces clinically interpretable modifiers consumed by downstream modules:

* endocrine_SVR_mod, endocrine_HR_add     -> circulation/baroreflex
* endocrine_VO2_mod, endocrine_lactate_mod -> metabolism
* endocrine_glucose_prod_mod, insulin_sensitivity_mod -> glucose
* endocrine_GFR_mod, ADH_water_retention_index -> renal/fluid
* adrenal_insufficiency_index and endocrine_severity_score -> scenario reporting
"""
from __future__ import annotations

import numpy as np
from typing import List

from core.base_module import BaseModule
from core.bus import PhysiologicalBus


class EndocrineStressAxisModule(BaseModule):
    DEFAULT_PARAMS = {
        "weight_kg": 20.0,
        "baseline_cortisol_activity": 0.22,    # [0-1]
        "baseline_catecholamine_tone": 0.18,   # [0-1]
        "hpa_tau_s": 900.0,                     # cortisol inertia
        "catechol_tau_s": 120.0,                # faster sympathetic/endocrine tone
        "illness_resolution_tau_s": 7200.0,
    }

    def __init__(self, params: dict | None = None):
        merged = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(name="EndocrineStressAxis", params=merged)
        self._cortisol = float(merged["baseline_cortisol_activity"])
        self._catechol = float(merged["baseline_catecholamine_tone"])
        self._thyroid_suppression = 0.0

    @property
    def input_keys(self) -> List[str]:
        return [
            "MAP", "HR", "T_core", "lactate", "glucose_mmol_L", "pain_score",
            "stress_index", "sedation_score", "cytokine_drive", "infection_load",
            "sepsis_severity_score", "microcirculatory_failure_index",
            "hydrocortisone_mg_kg_h", "dexamethasone_mcg_kg_h",
            "hydrocortisone_adrenal_support_signal",
            "hydrocortisone_antiinflammatory_signal",
            "dexamethasone_antiinflammatory_signal",
            "dexamethasone_ICP_edema_signal",
            "norad_mcg_kg_min", "adrenaline_mcg_kg_min", "vasopressin_mU_kg_min",
            "insulin_UI_h", "insulin_glucose_clearance_signal", "insulin_action_signal",
            "GIR_mg_kg_min", "Na_mmol_L", "fluid_balance", "GFR",
        ]

    @property
    def output_keys(self) -> List[str]:
        return [
            "cortisol_activity", "catecholamine_tone", "HPA_axis_activation",
            "adrenal_insufficiency_index", "critical_illness_steroid_need_index",
            "insulin_resistance_index", "stress_hyperglycemia_index",
            "endocrine_glucose_prod_mod", "insulin_sensitivity_mod",
            "endocrine_SVR_mod", "endocrine_HR_add", "endocrine_VO2_mod",
            "endocrine_lactate_mod", "ADH_water_retention_index",
            "endocrine_GFR_mod", "thyroid_suppression_index",
            "endocrine_severity_score",
        ]

    def initialize(self, bus: PhysiologicalBus) -> None:
        self._cortisol = float(np.clip(bus.get("cortisol_activity") if hasattr(bus.state, "cortisol_activity") else self.params["baseline_cortisol_activity"], 0.0, 1.0))
        self._catechol = float(np.clip(bus.get("catecholamine_tone") if hasattr(bus.state, "catecholamine_tone") else self.params["baseline_catecholamine_tone"], 0.0, 1.0))
        self._thyroid_suppression = float(np.clip(bus.get("thyroid_suppression_index") if hasattr(bus.state, "thyroid_suppression_index") else 0.0, 0.0, 1.0))
        bus.update({
            "cortisol_activity": self._cortisol,
            "catecholamine_tone": self._catechol,
            "HPA_axis_activation": self._cortisol,
            "thyroid_suppression_index": self._thyroid_suppression,
        })

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        MAP = float(bus.get("MAP"))
        T = float(bus.get("T_core"))
        lact = float(bus.get("lactate"))
        glucose = float(bus.get("glucose_mmol_L")) if hasattr(bus.state, "glucose_mmol_L") else 5.0
        pain = float(bus.get("pain_score")) if hasattr(bus.state, "pain_score") else 0.0
        stress = float(bus.get("stress_index")) if hasattr(bus.state, "stress_index") else 0.0
        sedation = float(bus.get("sedation_score")) if hasattr(bus.state, "sedation_score") else 0.0
        cytokine = float(bus.get("cytokine_drive")) if hasattr(bus.state, "cytokine_drive") else 0.0
        infection = float(bus.get("infection_load")) if hasattr(bus.state, "infection_load") else 0.0
        sepsis_sev = float(bus.get("sepsis_severity_score")) if hasattr(bus.state, "sepsis_severity_score") else 0.0
        micro = float(bus.get("microcirculatory_failure_index")) if hasattr(bus.state, "microcirculatory_failure_index") else 0.0
        hydro = float(bus.get("hydrocortisone_mg_kg_h")) if hasattr(bus.state, "hydrocortisone_mg_kg_h") else 0.0
        dexa = float(bus.get("dexamethasone_mcg_kg_h")) if hasattr(bus.state, "dexamethasone_mcg_kg_h") else 0.0
        norad = float(bus.get("norad_mcg_kg_min")) if hasattr(bus.state, "norad_mcg_kg_min") else 0.0
        adr = float(bus.get("adrenaline_mcg_kg_min")) if hasattr(bus.state, "adrenaline_mcg_kg_min") else 0.0
        vaso = float(bus.get("vasopressin_mU_kg_min")) if hasattr(bus.state, "vasopressin_mU_kg_min") else 0.0
        insulin_revision = int(getattr(bus.state, "insulin_effect_revision", 0)) if hasattr(bus.state, "insulin_effect_revision") else 0
        if insulin_revision >= 319:
            insulin_action = float(np.clip(getattr(bus.state, "insulin_action_signal", 0.0), 0.0, 1.0))
        else:
            # Legacy fallback for historical scenarios without PharmacologyModule.
            insulin_action = float(np.clip((bus.get("insulin_UI_h") if hasattr(bus.state, "insulin_UI_h") else 0.0) / 1.0, 0.0, 1.0))
        Na = float(bus.get("Na_mmol_L")) if hasattr(bus.state, "Na_mmol_L") else 138.0
        fluid_balance = float(bus.get("fluid_balance")) if hasattr(bus.state, "fluid_balance") else 0.0

        shock_drive = np.clip((62.0 - MAP) / 35.0, 0.0, 1.0)
        fever_drive = np.clip((T - 37.5) / 2.5, 0.0, 1.0)
        lact_drive = np.clip((lact - 2.0) / 6.0, 0.0, 1.0)
        pain_drive = np.clip(pain / 10.0, 0.0, 1.0)
        glucotoxic_drive = np.clip((glucose - 10.0) / 12.0, 0.0, 1.0)
        hypogly_drive = np.clip((3.5 - glucose) / 2.0, 0.0, 1.0)

        illness_drive = float(np.clip(
            0.24 * shock_drive + 0.18 * cytokine + 0.14 * infection +
            0.12 * sepsis_sev + 0.10 * lact_drive + 0.08 * fever_drive +
            0.08 * pain_drive + 0.06 * hypogly_drive,
            0.0, 1.0
        ))

        # Exogenous steroid activity must be delayed/genomic.  Use filtered
        # PD signals from SteroidsModule rather than raw command doses, so
        # hydrocortisone/dexamethasone do not behave like instant vasoactives.
        hydro_support_sig = float(bus.get("hydrocortisone_adrenal_support_signal")) if hasattr(bus.state, "hydrocortisone_adrenal_support_signal") else 0.0
        hydro_anti_sig = float(bus.get("hydrocortisone_antiinflammatory_signal")) if hasattr(bus.state, "hydrocortisone_antiinflammatory_signal") else 0.0
        dexa_anti_sig = float(bus.get("dexamethasone_antiinflammatory_signal")) if hasattr(bus.state, "dexamethasone_antiinflammatory_signal") else 0.0
        dexa_icp_sig = float(bus.get("dexamethasone_ICP_edema_signal")) if hasattr(bus.state, "dexamethasone_ICP_edema_signal") else 0.0
        hydro_activity = 0.55 * max(hydro_support_sig, hydro_anti_sig)
        dexa_activity = 0.35 * max(dexa_anti_sig, dexa_icp_sig)
        exogenous_gc = float(np.clip(hydro_activity + dexa_activity, 0.0, 0.85))

        target_cortisol = float(np.clip(0.18 + 0.72 * illness_drive + exogenous_gc, 0.0, 1.0))
        # Deep sedation blunts endogenous HPA activation but not exogenous steroid.
        target_cortisol = float(np.clip(target_cortisol * (1.0 - 0.18 * sedation) + exogenous_gc * 0.25, 0.0, 1.0))
        alpha_hpa = 1.0 - np.exp(-dt / float(self.params["hpa_tau_s"]))
        self._cortisol += alpha_hpa * (target_cortisol - self._cortisol)
        self._cortisol = float(np.clip(self._cortisol, 0.0, 1.0))

        target_catechol = float(np.clip(
            0.12 + 0.45 * shock_drive + 0.20 * pain_drive + 0.12 * hypogly_drive +
            0.08 * fever_drive + 0.10 * adr / (0.12 + max(adr, 0.0)) +
            0.06 * norad / (0.20 + max(norad, 0.0)),
            0.0, 1.0
        ))
        # Alpha-2 agonists and sedatives reduce endogenous tone.
        alpha2_effect = 0.0
        if hasattr(bus.state, "C_dexmedetomidine_ng_mL"):
            alpha2_effect += 0.30 * float(bus.get("C_dexmedetomidine_ng_mL")) / (0.8 + float(bus.get("C_dexmedetomidine_ng_mL")))
        if hasattr(bus.state, "C_clonidine_ng_mL"):
            alpha2_effect += 0.18 * float(bus.get("C_clonidine_ng_mL")) / (1.0 + float(bus.get("C_clonidine_ng_mL")))
        target_catechol *= float(np.clip(1.0 - alpha2_effect - 0.12 * sedation, 0.45, 1.0))
        alpha_cat = 1.0 - np.exp(-dt / float(self.params["catechol_tau_s"]))
        self._catechol += alpha_cat * (target_catechol - self._catechol)
        self._catechol = float(np.clip(self._catechol, 0.0, 1.0))

        # Relative adrenal insufficiency: high shock/cytokines but insufficient
        # cortisol/vasopressor responsiveness. Hydrocortisone lowers it.
        expected_cortisol = float(np.clip(0.25 + 0.70 * illness_drive, 0.0, 1.0))
        adrenal_insuff = float(np.clip((expected_cortisol - self._cortisol) / 0.75 + 0.20 * vaso / (0.08 + max(vaso, 0.0)), 0.0, 1.0))
        adrenal_insuff *= float(np.clip(1.0 - 0.65 * hydro_activity, 0.15, 1.0))
        steroid_need = float(np.clip(0.38 * shock_drive + 0.25 * vaso + 0.20 * sepsis_sev + 0.17 * adrenal_insuff, 0.0, 1.0))

        # Insulin resistance: stress hormones, steroids, cytokines. Insulin lowers
        # effective hyperglycemia but not the underlying resistance signal fully.
        insulin_resist = float(np.clip(
            0.18 * self._cortisol + 0.22 * self._catechol + 0.24 * cytokine +
            0.14 * exogenous_gc + 0.10 * glucotoxic_drive + 0.12 * sepsis_sev,
            0.0, 1.0
        ))
        # Step 3.9: effective insulin action is delayed/effect-site based, not
        # a direct subtraction from the raw pump command.
        stress_hyperglycemia = float(np.clip((glucose - 7.8) / 10.0 + 0.35 * insulin_resist - 0.10 * insulin_action, 0.0, 1.0))

        glucose_prod_mod = float(np.clip(1.0 + 0.65 * self._cortisol + 0.42 * self._catechol + 0.35 * exogenous_gc, 1.0, 2.6))
        insulin_sensitivity_mod = float(np.clip(1.0 - 0.62 * insulin_resist, 0.25, 1.05))

        endocrine_SVR_mod = float(np.clip(1.0 + 0.22 * self._catechol + 0.20 * self._cortisol - 0.45 * adrenal_insuff, 0.55, 1.55))
        endocrine_HR_add = float(np.clip(22.0 * self._catechol + 10.0 * hypogly_drive - 6.0 * sedation, -12.0, 42.0))
        endocrine_VO2_mod = float(np.clip(1.0 + 0.18 * self._catechol + 0.10 * fever_drive - 0.10 * self._thyroid_suppression, 0.80, 1.35))
        endocrine_lactate_mod = float(np.clip(1.0 + 0.35 * self._catechol + 0.28 * micro + 0.15 * adrenal_insuff, 1.0, 2.0))

        # ADH-like response: shock/stress retains water and lowers effective GFR.
        # Hypertonic state blunts water retention; fluid overload also blunts it.
        fluid_overload_hint = np.clip(fluid_balance / max(float(getattr(bus.state, "blood_volume_mL", 1500.0)), 1.0), 0.0, 1.5)
        osmotic_blunt = np.clip((Na - 142.0) / 12.0, 0.0, 1.0)
        ADH = float(np.clip(0.55 * shock_drive + 0.22 * self._catechol + 0.18 * pain_drive + 0.10 * vaso - 0.25 * osmotic_blunt - 0.20 * fluid_overload_hint, 0.0, 1.0))
        endocrine_GFR_mod = float(np.clip(1.0 - 0.22 * ADH - 0.18 * adrenal_insuff - 0.10 * shock_drive, 0.55, 1.05))

        # Non-thyroidal illness marker: slow severity integrator.
        thyroid_target = float(np.clip(0.25 * sepsis_sev + 0.22 * cytokine + 0.18 * lact_drive + 0.18 * shock_drive + 0.17 * max(sedation - 0.4, 0.0), 0.0, 1.0))
        self._thyroid_suppression += (1.0 - np.exp(-dt / 3600.0)) * (thyroid_target - self._thyroid_suppression)
        self._thyroid_suppression = float(np.clip(self._thyroid_suppression, 0.0, 1.0))

        severity = float(np.clip(0.22 * illness_drive + 0.18 * insulin_resist + 0.18 * adrenal_insuff + 0.16 * ADH + 0.14 * self._thyroid_suppression + 0.12 * stress_hyperglycemia, 0.0, 1.0))

        bus.update({
            "cortisol_activity": self._cortisol,
            "catecholamine_tone": self._catechol,
            "HPA_axis_activation": self._cortisol,
            "adrenal_insufficiency_index": adrenal_insuff,
            "critical_illness_steroid_need_index": steroid_need,
            "insulin_resistance_index": insulin_resist,
            "stress_hyperglycemia_index": stress_hyperglycemia,
            "endocrine_glucose_prod_mod": glucose_prod_mod,
            "insulin_sensitivity_mod": insulin_sensitivity_mod,
            "endocrine_SVR_mod": endocrine_SVR_mod,
            "endocrine_HR_add": endocrine_HR_add,
            "endocrine_VO2_mod": endocrine_VO2_mod,
            "endocrine_lactate_mod": endocrine_lactate_mod,
            "ADH_water_retention_index": ADH,
            "endocrine_GFR_mod": endocrine_GFR_mod,
            "thyroid_suppression_index": self._thyroid_suppression,
            "endocrine_severity_score": severity,
        })

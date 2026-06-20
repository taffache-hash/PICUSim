"""
Hematology / Oxygen Transport Module — v0.21
===========================================

Qualitative pediatric hematology module for PICU physiology simulation.
It does not prescribe transfusion. It tracks anemia, oxygen carrying
capacity, WBC/neutrophils, bleeding/thrombosis risk, hemolysis and a
transfusion-trigger score that can be used for scenario exploration.
"""

from __future__ import annotations
import numpy as np
from typing import List

from core.base_module import BaseModule
from core.bus import PhysiologicalBus


class HematologyOxygenTransportModule(BaseModule):
    """
    Pediatric hematology / oxygen transport module.

    Main outputs
    ------------
    Hct_percent, RBC_million_uL, WBC_count, neutrophil_count,
    anemia_severity_index, oxygen_carrying_capacity_mL_dL,
    oxygen_transport_reserve, transfusion_trigger_score,
    bleeding_risk_index, thrombosis_risk_index, hemolysis_index,
    marrow_suppression_index, platelet_function_index, heme_severity_score.

    Notes
    -----
    This is an exploratory model. Thresholds are intended as physiologic
    anchors, not clinical recommendations.
    """

    DEFAULT_PARAMS = {
        "weight_kg": 20.0,
        "Hb_baseline": 11.0,
        "WBC_baseline": 8.0,
        "neutrophil_baseline": 5.0,
        "lymphocyte_baseline": 2.2,
        "transfusion_threshold_Hb": 7.0,
        "critical_Hb": 5.0,
        "unstable_Hb_modifier": 1.0,
        "blood_volume_mL_kg": 75.0,
        "Hb_loss_per_mL_per_kg": 0.012,   # heuristic Hb drop per mL/kg blood loss
        "tau_WBC_s": 1800.0,
        "tau_bleeding_s": 120.0,
    }

    def __init__(self, params: dict | None = None):
        merged = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(name="HematologyOxygenTransport", params=merged)
        self._WBC = float(merged["WBC_baseline"])
        self._neut = float(merged["neutrophil_baseline"])
        self._lymph = float(merged["lymphocyte_baseline"])
        self._retic = 1.0
        self._cumulative_blood_loss_mL = 0.0
        self._last_RBC_transfused_mL = 0.0

    @property
    def input_keys(self) -> List[str]:
        return [
            "Hb", "SaO2", "PaO2", "CO", "VO2", "MAP", "HR", "lactate",
            "INR", "PLT_count", "fibrinogen", "d_dimer", "AT3", "coag_score",
            "infection_load", "cytokine_drive", "sepsis_severity_score",
            "microcirculatory_failure_index", "endothelial_leak_index",
            "urea_mmol_L", "creatinine_mg_dL", "fluid_balance",
            "GRC_units_given", "FFP_mL_given", "PLT_units_given",
            "bleeding_rate_mL_h", "hemolysis_index", "platelet_function_index",
        ]

    @property
    def output_keys(self) -> List[str]:
        return [
            "Hct_percent", "RBC_million_uL", "WBC_count", "neutrophil_count",
            "lymphocyte_count", "reticulocyte_percent", "anemia_severity_index",
            "oxygen_carrying_capacity_mL_dL", "oxygen_transport_reserve",
            "transfusion_trigger_score", "bleeding_risk_index",
            "thrombosis_risk_index", "hemolysis_index", "LDH_index",
            "indirect_bilirubin_mg_dL", "methemoglobin_percent",
            "marrow_suppression_index", "platelet_function_index",
            "heme_severity_score",
        ]

    def initialize(self, bus: PhysiologicalBus) -> None:
        Hb = float(bus.get("Hb"))
        wt = float(self.params["weight_kg"])
        age_group = getattr(bus.state, "age_group", "child")
        if age_group in ("neonate", "infant"):
            self.params["transfusion_threshold_Hb"] = max(self.params["transfusion_threshold_Hb"], 7.5)
        bus.update({
            "Hct_percent": float(np.clip(Hb * 3.0, 12.0, 65.0)),
            "RBC_million_uL": float(np.clip(Hb / 3.0, 1.0, 7.5)),
            "WBC_count": self._WBC,
            "neutrophil_count": self._neut,
            "lymphocyte_count": self._lymph,
            "reticulocyte_percent": self._retic,
            "transfusion_threshold_Hb": float(self.params["transfusion_threshold_Hb"]),
        })
        if not getattr(bus.state, "blood_volume_mL", None):
            bus.set("blood_volume_mL", wt * self.params["blood_volume_mL_kg"])

    @staticmethod
    def _clip01(x: float) -> float:
        return float(np.clip(x, 0.0, 1.0))

    def _wbc_dynamics(self, bus: PhysiologicalBus, dt: float) -> tuple[float, float, float, float]:
        infection = float(getattr(bus.state, "infection_load", 0.0))
        cytokine = float(getattr(bus.state, "cytokine_drive", 0.0))
        sepsis = float(getattr(bus.state, "sepsis_severity_score", 0.0))
        steroid = float(getattr(bus.state, "C_hydrocort_mcg_mL", 0.0)) + 0.5 * float(getattr(bus.state, "C_dexa_ng_mL", 0.0))
        shock = self._clip01((float(bus.get("lactate")) - 2.0) / 6.0)

        target_wbc = self.params["WBC_baseline"] * (1.0 + 1.2 * infection + 0.8 * cytokine + 0.4 * steroid)
        marrow_suppression = self._clip01(0.15 * sepsis + 0.25 * shock + 0.20 * max(float(bus.get("lactate")) - 6.0, 0.0) / 6.0)
        target_wbc *= (1.0 - 0.55 * marrow_suppression)
        target_wbc = float(np.clip(target_wbc, 1.0, 45.0))
        tau = self.params["tau_WBC_s"]
        self._WBC += (target_wbc - self._WBC) * dt / tau
        self._WBC = float(np.clip(self._WBC, 0.5, 60.0))

        neut_frac = np.clip(0.55 + 0.25 * infection + 0.10 * steroid - 0.15 * marrow_suppression, 0.25, 0.92)
        lymph_frac = np.clip(0.33 - 0.18 * infection - 0.12 * steroid, 0.04, 0.55)
        self._neut = float(np.clip(self._WBC * neut_frac, 0.1, 55.0))
        self._lymph = float(np.clip(self._WBC * lymph_frac, 0.05, 20.0))
        self._retic = float(np.clip(1.0 + 3.0 * self._clip01((self.params["Hb_baseline"] - bus.get("Hb")) / 5.0) - 1.5 * marrow_suppression, 0.2, 8.0))
        return self._WBC, self._neut, self._lymph, marrow_suppression

    def _apply_bleeding_hemolysis(self, bus: PhysiologicalBus, dt: float) -> float:
        wt = float(self.params["weight_kg"])
        Hb = float(bus.get("Hb"))
        bleeding_rate = max(float(getattr(bus.state, "bleeding_rate_mL_h", 0.0)), 0.0)
        hemolysis = self._clip01(float(getattr(bus.state, "hemolysis_index", 0.0)))
        sepsis = float(getattr(bus.state, "sepsis_severity_score", 0.0))
        micro = float(getattr(bus.state, "microcirculatory_failure_index", 0.0))
        # sepsis-associated low-grade hemolysis / red cell fragility
        endogenous_hemolysis = self._clip01(0.08 * sepsis + 0.08 * micro)
        hemolysis_eff = max(hemolysis, endogenous_hemolysis)

        blood_loss_mL = bleeding_rate * dt / 3600.0
        if blood_loss_mL > 0:
            self._cumulative_blood_loss_mL += blood_loss_mL
            Hb -= (blood_loss_mL / max(wt, 1.0)) * self.params["Hb_loss_per_mL_per_kg"]
            # blood loss also worsens fluid balance if not replaced
            bus.set("fluid_balance", float(bus.get("fluid_balance") - blood_loss_mL * 0.3))

        # Persistent RBC transfusion effect. v0.35: apply only the incremental
        # RBC volume since the last hematology step. Hematology owns the final
        # Hb response; Transfusion only increments RBC_transfused_mL.
        rbc_total_mL = float(getattr(bus.state, "RBC_transfused_mL", 0.0))
        rbc_delta_mL = max(rbc_total_mL - self._last_RBC_transfused_mL, 0.0)
        self._last_RBC_transfused_mL = rbc_total_mL
        if rbc_delta_mL > 0.0:
            Hb += 0.13 * (rbc_delta_mL / max(wt, 1.0))  # ~1.3 g/dL per 10 mL/kg

        # Hemolysis slowly decreases effective Hb and increases K/bilirubin indices.
        Hb -= hemolysis_eff * 0.04 * dt / 60.0
        Hb = float(np.clip(Hb, 3.0, 22.0))
        bus.set("Hb", Hb)
        return hemolysis_eff

    def _risk_scores(self, bus: PhysiologicalBus, Hb: float, marrow_suppression: float, hemolysis_eff: float) -> dict:
        PLT = float(bus.get("PLT_count"))
        INR = float(bus.get("INR"))
        Fib = float(bus.get("fibrinogen"))
        Ddim = float(bus.get("d_dimer"))
        urea = float(getattr(bus.state, "urea_mmol_L", 5.0))
        lactate = float(bus.get("lactate"))
        MAP = float(bus.get("MAP"))
        SaO2 = float(bus.get("SaO2"))
        CO = float(bus.get("CO"))
        VO2 = float(bus.get("VO2"))
        threshold = float(getattr(bus.state, "transfusion_threshold_Hb", self.params["transfusion_threshold_Hb"]))

        anemia = self._clip01((10.0 - Hb) / 5.0)
        critical_anemia = self._clip01((self.params["critical_Hb"] + 1.0 - Hb) / 2.0)
        shock_modifier = self._clip01((2.5 - MAP / 40.0) + (lactate - 2.0) / 6.0 + max(0.92 - SaO2, 0.0) * 3.0)

        platelet_function = float(getattr(bus.state, "platelet_function_index", 1.0))
        # uremia and sepsis impair platelet function even if count is preserved
        platelet_function *= (1.0 - 0.20 * self._clip01((urea - 12.0) / 18.0))
        platelet_function *= (1.0 - 0.15 * float(getattr(bus.state, "sepsis_severity_score", 0.0)))
        platelet_function = float(np.clip(platelet_function, 0.25, 1.0))

        bleeding_risk = (
            0.32 * self._clip01((75.0 - PLT) / 75.0) +
            0.25 * self._clip01((INR - 1.3) / 1.7) +
            0.18 * self._clip01((1.8 - Fib) / 1.2) +
            0.15 * (1.0 - platelet_function) +
            0.10 * self._clip01((Hb - 16.0) / 4.0)
        )
        bleeding_risk = self._clip01(bleeding_risk)

        thrombosis_risk = (
            0.25 * self._clip01((PLT - 450.0) / 350.0) +
            0.25 * self._clip01((Fib - 4.0) / 3.0) +
            0.20 * self._clip01((Ddim - 2.0) / 8.0) +
            0.15 * float(getattr(bus.state, "infection_load", 0.0)) +
            0.15 * float(getattr(bus.state, "CRRT_active_effective", 0.0))
        )
        thrombosis_risk = self._clip01(thrombosis_risk)

        # Restrictive strategy anchor: Hb <7 in stable patients, stronger score if shock/hypoxemia/low reserve.
        transfusion_score = self._clip01((threshold - Hb) / 2.0 + 0.45 * shock_modifier + 0.40 * critical_anemia)

        CaO2 = 1.34 * Hb * SaO2 + 0.003 * float(bus.get("PaO2"))
        DO2 = CO * CaO2 * 10.0
        O2_reserve = float(np.clip(DO2 / (VO2 * 3.0 + 1e-6), 0.0, 2.0))
        ERO2 = float(np.clip(VO2 / (DO2 + 1e-6), 0.05, 0.95))
        SvO2 = float(np.clip(1.0 - ERO2, 0.05, 0.95))
        PvO2 = float(np.clip(23.0 + 30.0 * SvO2, 18.0, 55.0))

        heme_sev = self._clip01(
            0.30 * anemia + 0.22 * bleeding_risk + 0.16 * thrombosis_risk +
            0.14 * hemolysis_eff + 0.10 * marrow_suppression +
            0.08 * self._clip01((1.0 - O2_reserve) / 0.8)
        )
        return {
            "anemia": anemia,
            "bleeding_risk": bleeding_risk,
            "thrombosis_risk": thrombosis_risk,
            "transfusion_score": transfusion_score,
            "platelet_function": platelet_function,
            "CaO2": CaO2,
            "DO2": DO2,
            "O2_reserve": O2_reserve,
            "ERO2": ERO2,
            "SvO2": SvO2,
            "PvO2": PvO2,
            "heme_sev": heme_sev,
        }

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        WBC, neut, lymph, marrow = self._wbc_dynamics(bus, dt)
        hemolysis_eff = self._apply_bleeding_hemolysis(bus, dt)
        Hb = float(bus.get("Hb"))
        scores = self._risk_scores(bus, Hb, marrow, hemolysis_eff)

        Hct = float(np.clip(Hb * 3.0, 10.0, 65.0))
        RBC = float(np.clip(Hb / 3.0, 0.8, 7.5))
        indirect_bili = float(np.clip(0.4 + 2.2 * hemolysis_eff + 0.5 * float(getattr(bus.state, "heme_severity_score", 0.0)), 0.1, 8.0))
        LDH = float(np.clip(0.15 + 1.2 * hemolysis_eff + 0.4 * float(getattr(bus.state, "microcirculatory_failure_index", 0.0)), 0.0, 3.0))
        metHb = float(np.clip(float(getattr(bus.state, "methemoglobin_percent", 0.5)), 0.0, 20.0))

        bus.update({
            "Hct_percent": Hct,
            "RBC_million_uL": RBC,
            "WBC_count": WBC,
            "neutrophil_count": neut,
            "lymphocyte_count": lymph,
            "reticulocyte_percent": self._retic,
            "marrow_suppression_index": marrow,
            "hemolysis_index": hemolysis_eff,
            "LDH_index": LDH,
            "indirect_bilirubin_mg_dL": indirect_bili,
            "methemoglobin_percent": metHb,
            "anemia_severity_index": scores["anemia"],
            "oxygen_carrying_capacity_mL_dL": scores["CaO2"],
            "oxygen_transport_reserve": scores["O2_reserve"],
            "transfusion_trigger_score": scores["transfusion_score"],
            "bleeding_risk_index": scores["bleeding_risk"],
            "thrombosis_risk_index": scores["thrombosis_risk"],
            "platelet_function_index": scores["platelet_function"],
            "heme_severity_score": scores["heme_sev"],
        })

"""
Nutrition / Catabolism Module v0.23
===================================

Modulo qualitativo per nutrizione PICU:
- apporto enterale/parenterale, proteine/lipidi
- bilancio energetico e proteico cumulativo
- catabolismo da sepsi/stress/steroidi
- feeding intolerance
- rischio refeeding con fosforo/magnesio/potassio
- trigliceridi da lipidi parenterali
- perdite proteiche in CRRT

Non è un calcolatore nutrizionale prescrittivo. Serve come asse fisiologico
esplorativo per scenari PICU.
"""

from __future__ import annotations
import numpy as np
from typing import List

from core.base_module import BaseModule
from core.bus import PhysiologicalBus


def _clip(x, lo, hi):
    return float(np.clip(x, lo, hi))


class NutritionCatabolismModule(BaseModule):
    DEFAULT_PARAMS = {
        "weight_kg": 20.0,
        "energy_target_kcal_kg_day": 55.0,
        "protein_target_g_kg_day": 1.5,
        "phosphate_baseline_mmol_L": 1.35,
        "magnesium_baseline_mmol_L": 0.82,
        "triglycerides_baseline_mmol_L": 1.0,
        "albumin_synthesis_rate_g_dL_h": 0.0015,
    }

    def __init__(self, params: dict | None = None):
        merged = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(name="NutritionCatabolism", params=merged)
        self._energy_balance_cum = 0.0
        self._protein_balance_cum = 0.0
        self._phos = float(merged["phosphate_baseline_mmol_L"])
        self._mg = float(merged["magnesium_baseline_mmol_L"])
        self._tg = float(merged["triglycerides_baseline_mmol_L"])

    @property
    def input_keys(self) -> List[str]:
        return ["VO2", "T_core", "infection_load", "cytokine_drive",
                "stress_index", "cortisol_activity", "insulin_resistance_index",
                "GIR_mg_kg_min", "glucose_mmol_L", "insulin_action_signal",
                "insulin_potassium_shift_signal", "CRRT_active_effective",
                "CRRT_effluent_mL_kg_h", "MAP", "norad_mcg_kg_min"]

    @property
    def output_keys(self) -> List[str]:
        return ["enteral_feed_mL_h", "parenteral_kcal_kg_day",
                "protein_g_kg_day", "lipid_g_kg_day", "energy_intake_kcal_day",
                "energy_expenditure_kcal_day", "energy_balance_kcal_day",
                "cumulative_energy_balance_kcal", "protein_intake_g_day",
                "protein_requirement_g_day", "protein_balance_g_day",
                "cumulative_protein_balance_g", "catabolism_index",
                "nitrogen_balance_proxy", "feeding_intolerance_index",
                "refeeding_risk_index", "phosphate_mmol_L", "magnesium_mmol_L",
                "triglycerides_mmol_L", "nutrition_severity_score",
                "CRRT_protein_loss_g_day", "nutrition_albumin_mod",
                "respiratory_quotient", "VCO2_mod"]

    def initialize(self, bus: PhysiologicalBus) -> None:
        self._energy_balance_cum = 0.0
        self._protein_balance_cum = 0.0
        self._phos = float(getattr(bus.state, "phosphate_mmol_L", self.params["phosphate_baseline_mmol_L"]))
        self._mg = float(getattr(bus.state, "magnesium_mmol_L", self.params["magnesium_baseline_mmol_L"]))
        self._tg = float(getattr(bus.state, "triglycerides_mmol_L", self.params["triglycerides_baseline_mmol_L"]))
        bus.update({
            "phosphate_mmol_L": self._phos,
            "magnesium_mmol_L": self._mg,
            "triglycerides_mmol_L": self._tg,
            "energy_balance_kcal_day": 0.0,
            "protein_balance_g_day": 0.0,
            "catabolism_index": 0.0,
            "feeding_intolerance_index": 0.0,
            "refeeding_risk_index": 0.0,
            "nutrition_severity_score": 0.0,
            "nutrition_albumin_mod": 1.0,
            "respiratory_quotient": 0.85,
            "VCO2_mod": 1.0,
        })

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        wt = float(self.params["weight_kg"])
        dt_h = dt / 3600.0
        dt_day = dt / 86400.0

        # Inputs nutrizionali
        enteral_mL_h = float(bus.get("enteral_feed_mL_h"))
        enteral_kcal_mL = float(bus.get("enteral_kcal_mL"))
        parenteral_kcal_kg_day = float(bus.get("parenteral_kcal_kg_day"))
        protein_g_kg_day = float(bus.get("protein_g_kg_day"))
        lipid_g_kg_day = float(bus.get("lipid_g_kg_day"))
        phosphate_supp = float(bus.get("phosphate_supplement_mmol"))
        magnesium_supp = float(bus.get("magnesium_supplement_mmol"))

        GIR = float(bus.get("GIR_mg_kg_min"))
        glucose = float(bus.get("glucose_mmol_L"))
        VO2 = float(bus.get("VO2"))
        MAP = float(bus.get("MAP"))
        infection = float(getattr(bus.state, "infection_load", 0.0))
        cytokine = float(getattr(bus.state, "cytokine_drive", 0.0))
        stress = float(getattr(bus.state, "stress_index", 0.0))
        cortisol = float(getattr(bus.state, "cortisol_activity", 0.2))
        insulin_res = float(getattr(bus.state, "insulin_resistance_index", 0.0))
        endocrine_sev = float(getattr(bus.state, "endocrine_severity_score", 0.0))
        sepsis_sev = float(getattr(bus.state, "sepsis_severity_score", 0.0))
        norad = float(getattr(bus.state, "norad_mcg_kg_min", 0.0))
        CRRT_eff = float(getattr(bus.state, "CRRT_active_effective", 0.0))
        CRRT_effluent = float(getattr(bus.state, "CRRT_effluent_mL_kg_h", 0.0))
        hepatic_sev = float(getattr(bus.state, "hepatic_severity_score", 0.0))
        lactate = float(getattr(bus.state, "lactate", 1.0))

        # Intake energetico: enterale + parenterale + GIR glucosio EV
        enteral_kcal_day = enteral_mL_h * enteral_kcal_mL * 24.0
        parenteral_kcal_day = parenteral_kcal_kg_day * wt
        gir_kcal_day = GIR * wt / 1000.0 * 3.75 * 60.0 * 24.0
        lipid_kcal_day = lipid_g_kg_day * wt * 9.0
        energy_intake = enteral_kcal_day + parenteral_kcal_day + gir_kcal_day + lipid_kcal_day

        # Spesa energetica da VO2 + stress/catabolismo
        REE_from_VO2 = VO2 * 0.0048 * 1440.0
        stress_factor = 1.0 + 0.18 * infection + 0.18 * cytokine + 0.12 * stress + 0.10 * max(cortisol - 0.25, 0.0)
        stress_factor *= (1.0 + 0.08 * max(bus.get("T_core") - 37.0, 0.0))
        energy_expenditure = REE_from_VO2 * _clip(stress_factor, 0.75, 1.65)

        # Catabolismo/proteine
        catabolism = 0.12 + 0.35 * sepsis_sev + 0.22 * cytokine + 0.14 * endocrine_sev + 0.10 * hepatic_sev
        catabolism += 0.10 * max(cortisol - 0.35, 0.0) + 0.08 * max(lactate - 2.0, 0.0) / 6.0
        catabolism = _clip(catabolism, 0.0, 1.0)
        protein_req = wt * self.params["protein_target_g_kg_day"] * (1.0 + 0.8 * catabolism)
        protein_intake = protein_g_kg_day * wt
        CRRT_protein_loss = CRRT_eff * (0.03 * CRRT_effluent * wt)  # g/day qualitative
        protein_balance = protein_intake - protein_req - CRRT_protein_loss
        nitrogen_balance = protein_balance / 6.25

        energy_balance = energy_intake - energy_expenditure
        self._energy_balance_cum += energy_balance * dt_day
        self._protein_balance_cum += protein_balance * dt_day

        # Feeding intolerance: shock, vasoattivi, lattato, PEEP/abdominal congestion proxy.
        gut_perfusion = _clip((MAP - 45.0) / 35.0, 0.0, 1.0)
        vaso = _clip(norad / 0.35, 0.0, 1.0)
        enteral_burden = _clip(enteral_mL_h / max(4.0 * wt, 1.0), 0.0, 1.2)
        feeding_intol = 0.08 + 0.32 * (1.0 - gut_perfusion) + 0.22 * vaso + 0.18 * sepsis_sev + 0.08 * hepatic_sev
        feeding_intol += 0.18 * max(enteral_burden - 0.5, 0.0)
        feeding_intol = _clip(feeding_intol, 0.0, 1.0)

        # Refeeding risk: malnutrition/negative cumulative balance + sudden calories + insulin/glucose shifts.
        malnutrition = float(getattr(bus.state, "malnutrition_index", 0.0))
        calorie_fraction = energy_intake / max(wt * self.params["energy_target_kcal_kg_day"], 1.0)
        refeed = 0.05 + 0.35 * malnutrition + 0.22 * max(calorie_fraction - 0.55, 0.0)
        insulin_revision = int(getattr(bus.state, "insulin_effect_revision", 0)) if hasattr(bus.state, "insulin_effect_revision") else 0
        if insulin_revision >= 319:
            insulin_refeed_signal = max(
                float(getattr(bus.state, "insulin_action_signal", 0.0)),
                float(getattr(bus.state, "insulin_potassium_shift_signal", 0.0)),
            )
        else:
            insulin_refeed_signal = max(float(bus.get("insulin_UI_h")) / max(wt * 0.05, 0.1), 0.0)
        refeed += 0.18 * insulin_refeed_signal
        refeed += 0.10 * max(glucose - 8.0, 0.0) / 8.0
        refeed = _clip(refeed, 0.0, 1.0)

        # Elettroliti nutrizionali: refeeding tira giù P/Mg/K, supplementi e CRRT influenzano.
        # Usiamo stato interno sincronizzato con bus se perturbato.
        self._phos = float(getattr(bus.state, "phosphate_mmol_L", self._phos))
        self._mg = float(getattr(bus.state, "magnesium_mmol_L", self._mg))
        self._tg = float(getattr(bus.state, "triglycerides_mmol_L", self._tg))

        dphos = (-0.035 * refeed - 0.010 * CRRT_eff * (CRRT_effluent / 30.0) + phosphate_supp / max(wt * 180.0, 1.0)) * dt_h
        dmg = (-0.010 * refeed - 0.005 * CRRT_eff * (CRRT_effluent / 30.0) + magnesium_supp / max(wt * 280.0, 1.0)) * dt_h
        self._phos = _clip(self._phos + dphos, 0.20, 2.20)
        self._mg = _clip(self._mg + dmg, 0.25, 1.60)

        # K shift da refeeding: piccola correzione verso basso, ma non prescrittiva.
        if refeed > 0.35 and hasattr(bus.state, "K_mmol_L"):
            k = float(bus.get("K_mmol_L"))
            bus.set("K_mmol_L", _clip(k - 0.006 * refeed * dt_h, 2.0, 7.5))

        # Trigliceridi: lipidi parenterali + sepsi/colestasi; clearance epatica ridotta.
        hepatic_clear = float(getattr(bus.state, "hepatic_drug_clearance_mod", 1.0))
        tg_prod = 0.020 * lipid_g_kg_day * (1.0 + 0.5 * sepsis_sev)
        tg_clear = 0.010 * hepatic_clear * max(self._tg - 0.8, 0.0)
        self._tg = _clip(self._tg + (tg_prod - tg_clear) * dt_h, 0.3, 8.0)

        # Albumina: apporto proteico positivo sostiene sintesi, catabolismo/leak la riducono.
        albumin_mod = _clip(1.0 + 0.06 * np.tanh(protein_balance / max(wt, 1.0)) - 0.12 * catabolism - 0.08 * feeding_intol, 0.75, 1.08)
        if hasattr(bus.state, "albumin_g_dL"):
            alb = float(bus.get("albumin_g_dL"))
            target_alb = _clip(alb * albumin_mod, 1.5, 4.5)
            alb_new = alb + (target_alb - alb) * min(dt / 7200.0, 0.02)
            bus.set("albumin_g_dL", _clip(alb_new, 1.5, 4.8))

        # Severity composito
        energy_deficit_index = _clip(-energy_balance / max(wt * self.params["energy_target_kcal_kg_day"], 1.0), 0.0, 1.0)
        protein_deficit_index = _clip(-protein_balance / max(protein_req, 1.0), 0.0, 1.0)
        electrolyte_risk = max(_clip((0.8 - self._phos) / 0.5, 0, 1), _clip((0.55 - self._mg) / 0.25, 0, 1))
        nutrition_sev = _clip(0.25 * energy_deficit_index + 0.25 * protein_deficit_index + 0.20 * feeding_intol + 0.20 * refeed + 0.10 * electrolyte_risk, 0.0, 1.0)

        # v0.27: substrate-dependent respiratory quotient.
        # Carbohydrate-heavy support increases CO2 production; lipid-heavy support lowers it.
        carb_signal = _clip((GIR - 3.0) / 6.0 + parenteral_kcal_kg_day / 80.0, 0.0, 1.0)
        lipid_signal = _clip(lipid_g_kg_day / 2.5, 0.0, 1.0)
        respiratory_quotient = _clip(0.82 + 0.18 * carb_signal - 0.12 * lipid_signal, 0.70, 1.05)
        VCO2_mod = _clip(respiratory_quotient / 0.85, 0.82, 1.24)

        bus.update({
            "energy_intake_kcal_day": float(energy_intake),
            "energy_expenditure_kcal_day": float(energy_expenditure),
            "energy_balance_kcal_day": float(energy_balance),
            "cumulative_energy_balance_kcal": float(self._energy_balance_cum),
            "protein_intake_g_day": float(protein_intake),
            "protein_requirement_g_day": float(protein_req),
            "protein_balance_g_day": float(protein_balance),
            "cumulative_protein_balance_g": float(self._protein_balance_cum),
            "catabolism_index": float(catabolism),
            "nitrogen_balance_proxy": float(nitrogen_balance),
            "feeding_intolerance_index": float(feeding_intol),
            "refeeding_risk_index": float(refeed),
            "phosphate_mmol_L": float(self._phos),
            "magnesium_mmol_L": float(self._mg),
            "triglycerides_mmol_L": float(self._tg),
            "CRRT_protein_loss_g_day": float(CRRT_protein_loss),
            "nutrition_albumin_mod": float(albumin_mod),
            "nutrition_severity_score": float(nutrition_sev),
            "respiratory_quotient": float(respiratory_quotient),
            "VCO2_mod": float(VCO2_mod),
        })

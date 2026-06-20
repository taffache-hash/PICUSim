"""
AKI / CRRT-lite Module — v0.18
================================
A qualitative pediatric acute kidney injury and renal replacement therapy
module. It is designed for exploratory PICU simulation, not dose calculation.

Implemented concepts:
  - creatinine/urea trajectories driven by GFR, sepsis and fluid dilution
  - KDIGO-like AKI stage from creatinine ratio and urine output proxy
  - fluid overload percent based on baseline body weight
  - diuretic response index
  - RRT indication score integrating hyperkalemia, acidosis, uremia, fluid overload
  - CRRT-lite effects on urea, potassium, bicarbonate, lactate and fluid balance
"""
from __future__ import annotations

import math
from typing import List
import numpy as np

from core.base_module import BaseModule
from core.bus import PhysiologicalBus
from core.profile_scaling import bus_patient_scalars, bsa_m2


class AKICRRTModule(BaseModule):
    DEFAULT_PARAMS = {
        "weight_kg": 20.0,
        "creatinine_baseline_mg_dL": 0.35,
        "urea_baseline_mmol_L": 5.0,
        "GFR_baseline": 70.0,
        "TBW_L_kg": 0.60,                 # approximate distribution for urea/K
        "creatinine_generation_mg_dL_day": 0.05,
        "urea_generation_mmol_L_day": 1.2,
        "AKI_creat_tau_h": 8.0,
        "diuretic_max_urine_gain": 2.5,   # fold over current urine proxy
        "crrt_K_clearance_gain": 0.55,
        "crrt_urea_clearance_gain": 0.65,
        "crrt_lactate_clearance_gain": 0.10,
        "crrt_HCO3_correction_gain": 0.55,
        "crrt_time_compression": 12.0,   # accelerates visible trajectory in short educational scenarios
        "crrt_min_effluent_for_effect": 10.0,
    }

    def __init__(self, params: dict | None = None):
        merged = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(name="AKI_CRRT_lite", params=merged)
        self.creatinine = float(merged["creatinine_baseline_mg_dL"])
        self.urea = float(merged["urea_baseline_mmol_L"])
        self._last_furosemide_mg_kg = 0.0
        self._renal_insult_memory = 0.0

    @property
    def input_keys(self) -> List[str]:
        return [
            "GFR", "AKI_index", "MAP", "urine_rate_mL_h", "fluid_balance", "blood_volume_mL",
            "Na_mmol_L", "K_mmol_L", "HCO3_mmol_L", "pH_a", "lactate", "urea_mmol_L",
            "microcirculatory_failure_index", "sepsis_GFR_mod", "endothelial_leak_index",
            "furosemide_mg_kg", "CRRT_active", "CRRT_effluent_mL_kg_h", "CRRT_net_UF_mL_h",
            "CRRT_dialysate_K_mmol_L", "CRRT_bicarbonate_mmol_L",
            "CRRT_K_target_mmol_L", "CRRT_HCO3_target_mmol_L", "CRRT_lactate_target_mmol_L",
        ]

    @property
    def output_keys(self) -> List[str]:
        return [
            "creatinine_mg_dL", "creatinine_ratio", "urea_mmol_L", "AKI_stage",
            "urine_output_mL_kg_h", "fluid_overload_percent", "diuretic_response_index",
            "RRT_indication_score", "renal_severity_score", "CRRT_active_effective",
            "CRRT_clearance_mod", "CRRT_UF_mL_h_effective",
            "CRRT_K_target_mmol_L", "CRRT_HCO3_target_mmol_L", "CRRT_lactate_target_mmol_L",
        ]

    def initialize(self, bus: PhysiologicalBus) -> None:
        info = bus_patient_scalars(bus, self.params)
        wt = info["weight_kg"]
        age_y = info["age_y"]
        prof = info["profile"]
        self.params["weight_kg"] = wt
        # v0.45: GFR baseline is derived from profile mL/min/1.73m2 and BSA.
        gfr_173 = float(prof.get("GFR_ml_min_1_73m2", self.params.get("GFR_baseline", 70.0)))
        self.params["GFR_baseline"] = gfr_173 * bsa_m2(wt, age_y) / 1.73
        # Neonates/infants have larger TBW fraction.
        self.params["TBW_L_kg"] = {"neonate": 0.75, "infant": 0.68, "toddler": 0.62}.get(info["age_group"], 0.60)
        bus.set("GFR", float(self.params["GFR_baseline"]))
        self.creatinine = float(bus.get("creatinine_mg_dL"))
        self.urea = float(bus.get("urea_mmol_L"))
        self._last_furosemide_mg_kg = float(bus.get("furosemide_mg_kg"))
        self._write(bus, stage=0, urine_ml_kg_h=float(bus.get("urine_rate_mL_h"))/max(self.params["weight_kg"],1.0),
                    fluid_overload=0.0, diur_resp=0.0, rrt_score=0.0, renal_score=0.0,
                    crrt_eff=0.0, clearance_mod=0.0)

    def _aki_stage(self, creat_ratio: float, urine_ml_kg_h: float) -> int:
        # KDIGO-like simplified staging. Urine threshold is instantaneous/proxy,
        # not a 6-12 h rolling window, so use it as supportive evidence only.
        stage_creat = 0
        if creat_ratio >= 3.0 or self.creatinine >= 4.0:
            stage_creat = 3
        elif creat_ratio >= 2.0:
            stage_creat = 2
        elif creat_ratio >= 1.5 or self.creatinine - self.params["creatinine_baseline_mg_dL"] >= 0.3:
            stage_creat = 1
        stage_urine = 0
        if urine_ml_kg_h < 0.1:
            stage_urine = 3
        elif urine_ml_kg_h < 0.3:
            stage_urine = 2
        elif urine_ml_kg_h < 0.5:
            stage_urine = 1
        return int(max(stage_creat, stage_urine))

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        info = bus_patient_scalars(bus, self.params)
        wt = max(float(info["weight_kg"]), 1.0)
        self.params["weight_kg"] = wt
        gfr = max(float(bus.get("GFR")), 0.0)
        gfr_base = max(float(self.params["GFR_baseline"]), 1.0)
        gfr_frac = float(np.clip(gfr / gfr_base, 0.0, 2.0))
        aki_idx = float(np.clip(bus.get("AKI_index"), 0.0, 1.0))
        micro = float(getattr(bus.state, "microcirculatory_failure_index", 0.0))
        sepsis_gfr_mod = float(getattr(bus.state, "sepsis_GFR_mod", 1.0))
        leak = float(getattr(bus.state, "endothelial_leak_index", 0.0))
        map_now = float(bus.get("MAP"))

        # Renal insult memory smooths transient hypotension/sepsis effects.
        insult_drive = np.clip((60.0 - map_now) / 35.0, 0.0, 1.0) * 0.5 + micro * 0.35 + (1.0 - sepsis_gfr_mod) * 0.25 + aki_idx * 0.55
        tau_mem = 1800.0
        self._renal_insult_memory += (float(insult_drive) - self._renal_insult_memory) * (1.0 - math.exp(-dt / tau_mem))
        self._renal_insult_memory = float(np.clip(self._renal_insult_memory, 0.0, 1.0))

        # Creatinine approaches a higher pseudo-steady state when GFR is low.
        creat_base = float(self.params["creatinine_baseline_mg_dL"])
        creat_target = creat_base / max(gfr_frac, 0.12)
        creat_target *= (1.0 + 0.35 * self._renal_insult_memory)
        # Positive fluid balance dilutes creatinine slightly; leak makes this less reliable.
        fluid_overload_percent = 100.0 * float(bus.get("fluid_balance")) / (wt * 1000.0)
        dilution = 1.0 / (1.0 + max(fluid_overload_percent, 0.0) / 100.0 * 0.55 * (1.0 - 0.4 * leak))
        creat_target *= dilution
        tau_creat = float(self.params["AKI_creat_tau_h"]) * 3600.0
        self.creatinine += (creat_target - self.creatinine) * (1.0 - math.exp(-dt / tau_creat))
        # generation term makes severe AKI drift upward over time.
        self.creatinine += (1.0 - min(gfr_frac, 1.0)) * self.params["creatinine_generation_mg_dL_day"] * dt / 86400.0
        self.creatinine = float(np.clip(self.creatinine, 0.08, 6.0))

        # Urea generation/clearance.
        urea_target = float(self.params["urea_baseline_mmol_L"]) / max(gfr_frac, 0.18)
        urea_target *= (1.0 + 0.25 * self._renal_insult_memory + 0.15 * micro)
        tau_urea = 4.0 * 3600.0 / max(gfr_frac, 0.2)
        self.urea += (urea_target - self.urea) * (1.0 - math.exp(-dt / tau_urea))
        self.urea += (1.0 - min(gfr_frac, 1.0)) * self.params["urea_generation_mmol_L_day"] * dt / 86400.0
        self.urea = float(np.clip(self.urea, 1.0, 60.0))

        # v3.1 Step 3.8: diuretic_response_index is a renal-adjusted audit
        # signal derived from PK/PD effect-site exposure.  It is not an owner
        # of urine_rate/fluid_balance and does not re-apply the raw cumulative
        # bolus counter; FluidBalance applies the final urine ledger once.
        furo = float(bus.get("furosemide_mg_kg"))
        self._last_furosemide_mg_kg = furo
        furo_pk_signal = float(np.clip(getattr(bus.state, "furosemide_effect_signal", 0.0), 0.0, 1.0))
        renal_delivery = float(np.clip(gfr_frac * (1.0 - aki_idx) * (1.0 - 0.55 * micro), 0.0, 1.0))
        diur_resp = float(np.clip(furo_pk_signal * renal_delivery, 0.0, 1.0))
        urine_rate = float(bus.get("urine_rate_mL_h"))
        if diur_resp > 0:
            gain = 1.0 + self.params["diuretic_max_urine_gain"] * diur_resp
            urine_rate = min(urine_rate * gain + 0.8 * wt * diur_resp, 8.0 * wt)
            # v0.31: AKI/CRRT no longer writes fluid_balance or urine_rate_mL_h.
            # It exposes diuretic_response_index; FluidBalance remains owner of
            # urine_rate_mL_h and the final fluid ledger.

        urine_ml_kg_h = urine_rate / wt
        creat_ratio = self.creatinine / max(creat_base, 0.05)
        stage = self._aki_stage(creat_ratio, urine_ml_kg_h)

        # RRT indication: qualitative integrated trigger, not a clinical rule.
        K = float(bus.get("K_mmol_L"))
        HCO3 = float(bus.get("HCO3_mmol_L"))
        pH = float(bus.get("pH_a"))
        lactate = float(bus.get("lactate"))
        hyperK = np.clip((K - 5.5) / 1.5, 0.0, 1.0)
        acidosis = max(np.clip((7.25 - pH) / 0.25, 0.0, 1.0), np.clip((18.0 - HCO3) / 10.0, 0.0, 1.0))
        uremia = np.clip((self.urea - 18.0) / 25.0, 0.0, 1.0)
        overload = np.clip((fluid_overload_percent - 8.0) / 12.0, 0.0, 1.0)
        oliguria = np.clip((0.5 - urine_ml_kg_h) / 0.5, 0.0, 1.0)
        rrt_score = float(np.clip(0.28 * hyperK + 0.25 * acidosis + 0.18 * uremia + 0.20 * overload + 0.09 * oliguria, 0.0, 1.0))
        renal_score = float(np.clip(0.25 * stage / 3.0 + 0.25 * self._renal_insult_memory + 0.20 * oliguria + 0.15 * overload + 0.15 * rrt_score, 0.0, 1.0))

        # CRRT-lite.
        crrt_active = bool(bus.get("CRRT_active"))
        effluent = float(bus.get("CRRT_effluent_mL_kg_h")) if crrt_active else 0.0
        crrt_eff = float(np.clip((effluent - self.params["crrt_min_effluent_for_effect"]) / 25.0, 0.0, 1.0))
        clearance_mod = crrt_eff
        # Owner/modifier outputs default to current values when CRRT is inactive.
        K_new = K
        HCO3_new = HCO3
        lact_new = lactate
        crrt_uf_h_effective = 0.0
        if crrt_eff > 0:
            # Small solute clearance toward dialysate/normal targets.
            TBW_L = max(wt * self.params["TBW_L_kg"], 1.0)
            k_rate = (effluent * wt / 1000.0) / TBW_L / 3600.0 * float(self.params.get("crrt_time_compression", 1.0))  # /s
            dial_K = float(bus.get("CRRT_dialysate_K_mmol_L"))
            dial_HCO3 = float(bus.get("CRRT_bicarbonate_mmol_L"))
            alpha = 1.0 - math.exp(-k_rate * dt)

            K_new = K + alpha * self.params["crrt_K_clearance_gain"] * (dial_K - K)
            HCO3_new = HCO3 + alpha * self.params["crrt_HCO3_correction_gain"] * (dial_HCO3 - HCO3)
            lact_new = lactate * (1.0 - alpha * self.params["crrt_lactate_clearance_gain"])
            self.urea += alpha * self.params["crrt_urea_clearance_gain"] * (float(self.params["urea_baseline_mmol_L"]) - self.urea)
            self.creatinine += alpha * 0.20 * (creat_base - self.creatinine)

            # Net ultrafiltration is suggested as a rate; FluidBalance owns the
            # final fluid_balance and cumulative UF ledger.
            net_uf = max(float(bus.get("CRRT_net_UF_mL_h")), 0.0)
            max_remove_h = max((float(bus.get("fluid_balance")) + 0.10 * wt * 1000.0) * 3600.0 / max(dt, 1e-9), 0.0)
            crrt_uf_h_effective = min(net_uf, max_remove_h)

        # v0.31: publish modifier/target fields; owner modules apply final values.
        bus.update({
            "CRRT_K_target_mmol_L": float(np.clip(K_new, 2.5, 7.5)),
            "CRRT_HCO3_target_mmol_L": float(np.clip(HCO3_new, 8.0, 40.0)),
            "CRRT_lactate_target_mmol_L": float(np.clip(lact_new, 0.3, 20.0)),
            "CRRT_UF_mL_h_effective": float(np.clip(crrt_uf_h_effective, 0.0, 5000.0)),
        })

        self._write(bus, stage=stage, urine_ml_kg_h=urine_ml_kg_h,
                    fluid_overload=fluid_overload_percent, diur_resp=diur_resp,
                    rrt_score=rrt_score, renal_score=renal_score,
                    crrt_eff=crrt_eff, clearance_mod=clearance_mod)

    def _write(self, bus: PhysiologicalBus, stage: int, urine_ml_kg_h: float,
               fluid_overload: float, diur_resp: float, rrt_score: float,
               renal_score: float, crrt_eff: float, clearance_mod: float) -> None:
        creat_base = max(float(self.params["creatinine_baseline_mg_dL"]), 0.05)
        bus.update({
            "creatinine_mg_dL": float(self.creatinine),
            "creatinine_baseline_mg_dL": float(creat_base),
            "creatinine_ratio": float(self.creatinine / creat_base),
            "urea_mmol_L": float(self.urea),
            "AKI_stage": int(stage),
            "urine_output_mL_kg_h": float(urine_ml_kg_h),
            "fluid_overload_percent": float(fluid_overload),
            "diuretic_response_index": float(diur_resp),
            "RRT_indication_score": float(rrt_score),
            "renal_severity_score": float(renal_score),
            "CRRT_active_effective": float(crrt_eff),
            "CRRT_clearance_mod": float(clearance_mod),
        })

"""
Hepatic Metabolism Module — v0.22
=================================

Qualitative pediatric liver/metabolism layer for PICU simulations.

Scope
-----
This module models functional hepatic dysfunction in critical illness:

* hepatic perfusion and hypoxic/hepatocellular injury proxy
* cholestasis / direct bilirubin
* indirect bilirubin contribution from hemolysis
* albumin synthesis / oncotic reserve
* hepatic contribution to INR/coagulation
* lactate clearance modifier
* drug clearance modifier
* ammonia / encephalopathy proxy

This is an exploratory physiology module, not a diagnostic hepatology model.
All thresholds are qualitative anchors for in-silico scenario behavior.
"""
from __future__ import annotations

from typing import List
import numpy as np

from core.base_module import BaseModule
from core.bus import PhysiologicalBus


class HepaticMetabolismModule(BaseModule):
    DEFAULT_PARAMS = {
        "weight_kg": 20.0,
        "albumin_baseline_g_dL": 3.8,
        "bilirubin_total_baseline_mg_dL": 0.5,
        "bilirubin_direct_baseline_mg_dL": 0.15,
        "AST_baseline_U_L": 35.0,
        "ALT_baseline_U_L": 25.0,
        "tau_bilirubin_s": 7200.0,
        "tau_albumin_s": 21600.0,
        "tau_ammonia_s": 3600.0,
    }

    def __init__(self, params: dict | None = None):
        merged = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(name="HepaticMetabolism", params=merged)
        self._albumin = float(merged["albumin_baseline_g_dL"])
        self._btot = float(merged["bilirubin_total_baseline_mg_dL"])
        self._bdir = float(merged["bilirubin_direct_baseline_mg_dL"])
        self._AST = float(merged["AST_baseline_U_L"])
        self._ALT = float(merged["ALT_baseline_U_L"])
        self._ammonia = 35.0

    @property
    def input_keys(self) -> List[str]:
        return [
            "MAP", "CO", "CVP", "lactate", "SaO2", "PaO2", "DO2",
            "infection_load", "cytokine_drive", "sepsis_severity_score",
            "microcirculatory_failure_index", "endothelial_leak_index",
            "hemolysis_index", "indirect_bilirubin_mg_dL", "INR",
            "PLT_count", "fibrinogen", "fluid_balance", "urea_mmol_L",
            "creatinine_mg_dL", "hydrocortisone_mg_kg_h", "ketamine_mg_kg_h",
            "midazolam_mcg_kg_h", "propofol_mg_kg_h", "fentanyl_mcg_kg_h",
        ]

    @property
    def output_keys(self) -> List[str]:
        return [
            "hepatic_perfusion_index", "hepatic_hypoxic_injury_index",
            "hepatocellular_injury_index", "cholestasis_index",
            "bilirubin_total_mg_dL", "bilirubin_direct_mg_dL",
            "bilirubin_indirect_mg_dL", "AST_U_L", "ALT_U_L",
            "albumin_g_dL", "oncotic_pressure_proxy",
            "hepatic_lactate_clearance_mod", "hepatic_drug_clearance_mod",
            "hepatic_INR_contribution", "ammonia_umol_L",
            "hepatic_encephalopathy_index", "hepatic_severity_score",
            "liver_SOFA_proxy", "hepatic_fluid_leak_mod",
        ]

    @staticmethod
    def _clip01(x: float) -> float:
        return float(np.clip(x, 0.0, 1.0))

    def initialize(self, bus: PhysiologicalBus) -> None:
        self._albumin = float(np.clip(getattr(bus.state, "albumin_g_dL", self._albumin), 1.2, 5.5))
        self._btot = float(np.clip(getattr(bus.state, "bilirubin_total_mg_dL", self._btot), 0.1, 30.0))
        self._bdir = float(np.clip(getattr(bus.state, "bilirubin_direct_mg_dL", self._bdir), 0.0, 25.0))
        self._AST = float(np.clip(getattr(bus.state, "AST_U_L", self._AST), 5.0, 20000.0))
        self._ALT = float(np.clip(getattr(bus.state, "ALT_U_L", self._ALT), 5.0, 20000.0))
        self._ammonia = float(np.clip(getattr(bus.state, "ammonia_umol_L", 35.0), 10.0, 500.0))
        bus.update({
            "albumin_g_dL": self._albumin,
            "bilirubin_total_mg_dL": self._btot,
            "bilirubin_direct_mg_dL": self._bdir,
            "bilirubin_indirect_mg_dL": max(self._btot - self._bdir, 0.0),
            "AST_U_L": self._AST,
            "ALT_U_L": self._ALT,
            "ammonia_umol_L": self._ammonia,
        })

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        MAP = float(bus.get("MAP"))
        CO = float(bus.get("CO"))
        CVP = float(bus.get("CVP"))
        lact = float(bus.get("lactate"))
        SaO2 = float(bus.get("SaO2"))
        PaO2 = float(bus.get("PaO2"))
        DO2 = float(bus.get("DO2"))
        infection = float(getattr(bus.state, "infection_load", 0.0))
        cytokine = float(getattr(bus.state, "cytokine_drive", 0.0))
        sepsis = float(getattr(bus.state, "sepsis_severity_score", 0.0))
        micro = float(getattr(bus.state, "microcirculatory_failure_index", 0.0))
        leak = float(getattr(bus.state, "endothelial_leak_index", 0.0))
        hemolysis = float(getattr(bus.state, "hemolysis_index", 0.0))
        indirect_heme = float(getattr(bus.state, "indirect_bilirubin_mg_dL", 0.3))
        urea = float(getattr(bus.state, "urea_mmol_L", 5.0))
        fluid_balance = float(getattr(bus.state, "fluid_balance", 0.0))
        wt = float(self.params["weight_kg"])

        # Perfusion: pressure, flow and venous congestion all matter.
        pressure = np.clip((MAP - 40.0) / 35.0, 0.05, 1.15)
        flow = np.clip(CO / max(0.10 * wt, 0.5), 0.15, 1.35)  # ~100 mL/kg/min as low anchor
        congestion_penalty = np.clip((CVP - 8.0) / 12.0, 0.0, 0.55)
        oxygen_penalty = np.clip((0.90 - SaO2) * 2.0 + (65.0 - PaO2) / 100.0, 0.0, 0.70)
        perfusion = float(np.clip(0.55 * pressure + 0.45 * flow - congestion_penalty - 0.4 * oxygen_penalty, 0.05, 1.15))

        hypoxic_injury = self._clip01((1.0 - perfusion) * 0.9 + micro * 0.35 + max(lact - 3.0, 0.0) / 12.0)
        inflammatory_cholestasis = self._clip01(0.45 * sepsis + 0.35 * cytokine + 0.20 * infection)
        cholestasis = self._clip01(0.55 * inflammatory_cholestasis + 0.30 * leak + 0.15 * congestion_penalty)
        hepatocellular = self._clip01(0.75 * hypoxic_injury + 0.15 * inflammatory_cholestasis + 0.10 * max(DO2 < wt * 14.0, 0))

        # Smooth labs toward targets.
        dt_bil = dt / max(float(self.params["tau_bilirubin_s"]), 1.0)
        target_bdir = 0.15 + 5.5 * cholestasis + 2.0 * hypoxic_injury
        target_bind = 0.25 + 3.0 * self._clip01(hemolysis) + 0.7 * indirect_heme
        self._bdir += (target_bdir - self._bdir) * dt_bil
        bind = max(self._btot - self._bdir, 0.0)
        bind += (target_bind - bind) * dt_bil
        self._bdir = float(np.clip(self._bdir, 0.0, 25.0))
        bind = float(np.clip(bind, 0.0, 20.0))
        self._btot = float(np.clip(self._bdir + bind, 0.1, 35.0))

        # AST/ALT: qualitative injury indices with slow changes.
        enzyme_target = 35.0 + 1500.0 * hepatocellular + 250.0 * inflammatory_cholestasis
        tau_enzyme = 3600.0
        self._AST += (enzyme_target - self._AST) * dt / tau_enzyme
        self._ALT += (0.75 * enzyme_target - self._ALT) * dt / tau_enzyme
        self._AST = float(np.clip(self._AST, 5.0, 20000.0))
        self._ALT = float(np.clip(self._ALT, 5.0, 20000.0))

        # Albumin: slow negative acute phase plus dilution/capillary leak.
        fluid_overload = self._clip01(fluid_balance / max(0.15 * wt * 1000.0, 1.0))
        albumin_target = self.params["albumin_baseline_g_dL"] * (1.0 - 0.22 * inflammatory_cholestasis - 0.18 * leak - 0.15 * fluid_overload)
        self._albumin += (albumin_target - self._albumin) * dt / max(float(self.params["tau_albumin_s"]), 1.0)
        self._albumin = float(np.clip(self._albumin, 1.2, 5.5))
        oncotic = float(np.clip(self._albumin / 4.0, 0.25, 1.25))

        # Ammonia/encephalopathy: hepatic dysfunction + uremia + sepsis.
        ammonia_target = 35.0 + 110.0 * hepatocellular + 80.0 * (1.0 - perfusion) + 25.0 * self._clip01((urea - 10.0) / 20.0)
        self._ammonia += (ammonia_target - self._ammonia) * dt / max(float(self.params["tau_ammonia_s"]), 1.0)
        self._ammonia = float(np.clip(self._ammonia, 10.0, 500.0))
        enceph = self._clip01((self._ammonia - 60.0) / 120.0 + 0.25 * sepsis + 0.20 * hypoxic_injury)

        lact_clear_mod = float(np.clip(1.0 - 0.60 * hypoxic_injury - 0.25 * cholestasis, 0.20, 1.15))
        drug_clear_mod = float(np.clip(1.0 - 0.55 * hepatocellular - 0.30 * cholestasis - 0.15 * (1.0 - perfusion), 0.25, 1.10))
        inr_contrib = float(np.clip(0.85 * hepatocellular + 0.35 * cholestasis + 0.20 * (1.0 - perfusion), 0.0, 1.8))
        fluid_leak_mod = float(np.clip(1.0 + 0.45 * (1.0 - oncotic) + 0.25 * cholestasis, 1.0, 1.7))

        # SOFA-like bilirubin proxy: 0-4 scaled; pediatric qualitative only.
        liver_sofa = 0
        if self._btot >= 12: liver_sofa = 4
        elif self._btot >= 6: liver_sofa = 3
        elif self._btot >= 2: liver_sofa = 2
        elif self._btot >= 1.2: liver_sofa = 1

        severity = self._clip01(0.26 * hypoxic_injury + 0.20 * cholestasis + 0.18 * (1.0 - oncotic) + 0.16 * inr_contrib / 1.8 + 0.12 * enceph + 0.08 * self._clip01((self._btot - 1.0) / 8.0))

        bus.update({
            "hepatic_perfusion_index": perfusion,
            "hepatic_hypoxic_injury_index": hypoxic_injury,
            "hepatocellular_injury_index": hepatocellular,
            "cholestasis_index": cholestasis,
            "bilirubin_total_mg_dL": self._btot,
            "bilirubin_direct_mg_dL": self._bdir,
            "bilirubin_indirect_mg_dL": bind,
            "AST_U_L": self._AST,
            "ALT_U_L": self._ALT,
            "albumin_g_dL": self._albumin,
            "oncotic_pressure_proxy": oncotic,
            "hepatic_lactate_clearance_mod": lact_clear_mod,
            "hepatic_drug_clearance_mod": drug_clear_mod,
            "hepatic_INR_contribution": inr_contrib,
            "ammonia_umol_L": self._ammonia,
            "hepatic_encephalopathy_index": enceph,
            "hepatic_severity_score": severity,
            "liver_SOFA_proxy": int(liver_sofa),
            "hepatic_fluid_leak_mod": fluid_leak_mod,
        })

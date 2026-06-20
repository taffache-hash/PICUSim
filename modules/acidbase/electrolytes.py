"""
AcidBaseElectrolyteModule — v0.17
=================================

Qualitative pediatric acid-base / electrolyte module.

Intent:
  - Make pH depend on both respiratory PaCO2 and metabolic components.
  - Track Na/K/Cl/HCO3, base excess, anion gap, osmolality and SID-lite.
  - Couple saline chloride load, bicarbonate, hypertonic saline, lactate,
    renal GFR and sepsis/endothelial leak into acid-base trajectories.
  - Remain educational/exploratory, not a clinical dosing calculator.
"""

from __future__ import annotations
import math
from typing import List
import numpy as np

from core.base_module import BaseModule
from core.bus import PhysiologicalBus


class AcidBaseElectrolyteModule(BaseModule):
    """
    Simplified Stewart/Henderson-Hasselbalch hybrid.

    State variables are intentionally interpretable:
      Na, K, Cl, HCO3, BE, AG, osmolality, SID, acid-base phenotype.

    The module overwrites pH_a after GasExchange, using current PaCO2 and
    metabolically updated HCO3. GasExchange then reads that pH on the next step.
    """

    DEFAULT_PARAMS = {
        "weight_kg": 20.0,
        "ECF_ml_kg": 250.0,          # distribution volume for crystalloids/electrolytes
        "Na_baseline": 138.0,
        "K_baseline": 4.0,
        "Cl_baseline": 103.0,
        "HCO3_baseline": 24.0,
        "albumin_g_dL": 3.5,
        "phosphate_mmol_L": 1.2,
        "renal_HCO3_recovery_h": 12.0,
        "renal_K_time_h": 6.0,
        "lactate_acid_gain": 0.35,   # mmol HCO3 consumed per mmol lactate above 1.5
        "chloride_acid_gain": 0.38,  # mmol HCO3 consumed per mmol Cl above 106
        "sepsis_acid_gain": 0.08,    # extra metabolic acid from microcirculatory failure
        "bicarb_effective_fraction": 0.75,
        "hypertonic_Na_mmol_per_mL_3pct": 0.513,
        "saline_NaCl_mmol_per_mL": 0.154,
        "balanced_fluid_Cl_mmol_per_mL": 0.109,
        "acetate_buffer_fraction": 0.65,
    }

    def __init__(self, params: dict | None = None):
        merged = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(name="AcidBaseElectrolytes", params=merged)
        self.Na = float(merged["Na_baseline"])
        self.K = float(merged["K_baseline"])
        self.Cl = float(merged["Cl_baseline"])
        self.HCO3 = float(merged["HCO3_baseline"])
        self._last_saline_mL = 0.0
        self._last_balanced_mL = 0.0
        self._last_bicarb_mmol = 0.0
        self._last_hts_mL = 0.0
        self._last_K_mmol = 0.0

    @property
    def input_keys(self) -> List[str]:
        return [
            "PaCO2", "pH_a", "lactate", "GFR", "fluid_balance", "glucose_mmol_L",
            "microcirculatory_failure_index", "endothelial_leak_index", "sepsis_GFR_mod",
            "normal_saline_mL", "balanced_crystalloid_mL", "bicarbonate_mmol",
            "hypertonic_saline_3pct_mL", "potassium_mmol", "diuretic_effect",
            "CRRT_active_effective", "CRRT_K_target_mmol_L", "CRRT_HCO3_target_mmol_L",
        ]

    @property
    def output_keys(self) -> List[str]:
        return [
            "Na_mmol_L", "K_mmol_L", "Cl_mmol_L", "HCO3_mmol_L", "base_excess_mmol_L",
            "anion_gap_mmol_L", "corrected_anion_gap_mmol_L", "SID_apparent_mmol_L",
            "osmolarity_mOsm_L", "acid_base_status", "metabolic_acidosis_index",
            "respiratory_acidosis_index", "hyperchloremia_index", "hypokalemia_index",
            "hyperkalemia_index", "pH_a",
        ]

    def initialize(self, bus: PhysiologicalBus) -> None:
        self.Na = float(bus.get("Na_mmol_L"))
        self.K = float(bus.get("K_mmol_L"))
        self.Cl = float(bus.get("Cl_mmol_L"))
        self.HCO3 = float(bus.get("HCO3_mmol_L"))
        self._last_saline_mL = float(bus.get("normal_saline_mL"))
        self._last_balanced_mL = float(bus.get("balanced_crystalloid_mL"))
        self._last_bicarb_mmol = float(bus.get("bicarbonate_mmol"))
        self._last_hts_mL = float(bus.get("hypertonic_saline_3pct_mL"))
        self._last_K_mmol = float(bus.get("potassium_mmol"))
        self._write(bus)

    def _ecf_L(self, bus: PhysiologicalBus) -> float:
        wt = float(self.params["weight_kg"])
        base = wt * float(self.params["ECF_ml_kg"]) / 1000.0
        # capillary leak expands ECF but only a fraction stays effective
        leak = float(getattr(bus.state, "endothelial_leak_index", 0.0))
        return max(base * (1.0 + 0.30 * leak), 0.6)

    def _hh_pH(self, PaCO2: float, HCO3: float) -> float:
        alpha = 0.0307
        pK = 6.10
        PaCO2 = max(float(PaCO2), 10.0)
        HCO3 = max(float(HCO3), 3.0)
        return float(pK + math.log10(HCO3 / (alpha * PaCO2)))

    def _classify(self, pH: float, PaCO2: float, HCO3: float, AGcorr: float, Cl: float) -> str:
        metabolic_acid = HCO3 < 20.0 or AGcorr > 16.0 or Cl > 112.0
        metabolic_alk = HCO3 > 28.0
        resp_acid = PaCO2 > 50.0
        resp_alk = PaCO2 < 32.0
        if pH < 7.32 and metabolic_acid and resp_acid:
            return "mixed_acidosis"
        if pH < 7.32 and AGcorr > 16.0:
            return "high_anion_gap_metabolic_acidosis"
        if pH < 7.32 and Cl > 110.0:
            return "hyperchloremic_metabolic_acidosis"
        if pH < 7.32 and resp_acid:
            return "respiratory_acidosis"
        if pH > 7.48 and resp_alk:
            return "respiratory_alkalosis"
        if pH > 7.48 and metabolic_alk:
            return "metabolic_alkalosis"
        if metabolic_acid:
            return "compensated_metabolic_acidosis"
        return "near_normal"

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        # Sync external changes from perturbations or downstream modules such as CRRT-lite.
        # In normal operation bus values equal internal state because this module writes them
        # every step; after a perturbation/CRRT update they differ and must be adopted.
        for attr, key in (("Na", "Na_mmol_L"), ("K", "K_mmol_L"),
                          ("Cl", "Cl_mmol_L"), ("HCO3", "HCO3_mmol_L")):
            v = float(bus.get(key))
            if abs(v - getattr(self, attr)) > 1e-6:
                setattr(self, attr, v)

        ECF = self._ecf_L(bus)
        GFR = max(float(bus.get("GFR")), 0.0)
        renal_factor = np.clip(GFR / 80.0, 0.05, 1.5)
        lactate = float(bus.get("lactate"))
        micro = float(getattr(bus.state, "microcirculatory_failure_index", 0.0))
        leak = float(getattr(bus.state, "endothelial_leak_index", 0.0))

        # Incremental interventions: cumulative counters on the bus.
        saline = float(bus.get("normal_saline_mL"))
        d_saline = max(saline - self._last_saline_mL, 0.0)
        self._last_saline_mL = saline

        balanced = float(bus.get("balanced_crystalloid_mL"))
        d_balanced = max(balanced - self._last_balanced_mL, 0.0)
        self._last_balanced_mL = balanced

        bic = float(bus.get("bicarbonate_mmol"))
        d_bic = max(bic - self._last_bicarb_mmol, 0.0)
        self._last_bicarb_mmol = bic

        hts = float(bus.get("hypertonic_saline_3pct_mL"))
        d_hts = max(hts - self._last_hts_mL, 0.0)
        self._last_hts_mL = hts

        K_total = float(bus.get("potassium_mmol"))
        d_K = max(K_total - self._last_K_mmol, 0.0)
        self._last_K_mmol = K_total

        # Electrolyte dilution/mixing from fluids. This is a coarse ECF mixer.
        if d_saline > 0:
            # v0.31: AcidBase records intervention volume in external ledger;
            # FluidBalance owns final fluid_balance/cumulative inputs.
            bus.set("external_fluid_input_mL", float(bus.get("external_fluid_input_mL") + d_saline))
            mmol = d_saline * self.params["saline_NaCl_mmol_per_mL"]
            self.Na = (self.Na * ECF + mmol) / (ECF + d_saline / 1000.0)
            self.Cl = (self.Cl * ECF + mmol) / (ECF + d_saline / 1000.0)
        if d_balanced > 0:
            bus.set("external_fluid_input_mL", float(bus.get("external_fluid_input_mL") + d_balanced))
            na_mmol = d_balanced * 0.140
            cl_mmol = d_balanced * self.params["balanced_fluid_Cl_mmol_per_mL"]
            buffer_mmol = d_balanced * 0.028 * self.params["acetate_buffer_fraction"]
            self.Na = (self.Na * ECF + na_mmol) / (ECF + d_balanced / 1000.0)
            self.Cl = (self.Cl * ECF + cl_mmol) / (ECF + d_balanced / 1000.0)
            self.HCO3 += buffer_mmol / ECF
        if d_hts > 0:
            bus.set("external_fluid_input_mL", float(bus.get("external_fluid_input_mL") + d_hts))
            mmol = d_hts * self.params["hypertonic_Na_mmol_per_mL_3pct"]
            self.Na += mmol / ECF
            self.Cl += mmol / ECF
        if d_bic > 0:
            self.Na += d_bic / ECF
            self.HCO3 += d_bic * self.params["bicarb_effective_fraction"] / ECF
        if d_K > 0:
            self.K += d_K / ECF

        # Metabolic acid drivers.
        lactate_excess = max(lactate - 1.5, 0.0)
        hco3_target = 24.0
        hco3_target -= self.params["lactate_acid_gain"] * lactate_excess
        hco3_target -= self.params["chloride_acid_gain"] * max(self.Cl - 106.0, 0.0)
        hco3_target -= self.params["sepsis_acid_gain"] * 10.0 * micro
        hco3_target -= 2.0 * leak
        hco3_target = float(np.clip(hco3_target, 8.0, 32.0))

        # Renal compensation toward target / baseline: slow unless GFR preserved.
        tau = float(self.params["renal_HCO3_recovery_h"]) * 3600.0 / max(renal_factor, 0.05)
        alpha = 1.0 - math.exp(-dt / tau)
        self.HCO3 += alpha * (hco3_target - self.HCO3)
        self.HCO3 = float(np.clip(self.HCO3, 5.0, 45.0))

        # K trends: acidosis and AKI push up; insulin/diuresis/normal kidney pull toward 4.
        pH_pre = self._hh_pH(float(bus.get("PaCO2")), self.HCO3)
        acidosis_shift = max(7.35 - pH_pre, 0.0) * 1.2
        aki_shift = max(1.0 - renal_factor, 0.0) * 0.04 * dt / 60.0
        insulin_revision = int(getattr(bus.state, "insulin_effect_revision", 0)) if hasattr(bus.state, "insulin_effect_revision") else 0
        if insulin_revision >= 319:
            # Step 3.9: potassium is not shifted directly by the raw insulin
            # command.  PharmacologyModule publishes an effect-site shift rate;
            # AcidBaseElectrolyteModule remains the sole writer of final K.
            insulin_shift_rate = float(np.clip(
                getattr(bus.state, "insulin_effective_potassium_shift_mmol_L_h", 0.0),
                0.0, 1.0
            ))
            insulin_shift = insulin_shift_rate * dt / 3600.0
        elif insulin_revision >= 116:
            insulin_signal = float(np.clip(getattr(bus.state, "insulin_potassium_shift_signal", 0.0), 0.0, 1.0))
            insulin_shift = 0.018 * insulin_signal * dt / 60.0
        else:
            insulin = float(getattr(bus.state, "insulin_UI_h", 0.0))
            insulin_shift = 0.03 * insulin * dt / 3600.0
        tauK = float(self.params["renal_K_time_h"]) * 3600.0 / max(renal_factor, 0.1)
        self.K += (4.0 + acidosis_shift - self.K) * (1.0 - math.exp(-dt / tauK)) + aki_shift - insulin_shift
        self.K = float(np.clip(self.K, 2.0, 8.0))

        # v0.31: CRRT no longer writes K/HCO3 directly. It publishes
        # targets; AcidBase/Electrolytes owns final K/HCO3 and applies a
        # conservative one-step movement toward those targets.
        crrt_eff = float(getattr(bus.state, "CRRT_active_effective", 0.0))
        if crrt_eff > 0.0:
            k_target = float(getattr(bus.state, "CRRT_K_target_mmol_L", self.K))
            hco3_target_crrt = float(getattr(bus.state, "CRRT_HCO3_target_mmol_L", self.HCO3))
            blend = float(np.clip(0.35 * crrt_eff, 0.0, 0.5))
            self.K += blend * (k_target - self.K)
            self.HCO3 += blend * (hco3_target_crrt - self.HCO3)
            self.K = float(np.clip(self.K, 2.0, 8.0))
            self.HCO3 = float(np.clip(self.HCO3, 5.0, 45.0))

        self._write(bus)

    def _write(self, bus: PhysiologicalBus) -> None:
        PaCO2 = float(bus.get("PaCO2"))
        pH = self._hh_pH(PaCO2, self.HCO3)
        albumin = float(self.params["albumin_g_dL"])
        albumin_corr = 2.5 * max(4.0 - albumin, 0.0)
        AG = self.Na + self.K - self.Cl - self.HCO3
        AGcorr = AG + albumin_corr
        SID = self.Na + self.K - self.Cl
        glucose = float(bus.get("glucose_mmol_L"))
        osm = 2.0 * self.Na + glucose + float(getattr(bus.state, "urea_mmol_L", 5.0))
        BE = self.HCO3 - 24.0 + 14.8 * (pH - 7.40)

        metabolic_idx = float(np.clip((24.0 - self.HCO3) / 12.0 + max(AGcorr - 14.0, 0.0) / 20.0, 0.0, 1.0))
        resp_idx = float(np.clip((PaCO2 - 45.0) / 35.0, 0.0, 1.0))
        hypercl = float(np.clip((self.Cl - 108.0) / 14.0, 0.0, 1.0))

        bus.update({
            "Na_mmol_L": float(self.Na),
            "K_mmol_L": float(self.K),
            "Cl_mmol_L": float(self.Cl),
            "HCO3_mmol_L": float(self.HCO3),
            "base_excess_mmol_L": float(BE),
            "anion_gap_mmol_L": float(AG),
            "corrected_anion_gap_mmol_L": float(AGcorr),
            "SID_apparent_mmol_L": float(SID),
            "osmolarity_mOsm_L": float(osm),
            "acid_base_status": self._classify(pH, PaCO2, self.HCO3, AGcorr, self.Cl),
            "metabolic_acidosis_index": metabolic_idx,
            "respiratory_acidosis_index": resp_idx,
            "hyperchloremia_index": hypercl,
            "hypokalemia_index": float(np.clip((3.5 - self.K) / 1.0, 0.0, 1.0)),
            "hyperkalemia_index": float(np.clip((self.K - 5.0) / 2.0, 0.0, 1.0)),
            "pH_a": float(np.clip(pH, 6.75, 7.75)),
        })

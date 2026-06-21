
"""
Airway Obstruction Module — v0.13
=================================
Modulo qualitativo per asma/bronchiolite/status ostruttivo pediatrico.

Non è un modello clinicamente validato. Serve a collegare bronchospasm,
small-airway obstruction, mucus plugging, air trapping e broncodilatatori con:
  - R_rs / resistenza vie aeree
  - auto-PEEP intrinseca
  - dynamic hyperinflation
  - dead-space e shunt additivi
  - effetto broncodilatatore di salbutamolo/ipratropio/magnesio/ketamina
  - tachicardia qualitativa da β2-agonista/adrenalina nebulizzata
  - segnale separato di sollievo vie aeree superiori da adrenalina nebulizzata.
"""
from __future__ import annotations
import numpy as np
from typing import List

from core.base_module import BaseModule
from core.bus import PhysiologicalBus
from modules.pharmacology.pk_pd import hill


class AirwayObstructionModule(BaseModule):
    DEFAULT_PARAMS = {
        "baseline_bronchospasm": 0.0,
        "baseline_mucus_load": 0.0,
        "baseline_small_airway_obstruction": 0.0,
        "tau_obstruction_s": 45.0,
        "R_mod_max": 6.0,
        "air_trapping_tau_gain": 1.7,
        # rough PD EC50 placeholders
        "salbutamol_EC50": 0.08,       # mcg/kg/min continuous equivalent
        "ipratropium_EC50": 5.0,       # mcg/kg/h
        "magnesium_EC50": 25.0,        # mg/kg/h
        "epi_EC50": 0.05,              # mcg/kg/min nebulized equivalent
        "ketamine_EC50_mg_L": 0.45,
    }

    def __init__(self, params: dict | None = None):
        merged = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(name="AirwayObstruction", params=merged)
        self._bronchospasm = float(merged["baseline_bronchospasm"])
        self._mucus = float(merged["baseline_mucus_load"])
        self._small = float(merged["baseline_small_airway_obstruction"])
        # v3.2 RC2: keep commanded obstruction/shunt targets separate from
        # displayed module state. Earlier builds wrote bronchospasm/mucus/small
        # airway and airway_shunt_add back to the bus every step, so one-shot
        # scenario perturbations were immediately overwritten on the next cycle.
        self._target_bronchospasm = self._bronchospasm
        self._target_mucus = self._mucus
        self._target_small = self._small
        self._external_shunt_target = 0.0
        self._last_written_shunt = 0.0

    @property
    def input_keys(self) -> List[str]:
        return ["bronchospasm_index", "mucus_load", "small_airway_obstruction",
                "salbutamol_mcg_kg_min", "ipratropium_mcg_kg_h", "magnesium_mg_kg_h",
                "nebulized_epinephrine_mcg_kg_min", "C_ketamine_mg_L", "R_rs", "C_rs",
                "RR_total", "RR", "IE_ratio", "PEEP", "Paw_current", "Flow_current_mL_s"]

    @property
    def output_keys(self) -> List[str]:
        return ["airway_obstruction_index", "bronchospasm_index", "mucus_load",
                "small_airway_obstruction", "air_trapping_index", "dynamic_hyperinflation",
                "airway_resistance_mod", "airway_VdVt_add", "airway_shunt_add",
                "expiratory_time_constant_s", "auto_PEEP_obstructive", "bronchodilator_effect",
                "salbutamol_bronchodilation_signal", "salbutamol_tachycardia_signal",
                "ipratropium_bronchodilation_signal", "magnesium_bronchodilation_signal",
                "nebulized_epinephrine_bronchodilation_signal",
                "nebulized_epinephrine_upper_airway_relief_signal",
                "nebulized_epinephrine_tachycardia_signal",
                "upper_airway_relief_signal", "bronchodilator_HR_mod"]

    def initialize(self, bus: PhysiologicalBus) -> None:
        self._bronchospasm = float(np.clip(bus.get("bronchospasm_index"), 0.0, 1.0))
        self._mucus = float(np.clip(bus.get("mucus_load"), 0.0, 1.0))
        self._small = float(np.clip(bus.get("small_airway_obstruction"), 0.0, 1.0))
        self._target_bronchospasm = self._bronchospasm
        self._target_mucus = self._mucus
        self._target_small = self._small
        self._external_shunt_target = float(np.clip(bus.get("airway_shunt_add") if hasattr(bus.state, "airway_shunt_add") else 0.0, 0.0, 0.80))
        self._last_written_shunt = self._external_shunt_target
        self._write(bus)

    def _bronchodilator_components(self, bus: PhysiologicalBus) -> dict[str, float]:
        """Return directional respiratory-drug PD components.

        Step 3.6 keeps bronchodilator pharmacology in this airway module:
        these drugs change airway obstruction/resistance and expose small
        systemic audit signals, but they do not directly write MAP/SVR.
        """
        sal = hill(bus.get("salbutamol_mcg_kg_min"), self.params["salbutamol_EC50"], 0.55, 1.4)
        ipr = hill(bus.get("ipratropium_mcg_kg_h"), self.params["ipratropium_EC50"], 0.28, 1.2)
        mag = hill(bus.get("magnesium_mg_kg_h"), self.params["magnesium_EC50"], 0.25, 1.3)
        epi = hill(bus.get("nebulized_epinephrine_mcg_kg_min"), self.params["epi_EC50"], 0.40, 1.4)
        ket = hill(bus.get("C_ketamine_mg_L"), self.params["ketamine_EC50_mg_L"], 0.22, 1.4)
        combined = 1.0 - (1.0-sal)*(1.0-ipr)*(1.0-mag)*(1.0-epi)*(1.0-ket)
        upper_relief = hill(bus.get("nebulized_epinephrine_mcg_kg_min"), self.params["epi_EC50"], 0.70, 1.7)
        sal_tachy = hill(bus.get("salbutamol_mcg_kg_min"), self.params["salbutamol_EC50"], 0.16, 1.5)
        epi_tachy = hill(bus.get("nebulized_epinephrine_mcg_kg_min"), self.params["epi_EC50"], 0.12, 1.5)
        hr_mod = 1.0 + sal_tachy + 0.65 * epi_tachy
        return {
            "sal": float(np.clip(sal, 0.0, 1.0)),
            "ipr": float(np.clip(ipr, 0.0, 1.0)),
            "mag": float(np.clip(mag, 0.0, 1.0)),
            "epi": float(np.clip(epi, 0.0, 1.0)),
            "ket": float(np.clip(ket, 0.0, 1.0)),
            "combined": float(np.clip(combined, 0.0, 0.85)),
            "upper_relief": float(np.clip(upper_relief, 0.0, 0.85)),
            "sal_tachy": float(np.clip(sal_tachy, 0.0, 0.25)),
            "epi_tachy": float(np.clip(epi_tachy, 0.0, 0.20)),
            "hr_mod": float(np.clip(hr_mod, 1.0, 1.24)),
        }

    def _bronchodilator_effect(self, bus: PhysiologicalBus) -> float:
        return self._bronchodilator_components(bus)["combined"]

    def _write(self, bus: PhysiologicalBus) -> None:
        comp = self._bronchodilator_components(bus)
        bronchod = comp["combined"]
        # Broncospasmo è reversibile; mucus/small airway meno.
        bronch_eff = self._bronchospasm * (1.0 - 0.80 * bronchod)
        small_eff = self._small * (1.0 - 0.25 * bronchod)
        mucus_eff = self._mucus * (1.0 - 0.10 * bronchod)
        obstruction = float(np.clip(0.48*bronch_eff + 0.30*small_eff + 0.22*mucus_eff, 0.0, 1.0))

        # Resistenza: componente non lineare perché le piccole vie si chiudono in modo disproporzionato.
        R_mod = 1.0 + (self.params["R_mod_max"] - 1.0) * (obstruction ** 1.35)
        R_mod = float(np.clip(R_mod, 1.0, self.params["R_mod_max"]))

        C_rs = max(float(bus.get("C_rs")), 1.0)
        R_base = max(float(bus.get("R_rs")), 3.0)
        tau_exp = (R_base * R_mod / 1000.0) * C_rs  # s, R cmH2O/L/s -> /1000 and C mL/cmH2O
        tau_exp = float(np.clip(tau_exp, 0.05, 4.5))
        RR = float(bus.get("RR_total") if hasattr(bus.state, "RR_total") and bus.get("RR_total") > 0 else bus.get("RR"))
        cycle = 60.0 / max(RR, 1.0)
        IE = float(np.clip(bus.get("IE_ratio") if hasattr(bus.state, "IE_ratio") else 0.38, 0.1, 0.9))
        T_exp = cycle * (1.0 - IE)
        exp_ratio = tau_exp / max(T_exp, 0.10)
        air_trap = float(np.clip((exp_ratio - 0.45) / 1.65, 0.0, 1.0))
        dyn_hyper = float(np.clip(0.65*air_trap + 0.35*obstruction, 0.0, 1.0))
        auto_peep = float(np.clip(12.0 * air_trap * obstruction, 0.0, 14.0))
        if obstruction < 0.08 or air_trap < 0.05:
            auto_peep = 0.0

        # Dead-space da air trapping; shunt da mucus plugging/atelettasia.
        vd_add = float(np.clip(0.04*obstruction + 0.18*air_trap, 0.0, 0.30))
        intrinsic_shunt = float(np.clip(0.03*mucus_eff + 0.05*small_eff, 0.0, 0.18))
        # Direct scenario/event shunt targets, such as tension pneumothorax V/Q
        # proxies, are educationally distinct from bronchiolitis/asthma mucus.
        # Keep them persistent until a later perturbation lowers them.
        shunt_add = float(np.clip(max(intrinsic_shunt, self._external_shunt_target), 0.0, 0.80))
        self._last_written_shunt = shunt_add

        bus.update({
            "airway_obstruction_index": obstruction,
            "bronchospasm_index": float(self._bronchospasm),
            "mucus_load": float(self._mucus),
            "small_airway_obstruction": float(self._small),
            "airway_resistance_mod": R_mod,
            "air_trapping_index": air_trap,
            "dynamic_hyperinflation": dyn_hyper,
            "expiratory_time_constant_s": tau_exp,
            "auto_PEEP_obstructive": auto_peep,
            "airway_VdVt_add": vd_add,
            "airway_shunt_add": shunt_add,
            "bronchodilator_effect": bronchod,
            "salbutamol_bronchodilation_signal": comp["sal"],
            "salbutamol_tachycardia_signal": comp["sal_tachy"],
            "ipratropium_bronchodilation_signal": comp["ipr"],
            "magnesium_bronchodilation_signal": comp["mag"],
            "nebulized_epinephrine_bronchodilation_signal": comp["epi"],
            "nebulized_epinephrine_upper_airway_relief_signal": comp["upper_relief"],
            "nebulized_epinephrine_tachycardia_signal": comp["epi_tachy"],
            "upper_airway_relief_signal": comp["upper_relief"],
            "bronchodilator_HR_mod": comp["hr_mod"],
        })

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        tau = max(float(self.params["tau_obstruction_s"]), dt)
        # Target scenario/modifiche sul bus: permette perturbazioni dirette.
        # The same bus variables are also displayed outputs, so we only treat a
        # bus value as a new command when it differs from the module's last
        # written state. This preserves timeline commands across subsequent
        # smoothing steps instead of losing them immediately.
        incoming_b = float(np.clip(bus.get("bronchospasm_index"), 0.0, 1.0))
        incoming_m = float(np.clip(bus.get("mucus_load"), 0.0, 1.0))
        incoming_s = float(np.clip(bus.get("small_airway_obstruction"), 0.0, 1.0))
        incoming_shunt = float(np.clip(bus.get("airway_shunt_add") if hasattr(bus.state, "airway_shunt_add") else 0.0, 0.0, 0.80))

        if abs(incoming_b - self._bronchospasm) > 1e-6:
            self._target_bronchospasm = incoming_b
        if abs(incoming_m - self._mucus) > 1e-6:
            self._target_mucus = incoming_m
        if abs(incoming_s - self._small) > 1e-6:
            self._target_small = incoming_s
        if abs(incoming_shunt - self._last_written_shunt) > 1e-6:
            self._external_shunt_target = incoming_shunt

        a = 1.0 - np.exp(-dt/tau)
        self._bronchospasm += a * (self._target_bronchospasm - self._bronchospasm)
        self._mucus += a * (self._target_mucus - self._mucus)
        self._small += a * (self._target_small - self._small)
        self._write(bus)

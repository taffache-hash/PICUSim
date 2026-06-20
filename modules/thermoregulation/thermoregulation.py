"""
Thermoregulation Module v0.24
=============================

Modulo qualitativo per termoregolazione in PICU:
- febbre/sepsi, ipertermia, ipotermia
- brivido/shivering e soppressione da sedazione/NMB
- paracetamolo/antipiretico, cooling, warming
- effetti su VO2, HR, lattato e coagulazione

Non è un modello termodinamico fisico completo. Serve come asse fisiologico
esplorativo, integrato con metabolismo, sepsi, analgosedazione, coagulazione
e scenari neurologici/cooling.
"""
from __future__ import annotations
import numpy as np
from typing import List

from core.base_module import BaseModule
from core.bus import PhysiologicalBus


def _clip(x, lo, hi):
    return float(np.clip(x, lo, hi))


class ThermoregulationModule(BaseModule):
    DEFAULT_PARAMS = {
        "weight_kg": 20.0,
        "baseline_setpoint_C": 37.0,
        "tau_temp_s": 1500.0,
        "tau_cooling_s": 900.0,
        "tau_warming_s": 1200.0,
        "max_fever_setpoint_C": 40.5,
        "min_temp_C": 32.0,
        "max_temp_C": 42.2,
    }

    def __init__(self, params: dict | None = None):
        merged = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(name="Thermoregulation", params=merged)
        self._setpoint = float(merged["baseline_setpoint_C"])

    @property
    def input_keys(self) -> List[str]:
        return ["T_core", "infection_load", "cytokine_drive", "sepsis_severity_score",
                "paracetamol_active", "sedation_score", "drug_NMB_frac",
                "cooling_device_active", "external_warming_active", "target_temperature_C",
                "MAP", "lactate"]

    @property
    def output_keys(self) -> List[str]:
        return ["T_core", "setpoint_T", "fever_drive", "hypothermia_index",
                "hyperthermia_index", "shivering_index", "cooling_effect",
                "warming_effect", "antipyretic_effect", "heat_loss_index",
                "thermo_VO2_mod", "thermo_HR_add", "thermo_coag_mod",
                "thermo_lactate_mod", "temperature_instability_score"]

    def initialize(self, bus: PhysiologicalBus) -> None:
        self._setpoint = float(getattr(bus.state, "setpoint_T", self.params["baseline_setpoint_C"]))
        if hasattr(bus.state, "target_temperature_C") and bus.get("target_temperature_C") == 37.0:
            bus.set("target_temperature_C", self._setpoint)
        bus.update({
            "setpoint_T": self._setpoint,
            "fever_drive": 0.0,
            "hypothermia_index": max((36.0 - float(bus.get("T_core"))) / 4.0, 0.0),
            "hyperthermia_index": max((float(bus.get("T_core")) - 38.5) / 3.0, 0.0),
            "shivering_index": 0.0,
            "thermo_VO2_mod": 1.0,
            "thermo_HR_add": 0.0,
            "thermo_coag_mod": 1.0,
            "thermo_lactate_mod": 1.0,
            "temperature_instability_score": 0.0,
        })

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        T = float(bus.get("T_core"))
        infection = float(getattr(bus.state, "infection_load", 0.0))
        cytokine = float(getattr(bus.state, "cytokine_drive", 0.0))
        sepsis = float(getattr(bus.state, "sepsis_severity_score", 0.0))
        paracetamol = bool(getattr(bus.state, "paracetamol_active", False))
        sedation = float(getattr(bus.state, "sedation_score", 0.0))
        nmb = float(getattr(bus.state, "drug_NMB_frac", 0.0))
        cooling = bool(getattr(bus.state, "cooling_device_active", False))
        warming = bool(getattr(bus.state, "external_warming_active", False))
        target = float(getattr(bus.state, "target_temperature_C", 37.0))
        lactate = float(getattr(bus.state, "lactate", 1.0))
        MAP = float(getattr(bus.state, "MAP", 65.0))

        # Febbre: guidata da infezione/citochine/sepsi, ridotta da antipiretico.
        fever_drive = _clip(0.15 * infection + 0.55 * cytokine + 0.35 * sepsis, 0.0, 1.0)
        antipyretic_effect = 0.55 if paracetamol else 0.0
        fever_drive_eff = _clip(fever_drive * (1.0 - antipyretic_effect), 0.0, 1.0)
        febrile_setpoint = 37.0 + 2.5 * fever_drive_eff
        self._setpoint += (febrile_setpoint - self._setpoint) * (1.0 - np.exp(-dt / 600.0))
        self._setpoint = _clip(self._setpoint, 35.0, self.params["max_fever_setpoint_C"])

        # Cooling / warming modificano la temperatura corporea verso un target.
        dT_setpoint = (self._setpoint - T) * dt / self.params["tau_temp_s"]
        cooling_effect = 0.0
        warming_effect = 0.0
        if cooling:
            cooling_effect = _clip((T - target) / 3.0, 0.0, 1.0)
            dT_cool = -(max(T - target, 0.0)) * dt / self.params["tau_cooling_s"]
        else:
            dT_cool = 0.0
        if warming:
            warming_effect = _clip((target - T) / 3.0, 0.0, 1.0)
            dT_warm = (max(target - T, 0.0)) * dt / self.params["tau_warming_s"]
        else:
            dT_warm = 0.0

        # Shock profondo riduce capacità termoregolatoria: tende a instabilità/ipo.
        shock_cooling = -0.00005 * max(55.0 - MAP, 0.0) * dt
        T_new = _clip(T + dT_setpoint + dT_cool + dT_warm + shock_cooling,
                      self.params["min_temp_C"], self.params["max_temp_C"])

        # Shivering: mismatch freddo rispetto al setpoint o cooling attivo;
        # attenuato da sedazione profonda e blocco neuromuscolare.
        cold_gap = max(self._setpoint - T_new - 0.25, 0.0)
        cooling_shiver = 0.35 * cooling_effect
        suppression = _clip(0.55 * sedation + 0.85 * nmb, 0.0, 0.95)
        shivering = _clip((cold_gap / 2.0 + cooling_shiver) * (1.0 - suppression), 0.0, 1.0)

        hypothermia = _clip((36.0 - T_new) / 4.0, 0.0, 1.0)
        hyperthermia = _clip((T_new - 38.5) / 3.0, 0.0, 1.0)
        heat_loss = _clip(cooling_effect + max(T_new - 39.0, 0.0) / 3.0, 0.0, 1.0)

        # Modificatori downstream.
        q10_mod = 2.2 ** ((T_new - 37.0) / 10.0)
        thermo_VO2_mod = _clip(q10_mod * (1.0 + 0.40 * shivering), 0.70, 1.80)
        thermo_HR_add = _clip(8.0 * (T_new - 37.0) + 18.0 * shivering - 10.0 * hypothermia, -25.0, 35.0)
        thermo_coag_mod = _clip(1.0 + 0.60 * hypothermia + 0.18 * hyperthermia, 1.0, 1.8)
        thermo_lactate_mod = _clip(1.0 + 0.35 * shivering + 0.20 * hyperthermia + 0.15 * hypothermia, 1.0, 1.7)
        instability = _clip(0.30 * fever_drive + 0.35 * hypothermia + 0.35 * hyperthermia + 0.20 * shivering + 0.04 * max(lactate - 2.0, 0.0), 0.0, 1.0)

        bus.update({
            "T_core": T_new,
            "setpoint_T": self._setpoint,
            "fever_drive": fever_drive_eff,
            "hypothermia_index": hypothermia,
            "hyperthermia_index": hyperthermia,
            "shivering_index": shivering,
            "cooling_effect": cooling_effect,
            "warming_effect": warming_effect,
            "antipyretic_effect": antipyretic_effect,
            "heat_loss_index": heat_loss,
            "thermo_VO2_mod": thermo_VO2_mod,
            "thermo_HR_add": thermo_HR_add,
            "thermo_coag_mod": thermo_coag_mod,
            "thermo_lactate_mod": thermo_lactate_mod,
            "temperature_instability_score": instability,
        })

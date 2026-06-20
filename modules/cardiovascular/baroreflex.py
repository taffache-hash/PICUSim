"""
Baroreflex Module
=================
Baroreflex arterioso semplificato.

Meccanismo:
  - Baroriamo del seno carotideo: attivo tra 60–180 mmHg
  - Risposta efferente: modulazione di HR, SVR, contrattilità

Formulazione:
  errore = MAP - MAP_setpoint
  HR_target = HR_0 - G_HR × errore
  SVR_mod   → via bus (letto da Circulation)

  Risposta di primo ordine con τ_baroreflex ≈ 5 s.

Limitazioni intentional per scalabilità:
  - Baroreflex semplificato (1 compartimento, no nonlinearità)
  - Chemoreflex-baroreflex interazione non modellata (placeholder)
"""

from __future__ import annotations
import numpy as np
from typing import List

from core.base_module import BaseModule
from core.bus import PhysiologicalBus


class BaroreflexModule(BaseModule):
    """
    Baroreflex arterioso con risposta HR e SVR.

    Parametri
    ---------
    MAP_setpoint : float    MAP target [mmHg]
    G_HR        : float    Gain HR [bpm/mmHg] (default 1.0)
    G_SVR       : float    Gain SVR relativo [/mmHg] (default 0.01)
    HR_min, HR_max : float  Limiti HR [bpm]
    tau_baroreflex : float  Costante di tempo [s]
    """

    DEFAULT_PARAMS = {
        "MAP_setpoint":     65.0,    # mmHg — target fisiologico
        "G_HR":             1.5,     # bpm per mmHg
        "G_SVR_rel":        0.008,
        "HR_min":           40.0,
        "HR_max":           165.0,
        "tau_baroreflex":   8.0,     # s
        "auto_setpoint":    False,   # se True, adotta MAP iniziale come setpoint
        "enabled":          True,
    }

    def __init__(self, params: dict | None = None):
        merged = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(name="Baroreflex", params=merged)
        self._HR_current:  float = 110.0
        self._SVR_mod:     float = 1.0   # moltiplicatore SVR (non usato direttamente)

    @property
    def input_keys(self) -> List[str]:
        return ["MAP", "HR", "T_core", "lactate", "norad_mcg_kg_min",
                "sed_HR_mod", "drug_HR_mod", "bronchodilator_HR_mod",
                "stress_index", "sepsis_HR_add", "shock_HR_add", "thermo_HR_add", "neuro_HR_add"]

    @property
    def output_keys(self) -> List[str]:
        return ["HR"]

    def initialize(self, bus: PhysiologicalBus) -> None:
        self._HR_current = bus.get("HR")
        self._HR_reference = bus.get("HR")   # HR di baseline dello scenario

        # auto_setpoint: usa MAP iniziale dello scenario come target
        # Utile per bambino sano. Disabilitare per scenari patologici
        # dove MAP è già bassa (sepsi) e si vuole compensazione verso norma.
        if self.params.get("auto_setpoint", False):
            self.params["MAP_setpoint"] = bus.get("MAP")

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        if not self.params["enabled"]:
            return

        MAP = bus.get("MAP")
        tau = self.params["tau_baroreflex"]

        # Errore baroriflessivo
        err = MAP - self.params["MAP_setpoint"]

        # HR target: modulazione intorno all'HR di baseline dello scenario.
        # In shock/sepsi/febbre il baroriflesso non deve cancellare completamente
        # la tachicardia da stress metabolico/catecolamine.
        sed_HR_mod = bus.get("sed_HR_mod") if hasattr(bus.state, "sed_HR_mod") else 1.0
        drug_HR_mod = bus.get("drug_HR_mod") if hasattr(bus.state, "drug_HR_mod") else 1.0
        bronchodilator_HR_mod = bus.get("bronchodilator_HR_mod") if hasattr(bus.state, "bronchodilator_HR_mod") else 1.0
        stress_index = bus.get("stress_index") if hasattr(bus.state, "stress_index") else 0.0
        sepsis_HR_add = bus.get("sepsis_HR_add") if hasattr(bus.state, "sepsis_HR_add") else 0.0
        shock_HR_add = bus.get("shock_HR_add") if hasattr(bus.state, "shock_HR_add") else 0.0
        endocrine_HR_add = bus.get("endocrine_HR_add") if hasattr(bus.state, "endocrine_HR_add") else 0.0
        thermo_HR_add = bus.get("thermo_HR_add") if hasattr(bus.state, "thermo_HR_add") else 0.0
        neuro_HR_add = bus.get("neuro_HR_add") if hasattr(bus.state, "neuro_HR_add") else 0.0
        HR_target = (self._HR_reference * sed_HR_mod + 18.0 * stress_index + sepsis_HR_add + shock_HR_add + endocrine_HR_add + thermo_HR_add + neuro_HR_add - self.params["G_HR"] * err)
        HR_target *= float(np.clip(drug_HR_mod, 0.55, 1.65))
        # Step 3.6: β2-agonists/nebulized epinephrine can cause mild
        # tachycardia, but this is kept separate from PK-owned drug_HR_mod.
        HR_target *= float(np.clip(bronchodilator_HR_mod, 1.0, 1.24))

        T_core = bus.get("T_core") if hasattr(bus.state, "T_core") else 37.0
        lactate = bus.get("lactate") if hasattr(bus.state, "lactate") else 1.0
        norad = bus.get("norad_mcg_kg_min") if hasattr(bus.state, "norad_mcg_kg_min") else 0.0
        stress = max(T_core - 38.0, 0.0) + max(lactate - 2.0, 0.0) * 0.25 + max(norad, 0.0)
        if stress > 0.5:
            HR_floor = max(self.params["HR_min"], self._HR_reference * 0.82)
        else:
            HR_floor = self.params["HR_min"]

        HR_target = float(np.clip(HR_target, HR_floor, self.params["HR_max"]))

        # Risposta di primo ordine
        alpha = 1.0 - np.exp(-dt / tau)
        self._HR_current += alpha * (HR_target - self._HR_current)

        bus.update({"HR": float(self._HR_current)})

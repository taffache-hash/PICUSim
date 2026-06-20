"""
Transfusion Module
==================
Logica trasfusionale per GRC, PFC e piastrine.

Prodotti implementati:
  GRC (globuli rossi concentrati):
    - Hb ~22 g/dL, Ht 0.65
    - Volume tipico 10-20 mL/kg
    - Effetto: Hb↑, DO2↑ immediato
    - Effetto su CVP: +1-2 mmHg per 10 mL/kg

  PFC (plasma fresco congelato):
    - INR: riduzione verso 1.5 con τ~30 min
    - Fibrinogeno: +0.5 g/L per 10 mL/kg
    - Volume: contribuisce al bilancio idrico

  Piastrine concentrate:
    - PLT: +30-50 ×10^9/L per singola unità (~200 mL)
    - Effetto immediato

Trigger automatici configurabili (opzionale):
  - GRC se Hb < Hb_trigger
  - PFC se INR > INR_trigger
  - PLT se PLT < PLT_trigger

Output principali:
  transfusion_event : str   ultimo evento trasfusionale
  GRC_units_given   : int   unità GRC somministrate
  FFP_mL_given      : float mL PFC somministrati
  PLT_units_given   : int   unità PLT somministrate
"""

from __future__ import annotations
import numpy as np
from typing import List

from core.base_module import BaseModule
from core.bus import PhysiologicalBus


class TransfusionModule(BaseModule):
    """
    Modulo trasfusionale con trigger automatici e perturbazioni manuali.

    Parametri
    ---------
    Hb_trigger : float      Soglia Hb per GRC automatico [g/dL] (default 7.0)
    INR_trigger : float     Soglia INR per PFC automatico (default 2.0)
    PLT_trigger : float     Soglia PLT per concentrato piastrine [×10^9/L] (default 50)
    GRC_volume_mL_kg : float  Volume GRC per trasfusione [mL/kg] (default 15)
    auto_transfuse : bool   Abilita trigger automatici (default False)
    GRC_Hb_content : float  Hb nel GRC [g/dL] (default 22.0)
    infusion_duration_s : float  Durata infusione GRC [s] (default 900 = 15 min)
    weight_kg : float       Peso paziente
    plasma_volume_L : float Volume plasmatico [L]
    """

    DEFAULT_PARAMS = {
        "Hb_trigger":          7.0,
        "INR_trigger":         2.0,
        "PLT_trigger":        50.0,
        "GRC_volume_mL_kg":   15.0,
        "auto_transfuse":     False,
        "GRC_Hb_content":     22.0,   # g/dL
        "infusion_duration_s": 900.0, # 15 min
        "weight_kg":          20.0,
        "plasma_volume_L":     1.0,
        # PFC: 10 mL/kg → riduce INR, aumenta fibrinogeno
        "FFP_volume_mL_kg":   10.0,
        "FFP_INR_effect":      0.4,   # riduzione INR assoluta per 10 mL/kg
        "FFP_Fib_effect":      0.5,   # aumento fibrinogeno [g/L] per 10 mL/kg
        # PLT: 1 unità (~200 mL) → +30-50 ×10^9/L
        "PLT_increment":      40.0,   # ×10^9/L per unità
    }

    def __init__(self, params: dict | None = None):
        merged = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(name="Transfusion", params=merged)

        # Stato infusione GRC in corso
        self._GRC_infusing:     bool  = False
        self._GRC_t_remaining:  float = 0.0   # s rimasti
        self._GRC_rate_Hb_per_s: float = 0.0  # g/dL/s di aumento Hb

        # Contatori
        self._GRC_units:  int   = 0
        self._FFP_mL:     float = 0.0
        self._PLT_units:  int   = 0

        # Cooldown automatico (evita loop)
        self._auto_cooldown: float = 0.0   # s prima della prossima auto-trasfusione

    @property
    def input_keys(self) -> List[str]:
        return ["Hb", "INR", "PLT_count", "external_fluid_input_mL"]

    @property
    def output_keys(self) -> List[str]:
        # v0.35: Transfusion no longer writes final Hb/INR/PLT directly.
        # It writes product counters/ledgers; Hematology/Coagulation own final values.
        return ["external_fluid_input_mL", "RBC_transfused_mL",
                "GRC_units_given", "FFP_mL_given", "PLT_units_given"]

    def initialize(self, bus: PhysiologicalBus) -> None:
        self._GRC_infusing = False
        self._GRC_t_remaining = 0.0
        self._GRC_units = 0
        self._FFP_mL    = 0.0
        self._PLT_units = 0
        self._auto_cooldown = 0.0

        bus.update({
            "GRC_units_given":  0,
            "FFP_mL_given":     0.0,
            "PLT_units_given":  0,
        })

    # ------------------------------------------------------------------
    # API pubblica — chiamata dalle perturbazioni dello scenario
    # ------------------------------------------------------------------

    def give_GRC(self, bus: PhysiologicalBus, volume_mL: float | None = None) -> None:
        """
        Avvia infusione GRC.
        volume_mL: se None usa GRC_volume_mL_kg × weight_kg.
        """
        wt  = self.params["weight_kg"]
        vol = volume_mL or (self.params["GRC_volume_mL_kg"] * wt)
        dur = self.params["infusion_duration_s"]

        # ΔHb = (GRC_Hb - Hb_curr) × vol / (plasma_volume_L × 1000 + vol)
        Hb_curr      = bus.get("Hb")
        Hb_grc       = self.params["GRC_Hb_content"]
        V_plasma_mL  = self.params["plasma_volume_L"] * 1000.0
        Hb_final     = ((Hb_curr * V_plasma_mL + Hb_grc * vol) /
                         (V_plasma_mL + vol))
        delta_Hb     = Hb_final - Hb_curr

        self._GRC_rate_Hb_per_s = delta_Hb / dur
        self._GRC_t_remaining   = dur
        self._GRC_infusing      = True
        self._GRC_units        += 1
        # v0.31: route volume through the external fluid ledger.
        # v0.35: route RBC mass through RBC_transfused_mL; Hematology owns final Hb.
        bus.set("external_fluid_input_mL", bus.get("external_fluid_input_mL") + vol)
        bus.set("RBC_transfused_mL", float(getattr(bus.state, "RBC_transfused_mL", 0.0) + vol))

    def give_FFP(self, bus: PhysiologicalBus, volume_mL: float | None = None) -> None:
        """Somministra PFC: riduce INR, aumenta fibrinogeno."""
        wt  = self.params["weight_kg"]
        vol = volume_mL or (self.params["FFP_volume_mL_kg"] * wt)

        # Scala l'effetto per il volume somministrato (riferimento: 10 mL/kg)
        scale = vol / (self.params["FFP_volume_mL_kg"] * wt + 1e-3)

        # v0.35: do not write INR/fibrinogen directly. Coagulation reads
        # the cumulative FFP_mL_given counter and applies the effect on the next step.
        bus.set("external_fluid_input_mL", bus.get("external_fluid_input_mL") + vol)
        self._FFP_mL += vol

    def give_PLT(self, bus: PhysiologicalBus, units: int = 1) -> None:
        """Somministra concentrato piastrinico."""
        # v0.35: do not write PLT_count directly. Coagulation reads
        # PLT_units_given and applies the product effect.
        bus.set("external_fluid_input_mL",
                bus.get("external_fluid_input_mL") + 200.0 * units)
        self._PLT_units += units

    # ------------------------------------------------------------------
    # Step
    # ------------------------------------------------------------------

    def step(self, bus: PhysiologicalBus, dt: float) -> None:

        # --- 0. Manual pending products from scenario perturbations ---
        pending_grc = float(getattr(bus.state, "GRC_pending_mL", 0.0))
        if pending_grc > 0.0:
            self.give_GRC(bus, volume_mL=pending_grc)
            bus.set("GRC_pending_mL", 0.0)

        pending_ffp = float(getattr(bus.state, "FFP_pending_mL", 0.0))
        if pending_ffp > 0.0:
            self.give_FFP(bus, volume_mL=pending_ffp)
            bus.set("FFP_pending_mL", 0.0)

        pending_plt = int(getattr(bus.state, "PLT_pending_units", 0))
        if pending_plt > 0:
            self.give_PLT(bus, units=pending_plt)
            bus.set("PLT_pending_units", 0)

        # --- 1. Infusione GRC in corso ---
        if self._GRC_infusing:
            # v0.35: infusion timer is kept for event state only; Hb response is
            # applied by Hematology from RBC_transfused_mL.
            dt_inf = min(dt, self._GRC_t_remaining)
            self._GRC_t_remaining -= dt_inf
            if self._GRC_t_remaining <= 0:
                self._GRC_infusing = False

        # --- 2. Trigger automatici ---
        if self._auto_cooldown > 0:
            self._auto_cooldown -= dt

        if self.params["auto_transfuse"] and self._auto_cooldown <= 0:
            Hb  = bus.get("Hb")
            INR = bus.get("INR")
            PLT = bus.get("PLT_count")

            if Hb < self.params["Hb_trigger"] and not self._GRC_infusing:
                self.give_GRC(bus)
                self._auto_cooldown = 3600.0   # 1h cooldown

            elif INR > self.params["INR_trigger"]:
                self.give_FFP(bus)
                self._auto_cooldown = 1800.0

            elif PLT < self.params["PLT_trigger"]:
                self.give_PLT(bus)
                self._auto_cooldown = 3600.0

        # --- 3. Scrivi contatori nel Bus ---
        bus.update({
            "GRC_units_given":  self._GRC_units,
            "FFP_mL_given":     float(self._FFP_mL),
            "PLT_units_given":  self._PLT_units,
        })

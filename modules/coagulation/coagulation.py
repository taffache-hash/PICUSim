"""
Coagulation Module
==================
Dinamica della coagulazione in PICU: CID, trombocitopenia, disfibrinogenemia.

Variabili di stato:
  INR           [1.0–8.0]   rapporto normalizzato internazionale
  PLT_count     [×10^9/L]   conta piastrinica
  fibrinogen    [g/L]        fibrinogeno
  d_dimer       [mg/L FEU]  D-dimero (marker di fibrinolisi)
  AT3           [%]          antitrombina III (marcatore consumo)

Modello evoluzione in CID/sepsi:
  - PLT: consumo proporzionale a intensità SIRS; nadir in 24-72h
  - INR: prolungamento da deficit fattori (produzione epatica ridotta)
  - Fibrinogeno: bifasico (↑ reattivo poi ↓ da consumo in CID avanzata)
  - D-dimero: sale con fibrinolisi
  - AT3: scende per consumo (inversamente proporzionale a coagulopatia)

Soglie di allerta:
  PLT < 50   → rischio emorragico severo
  INR > 2.0  → coagulopatia significativa
  Fib < 1.0  → ipofibrinogenemia → rischio CID
  D-dim > 5  → fibrinolisi attiva

Risposta alle trasfusioni:
  PFC → INR↓, Fib↑ (gestito da TransfusionModule)
  PLT concentrate → PLT↑
  Fibrinogeno concentrato → Fib↑ direttamente

Output anche:
  coag_score [0-4]: score CID semplificato (ISTH score)
"""

from __future__ import annotations
import numpy as np
from typing import List

from core.base_module import BaseModule
from core.bus import PhysiologicalBus


class CoagulationModule(BaseModule):
    """
    Dinamica della coagulazione e DIC.

    Parametri
    ---------
    INR_baseline        : float   1.0
    PLT_baseline        : float   200.0  [×10^9/L]
    fibrinogen_baseline : float   2.5    [g/L]
    d_dimer_baseline    : float   0.3    [mg/L FEU]
    AT3_baseline        : float   100.0  [%]

    SIRS intensità di consumo (proporzionale a SIRS_factor - 1):
    PLT_consumption_rate_per_h   : float  %/h per unità SIRS extra (5.0)
    INR_increase_rate_per_h      : float  INR/h per unità SIRS extra (0.08)
    fibrinogen_biphasic_peak_h   : float  Ore al picco fibrinogeno acuto (6)
    fibrinogen_consumption_h     : float  Ore al nadir fibrinogeno in DIC (24)
    d_dimer_rise_rate_per_h      : float  mg/L/h per unità SIRS (0.3)

    Epatico (dipende da MAP):
    liver_factor_synthesis_rate  : float  Produzione fattori coagulativi (MAP-dep)
    """

    DEFAULT_PARAMS = {
        "INR_baseline":        1.0,
        "PLT_baseline":       200.0,
        "fibrinogen_baseline": 2.5,
        "d_dimer_baseline":    0.3,
        "AT3_baseline":       100.0,
        # Consumo da SIRS
        "PLT_consumption_rate_per_h":  5.0,    # % PLT/h per unità SIRS extra
        "INR_increase_rate_per_h":     0.08,   # INR/h
        "fibrinogen_consumption_h":    0.05,   # g/L/h in CID
        "fibrinogen_acute_rise_rate":  0.20,   # g/L/h nelle prime 6h (fase acuta)
        "fibrinogen_acute_peak_h":     6.0,    # h al picco
        "d_dimer_rise_rate_per_h":     0.3,    # mg/L/h per unità SIRS extra
        "AT3_consumption_rate_per_h":  2.0,    # %/h
        # Recovery spontanea (senza SIRS)
        "PLT_recovery_rate_per_h":     4.0,    # ×10^9/L/h
        "INR_recovery_rate_per_h":     0.03,
        "fibrinogen_recovery_rate":    0.10,
        # Epatico MAP-dipendente
        "liver_MAP_thresh":           50.0,
        # Limiti fisiologici
        "PLT_max":   600.0,
        "INR_max":     8.0,
        "Fib_max":     8.0,
        "d_dim_max":  50.0,
    }

    def __init__(self, params: dict | None = None):
        merged = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(name="Coagulation", params=merged)

        self._INR:    float = merged["INR_baseline"]
        self._PLT:    float = merged["PLT_baseline"]
        self._Fib:    float = merged["fibrinogen_baseline"]
        self._Ddim:   float = merged["d_dimer_baseline"]
        self._AT3:    float = merged["AT3_baseline"]
        self._t_sim:  float = 0.0   # per fase bifasica fibrinogeno
        self._last_FFP_mL_given: float = 0.0
        self._last_PLT_units_given: int = 0

    @property
    def input_keys(self) -> List[str]:
        return ["MAP", "steroid_SIRS_mod", "lactate", "sepsis_coag_mod",
                "hepatic_INR_contribution", "hepatic_perfusion_index", "thermo_coag_mod",
                "GRC_units_given", "FFP_mL_given", "PLT_units_given"]

    @property
    def output_keys(self) -> List[str]:
        return ["INR", "PLT_count", "fibrinogen",
                "d_dimer", "AT3", "coag_score"]

    def initialize(self, bus: PhysiologicalBus) -> None:
        self._INR   = self.params["INR_baseline"]
        self._PLT   = self.params["PLT_baseline"]
        self._Fib   = self.params["fibrinogen_baseline"]
        self._Ddim  = self.params["d_dimer_baseline"]
        self._AT3   = self.params["AT3_baseline"]
        self._t_sim = 0.0
        self._last_FFP_mL_given = float(getattr(bus.state, "FFP_mL_given", 0.0))
        self._last_PLT_units_given = int(getattr(bus.state, "PLT_units_given", 0))

        bus.update({
            "INR":        self._INR,
            "PLT_count":  self._PLT,
            "fibrinogen": self._Fib,
            "d_dimer":    self._Ddim,
            "AT3":        self._AT3,
            "coag_score": 0,
        })

    def _SIRS_intensity(self, bus: PhysiologicalBus) -> float:
        """SIRS intensity extra (0 = nessuna infiammazione)."""
        # Proxy: lattato alto e SIRS_mod basso indicano infiammazione
        lactate = bus.get("lactate")
        SIRS_mod = bus.get("steroid_SIRS_mod") \
                   if hasattr(bus.state, "steroid_SIRS_mod") else 1.0
        # SIRS_mod < 1 → anti-infiammatori attivi
        # Lattato > 2 → danno tissutale / consumo coagulativo
        sirs_extra = max(lactate - 1.5, 0.0) * 0.5 * SIRS_mod
        sepsis_coag_mod = bus.get("sepsis_coag_mod") if hasattr(bus.state, "sepsis_coag_mod") else 1.0
        return float(np.clip(sirs_extra * sepsis_coag_mod, 0.0, 5.0))

    def _liver_function(self, MAP: float) -> float:
        """Funzione epatica [0-1]: ridotta se MAP < soglia."""
        thresh = self.params["liver_MAP_thresh"]
        return float(np.clip((MAP - 30.0) / (thresh - 30.0), 0.05, 1.0))

    def _coag_score(self) -> int:
        """
        ISTH score CID semplificato [0-4]:
          PLT < 100 → +1; < 50 → +2
          INR 1.5-2 → +1; > 2 → +2
          Fib < 1.5 → +1
          D-dim > 3 → +1
        """
        score = 0
        score += 2 if self._PLT < 50 else (1 if self._PLT < 100 else 0)
        score += 2 if self._INR > 2.0 else (1 if self._INR > 1.5 else 0)
        score += 1 if self._Fib < 1.5 else 0
        score += 1 if self._Ddim > 3.0 else 0
        return min(score, 8)

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        # v0.35: Coagulation owns final INR/PLT/fibrinogen. Transfusion writes
        # cumulative product counters; Coagulation applies incremental effects.
        pending_fib = float(getattr(bus.state, "fibrinogen_pending_g", 0.0))
        if pending_fib > 0.0:
            self._Fib = float(np.clip(self._Fib + pending_fib, 0.2, self.params["Fib_max"]))
            bus.set("fibrinogen_pending_g", 0.0)

        ffp_total = float(getattr(bus.state, "FFP_mL_given", 0.0))
        ffp_delta = max(ffp_total - self._last_FFP_mL_given, 0.0)
        self._last_FFP_mL_given = ffp_total
        if ffp_delta > 0.0:
            wt = float(getattr(bus.state, "weight_kg", 20.0))
            scale = ffp_delta / (10.0 * max(wt, 1.0) + 1e-6)
            self._INR = float(np.clip(self._INR - 0.4 * scale, 1.0, self.params["INR_max"]))
            self._Fib = float(np.clip(self._Fib + 0.5 * scale, 0.2, self.params["Fib_max"]))

        plt_total = int(getattr(bus.state, "PLT_units_given", 0))
        plt_delta = max(plt_total - self._last_PLT_units_given, 0)
        self._last_PLT_units_given = plt_total
        if plt_delta > 0:
            self._PLT = float(np.clip(self._PLT + 40.0 * plt_delta, 0.0, self.params["PLT_max"]))

        MAP          = bus.get("MAP")
        sirs_extra   = self._SIRS_intensity(bus)
        thermo_coag_mod = bus.get("thermo_coag_mod") if hasattr(bus.state, "thermo_coag_mod") else 1.0
        sirs_extra = float(np.clip(sirs_extra * thermo_coag_mod, 0.0, 6.0))
        liver_fn     = self._liver_function(MAP)
        dt_h         = dt / 3600.0
        self._t_sim += dt_h

        # --- PLT ---
        consumption_PLT = self.params["PLT_consumption_rate_per_h"] * sirs_extra
        recovery_PLT    = self.params["PLT_recovery_rate_per_h"] * liver_fn * (1.0 - sirs_extra * 0.2)
        dPLT = (-consumption_PLT + max(recovery_PLT, 0)) * dt_h
        self._PLT = float(np.clip(self._PLT + dPLT,
                                   0.0, self.params["PLT_max"]))

        # --- INR ---
        hepatic_contrib = float(getattr(bus.state, "hepatic_INR_contribution", 0.0))
        hepatic_perf = float(getattr(bus.state, "hepatic_perfusion_index", 1.0))
        liver_fn = float(np.clip(liver_fn * np.clip(hepatic_perf, 0.25, 1.1), 0.05, 1.0))
        prolungamento = self.params["INR_increase_rate_per_h"] * sirs_extra * (2.0 - liver_fn) + 0.08 * hepatic_contrib
        recovery_INR  = self.params["INR_recovery_rate_per_h"] * liver_fn
        target_INR    = self.params["INR_baseline"] + sirs_extra * 0.8 + hepatic_contrib
        dINR = (prolungamento - recovery_INR * (self._INR - 1.0)) * dt_h
        self._INR = float(np.clip(self._INR + dINR,
                                   1.0, self.params["INR_max"]))

        # --- Fibrinogeno (bifasico) ---
        # Fase acuta (prime 6h): Fib sale (reattante di fase acuta)
        # Poi in CID: Fib cala per consumo
        if self._t_sim < self.params["fibrinogen_acute_peak_h"] and sirs_extra > 0.5:
            dFib = self.params["fibrinogen_acute_rise_rate"] * sirs_extra * dt_h
        else:
            # Consumo da DIC
            consumption_Fib = self.params["fibrinogen_consumption_h"] * sirs_extra
            recovery_Fib    = self.params["fibrinogen_recovery_rate"] * liver_fn
            dFib = (recovery_Fib - consumption_Fib) * dt_h

        self._Fib = float(np.clip(self._Fib + dFib,
                                   0.2, self.params["Fib_max"]))

        # --- D-dimero ---
        rise_Ddim = self.params["d_dimer_rise_rate_per_h"] * sirs_extra
        # Clearance renale (ridotta se MAP bassa)
        clear_Ddim = 0.2 * liver_fn
        dDdim = (rise_Ddim - clear_Ddim * self._Ddim) * dt_h
        self._Ddim = float(np.clip(self._Ddim + dDdim,
                                    0.1, self.params["d_dim_max"]))

        # --- AT3 ---
        consumption_AT3 = self.params["AT3_consumption_rate_per_h"] * sirs_extra
        recovery_AT3    = 1.0 * liver_fn
        dAT3 = (-consumption_AT3 + recovery_AT3 * (self.params["AT3_baseline"] - self._AT3) * 0.1) * dt_h
        self._AT3 = float(np.clip(self._AT3 + dAT3, 10.0, 120.0))

        bus.update({
            "INR":        float(self._INR),
            "PLT_count":  float(self._PLT),
            "fibrinogen": float(self._Fib),
            "d_dimer":    float(self._Ddim),
            "AT3":        float(self._AT3),
            "coag_score": int(self._coag_score()),
        })

"""
Inhaled Nitric Oxide (iNO) Module
===================================
Vasodilatazione polmonare selettiva da ossido nitrico inalato.

Fisica:
  - Hill dose-risposta su PVR: Emax=0.55, EC50=10 ppm, n=0.8
    (calibrato su Sitbon 1998, Barst 1998, Davidson 1998)
  - Effetto selettivo polmonare: NO inattivato da Hb entro 1-2s
    → nessun effetto su SVR sistemica
  - Onset rapido: τ_onset = 60s (equilibrio alveolo→arteriola)
  - Cessazione: τ_offset = 30s (wash-out rapido)
  - Miglioramento ossigenazione: riduzione Qs/Qt per redistribuzione
    flusso verso unità ventilate (vasocostrizione ipossica → invertita)
  - Effetto su RV afterload: PAP↓ → EDV_rv↓ → potenziale miglioramento CO
    in cuore destro sovraccaricato

Output:
  ino_PVR_mod    : moltiplicatore su PVR [0-1] (< 1 = riduzione)
  ino_Qs_Qt_mod  : riduzione shunt relativa [0-1]
  ino_ppm        : dose corrente [ppm] (echo del Bus)
  ino_pulmonary_vasodilation_signal : audit [0-1]
  ino_oxygenation_signal            : audit [0-1]
  ino_rebound_risk_signal           : audit [0-1] se sospeso dopo effetto
"""

from __future__ import annotations
import numpy as np
from typing import List

from core.base_module import BaseModule
from core.bus import PhysiologicalBus


def _hill(C: float, EC50: float, Emax: float, n: float = 1.0) -> float:
    if C <= 0:
        return 0.0
    Cn = C ** n
    return float(Emax * Cn / (EC50 ** n + Cn))


class INOModule(BaseModule):
    """
    Modulo iNO — vasodilatazione polmonare selettiva.

    Parametri
    ---------
    EC50_ppm : float    EC50 per riduzione PVR [ppm] (default 10)
    Emax_PVR : float    Riduzione massima PVR [0-1] (default 0.55 = 55%)
    n_hill   : float    Coefficiente Hill (default 0.8 — curva sub-lineare)
    Emax_Qs  : float    Riduzione massima Qs/Qt (default 0.35)
    tau_onset_s : float Costante di tempo effetto [s] (default 60)
    tau_offset_s: float Costante di tempo wash-out [s] (default 30)
    """

    DEFAULT_PARAMS = {
        "EC50_ppm":     10.0,
        "Emax_PVR":      0.55,
        "n_hill":        0.80,
        "Emax_Qs":       0.35,
        "tau_onset_s":  60.0,
        "tau_offset_s": 30.0,
    }

    def __init__(self, params: dict | None = None):
        merged = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(name="iNO", params=merged)
        self._PVR_mod_current: float = 1.0
        self._Qs_mod_current:  float = 1.0

    @property
    def input_keys(self) -> List[str]:
        # v0.31: iNO no longer writes final PVR/PAP. Circulation owns those
        # variables and applies ino_PVR_mod as an explicit modifier.
        return ["ino_ppm"]

    @property
    def output_keys(self) -> List[str]:
        return ["ino_PVR_mod", "ino_Qs_Qt_mod",
                "ino_pulmonary_vasodilation_signal", "ino_oxygenation_signal",
                "ino_rebound_risk_signal"]

    def initialize(self, bus: PhysiologicalBus) -> None:
        self._PVR_mod_current = 1.0
        self._Qs_mod_current  = 1.0
        bus.update({
            "ino_PVR_mod":   1.0,
            "ino_Qs_Qt_mod": 1.0,
            "ino_pulmonary_vasodilation_signal": 0.0,
            "ino_oxygenation_signal": 0.0,
            "ino_rebound_risk_signal": 0.0,
        })

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        ppm = bus.get("ino_ppm")

        # --- Effetto target (Hill) ---
        E_PVR = _hill(ppm, self.params["EC50_ppm"],
                      self.params["Emax_PVR"], self.params["n_hill"])
        E_Qs  = _hill(ppm, self.params["EC50_ppm"],
                      self.params["Emax_Qs"],  self.params["n_hill"])

        PVR_mod_target = 1.0 - E_PVR   # < 1 → riduzione PVR
        Qs_mod_target  = 1.0 - E_Qs

        # --- Filtro temporale (onset/offset) ---
        if ppm > 0:
            tau = self.params["tau_onset_s"]
        else:
            tau = self.params["tau_offset_s"]

        alpha = 1.0 - np.exp(-dt / tau)
        self._PVR_mod_current += alpha * (PVR_mod_target - self._PVR_mod_current)
        self._Qs_mod_current  += alpha * (Qs_mod_target  - self._Qs_mod_current)

        pvr_mod = float(np.clip(self._PVR_mod_current, 0.30, 1.0))
        qs_mod = float(np.clip(self._Qs_mod_current, 0.30, 1.0))
        vasodil_signal = float(np.clip(1.0 - pvr_mod, 0.0, 1.0))
        oxy_signal = float(np.clip(1.0 - qs_mod, 0.0, 1.0))
        rebound_risk = float(np.clip((1.0 - pvr_mod) if ppm <= 0 else 0.0, 0.0, 1.0))

        # v0.31: write only modifiers. Circulation is the owner of final
        # PVR/PAP_mean and applies ino_PVR_mod during its own step. Step 3.6
        # adds explicit audit signals and no systemic SVR/MAP coupling.
        bus.update({
            "ino_PVR_mod": pvr_mod,
            "ino_Qs_Qt_mod": qs_mod,
            "ino_pulmonary_vasodilation_signal": vasodil_signal,
            "ino_oxygenation_signal": oxy_signal,
            "ino_rebound_risk_signal": rebound_risk,
        })

"""
Chemoreflex Drive Module
========================
Public educational model of ventilatory drive.

The module combines a central CO2/pH component, a peripheral hypoxic component,
and pharmacologic/neurologic modifiers to generate muscular pressure and a
spontaneous respiratory-rate tendency. It is a qualitative control-loop model,
not a validated patient-specific controller.

Revision v1.23 fixes spontaneous-mode RR drift by anchoring the response to the
baseline scenario respiratory rate rather than repeatedly multiplying the current
Bus RR.
"""

from __future__ import annotations
import numpy as np
from typing import List

from core.base_module import BaseModule
from core.bus import PhysiologicalBus


class ChemoreflexModule(BaseModule):
    """
    Modulo di drive ventilatorio chemioriflessivo.

    Parametri
    ---------
    phi : float [0-1]
        0 = puro chemioriflessivo; 1 = drive fisso (PSV classica)
        Default 0.5 (scenario clinicamente realistico)
    CO2_drive_threshold : float
        CO2 response threshold [mmHg] (default 37)
    PaO2_crit : float
        Soglia ipossica per drive periferico [mmHg] (default 60)
    Pmus_baseline : float
        Pmus di baseline [cmH2O] al PaCO2 iniziale
    tau_drive_s : float
        Costante di tempo del drive [s] (ritardo neurale)
    RR_min, RR_max : float
        Range frequenza respiratoria guidata [atti/min]
    """

    DEFAULT_PARAMS = {
        "phi":              0.5,
        "CO2_drive_threshold":     37.0,    # mmHg
        "PaO2_crit":        60.0,    # mmHg
        "Pmus_baseline":    5.0,     # cmH2O
        "Pmus_max":         20.0,    # cmH2O
        "tau_drive_s":      3.0,     # s
        "RR_min":           10.0,
        "RR_max":           60.0,
        "gain_CO2":         None,    # stimato al baseline se None
        "gain_O2":          0.5,     # cmH2O per mmHg sotto PaO2_crit
    }

    def __init__(self, params: dict | None = None):
        merged = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(name="Chemoreflex", params=merged)

        self._Pmus_current: float = self.params["Pmus_baseline"]
        self._RR_current:   float = 25.0
        self._RR_baseline:  float = 25.0
        self._gain_CO2:     float = 0.0   # stimato in initialize
        self._Pmus_fixed:   float = self.params["Pmus_baseline"]

    @property
    def input_keys(self) -> List[str]:
        return ["PaCO2", "PaO2", "pH_a", "RR", "Pmus", "drug_drive_mod",
                "drug_NMB_frac", "sed_resp_mod", "neuro_resp_drive_mod"]

    @property
    def output_keys(self) -> List[str]:
        return ["Pmus", "RR", "drive_level", "spontaneous_effort_available",
                "neuromuscular_blockade_active", "nmb_trigger_block_active"]

    def initialize(self, bus: PhysiologicalBus) -> None:
        PaCO2_0 = bus.get("PaCO2")
        self._Pmus_fixed   = self.params["Pmus_baseline"]
        self._Pmus_current = self.params["Pmus_baseline"]
        self._RR_current   = bus.get("RR")
        self._RR_baseline  = bus.get("RR")

        # Gain CO2: stima da consistenza al baseline
        # Al baseline: Pmus_0 = gain_CO2 × (PaCO2_0 - CO2 threshold)
        excess_CO2 = max(PaCO2_0 - self.params["CO2_drive_threshold"], 0.1)
        if self.params["gain_CO2"] is None:
            self._gain_CO2 = self.params["Pmus_baseline"] / excess_CO2
        else:
            self._gain_CO2 = float(self.params["gain_CO2"])

        bus.update({
            "Pmus":        self._Pmus_current,
            "drive_level": 1.0,
        })

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        PaCO2 = bus.get("PaCO2")
        PaO2  = bus.get("PaO2")
        phi   = self.params["phi"]
        tau   = self.params["tau_drive_s"]

        # --- Componente CO2 (centrale) ---
        excess_CO2 = max(PaCO2 - self.params["CO2_drive_threshold"], 0.0)
        Pmus_CO2   = self._gain_CO2 * excess_CO2

        # --- Componente O2 (periferica) ---
        deficit_O2 = max(self.params["PaO2_crit"] - PaO2, 0.0)
        Pmus_O2    = self.params["gain_O2"] * deficit_O2

        # --- Pmus target chemioriflessivo ---
        Pmus_chemo = float(np.clip(
            Pmus_CO2 + Pmus_O2,
            0.0, self.params["Pmus_max"]
        ))

        # --- Mix fisso vs chemioriflessivo ---
        Pmus_target = phi * self._Pmus_fixed + (1 - phi) * Pmus_chemo

        # --- Modulazione farmacologica (sedazione/NMB) ---
        # drug_drive_mod: 1=normale, 0=apnea (midazolam/propofol), sed_resp_mod
        # carries opioid respiratory depression, and drug_NMB_frac is the single
        # neuromuscular-blockade path for rocuronium.
        NMB_frac   = float(np.clip(bus.get("drug_NMB_frac"), 0.0, 1.0))
        drive_mod  = float(np.clip(bus.get("drug_drive_mod"), 0.0, 1.5))
        sed_resp_mod = float(np.clip(bus.get("sed_resp_mod"), 0.0, 1.5)) if hasattr(bus.state, "sed_resp_mod") else 1.0
        neuro_resp_drive_mod = float(np.clip(bus.get("neuro_resp_drive_mod"), 0.0, 1.5)) if hasattr(bus.state, "neuro_resp_drive_mod") else 1.0
        motor_availability = float(np.clip(1.0 - NMB_frac, 0.0, 1.0))
        Pmus_target *= drive_mod * sed_resp_mod * neuro_resp_drive_mod * motor_availability

        # --- Filtro temporale (ritardo neurale) ---
        alpha = 1.0 - np.exp(-dt / tau)
        self._Pmus_current += alpha * (Pmus_target - self._Pmus_current)

        # --- RR guidato dal drive (proporzionale a Pmus) ---
        # Nei modi controllati (PCV/VCV/HFOV) il ventilatore mantiene la RR
        # impostata; il chemioriflesso modifica Pmus/drive ma non prende il
        # controllo della frequenza macchina. Nei modi spontanei/assistiti,
        # invece, ipercapnia/ipossia possono aumentare RR.
        mode = str(bus.get("vent_mode")) if hasattr(bus.state, "vent_mode") else "PCV"
        if mode in ("PCV", "VCV", "HFOV"):
            RR_target = bus.get("RR")
        else:
            # In spontaneous/assisted modes, the displayed spontaneous RR should
            # follow available motor output, not the unblocked chemical stimulus.
            # Full NMB therefore produces apnea/no effective spontaneous trigger.
            drive_normalized = Pmus_target / (self.params["Pmus_baseline"] + 1e-3)
            if drive_normalized <= 0.05:
                RR_target = 0.0
            else:
                RR_target = np.clip(
                    self._RR_baseline * drive_normalized,
                    self.params["RR_min"],
                    self.params["RR_max"]
                )
        self._RR_current += alpha * (RR_target - self._RR_current)

        # --- Drive level normalizzato (1 = baseline) ---
        drive_level = float(np.clip(
            self._Pmus_current / (self._Pmus_fixed + 1e-3),
            0.0, 5.0
        ))

        bus.update({
            "Pmus":        float(self._Pmus_current),
            "RR":          float(self._RR_current),
            "drive_level": drive_level,
            "spontaneous_effort_available": float(np.clip(1.0 - NMB_frac, 0.0, 1.0)),
            "neuromuscular_blockade_active": bool(NMB_frac >= 0.90),
            "nmb_trigger_block_active": bool(NMB_frac >= 0.90),
        })

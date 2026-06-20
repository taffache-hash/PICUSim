"""
Metabolism & Thermoregulation Module
======================================
Modella il metabolismo energetico e la termoregolazione.

Fisica implementata:
  - VO2 e VCO2 dinamici funzione di T_core (legge Q10)
  - Effetto farmaci: sedazione riduce VO2 (rilassamento muscolare)
  - Effetto NMB: rocuronio elimina contributo muscolare
  - Effetto sepsi/infiammazione: SIRS aumenta VO2
  - Termoregolazione: T_core converge a setpoint con τ~30 min
  - Setpoint febbre modulabile da antipiretici
  - Produzione di lattato: da anaerobiosi quando DO2 critica
  - Clearance lattato: epatica, MAP-dipendente

Output principali: VO2, VCO2, lactate (v0.31: Thermoregulation owns T_core/setpoint_T)
"""

from __future__ import annotations
import numpy as np
from typing import List

from core.base_module import BaseModule
from core.bus import PhysiologicalBus


class MetabolismModule(BaseModule):
    """
    Metabolismo energetico e termoregolazione.

    Parametri
    ---------
    VO2_baseline_per_kg : float
        VO2 basale [mL/kg/min] (default 6.0 per bambino 5 anni)
    weight_kg : float
        Peso [kg]
    Q10 : float
        Coefficiente Q10 metabolico (default 2.3)
    T_setpoint_baseline : float
        Setpoint termico baseline [°C] (37 in eutermia, 39 in febbre)
    tau_thermo_s : float
        Costante di tempo termoregolazione [s] (default 1800 = 30 min)
    SIRS_factor : float
        Moltiplicatore VO2 per sepsi/infiammazione (1.0=normale, 1.5=sepsi grave)
    lactate_DO2_crit : float
        DO2 critica sotto cui inizia la produzione di lattato [mL/min]
    lactate_clearance_half : float
        Clearance lattato a MAP normale [mmol/L/h]
    paracetamol_effect : float
        Riduzione setpoint per dose standard paracetamolo [°C/h]
    """

    DEFAULT_PARAMS = {
        "VO2_baseline_per_kg":    6.0,    # mL/kg/min
        "weight_kg":              20.0,   # kg
        "RQ_baseline":            0.85,   # quoziente respiratorio
        "Q10":                    2.3,    # coefficiente Q10
        "T_setpoint_baseline":    37.0,   # °C
        "tau_thermo_s":           1800.0, # s (30 min)
        "k_skin":                 4.0,    # W/°C (perdita cutanea)
        "T_ambient":              24.0,   # °C (PICU standard)
        "SIRS_factor":            1.0,    # 1.0=normale, 1.3-1.8=sepsi
        # Lattato
        "lactate_DO2_crit":       300.0,  # mL/min (DO2 critica per 20 kg)
        "lactate_prod_gain":      0.05,   # mmol/L per mL/min di deficit DO2
        "lactate_clearance_rate": 0.5,    # mmol/L/h a MAP normale
        # Antipiretici (effetto sul setpoint)
        "paracetamol_active":     False,
        "paracetamol_effect_per_h": 0.5, # °C/h di riduzione setpoint
        # NMB: riduzione VO2 muscolare
        "VO2_muscle_frac":        0.30,  # 30% di VO2 è muscolare
        # Sedazione: riduzione VO2 cerebrale/metabolica
        "VO2_sedation_frac":      0.15,  # 15% di VO2 è cerebrale/sedazione-sensibile
    }

    def __init__(self, params: dict | None = None):
        merged = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(name="Metabolism", params=merged)
        self._T_setpoint: float = merged["T_setpoint_baseline"]
        self._lactate:    float = 1.0   # sovrascritto in initialize() dal bus

    @property
    def input_keys(self) -> List[str]:
        return ["T_core", "DO2", "MAP", "drug_drive_mod",
                "drug_NMB_frac", "norad_mcg_kg_min", "sed_VO2_mod",
                "sepsis_VO2_mod", "sepsis_lactate_prod_mod",
                "shock_lactate_prod_mod", "shock_lactate_clearance_mod",
                "thermo_VO2_mod", "thermo_lactate_mod", "infection_lactate_mod",
                "cerebral_metabolic_rate_mod", "hepatic_lactate_clearance_mod",
                "CRRT_lactate_target_mmol_L", "CRRT_active_effective"]

    @property
    def output_keys(self) -> List[str]:
        # v0.31: Thermoregulation is the sole owner of T_core and setpoint_T.
        # Metabolism reads temperature and writes VO2/lactate only.
        return ["VO2", "lactate"]

    def initialize(self, bus: PhysiologicalBus) -> None:
        self._T_setpoint = self.params["T_setpoint_baseline"]
        # Legge il lattato iniziale dal bus (impostato dallo scenario)
        self._lactate = float(bus.get("lactate"))
        # VO2 iniziale coerente con T_core dello scenario
        T0 = bus.get("T_core")
        VO2_0 = self._compute_VO2(T0, 1.0, 0.0)
        bus.update({
            "VO2":        float(VO2_0),
            "lactate":    float(self._lactate),
        })

    def _compute_VO2(self, T_core: float,
                     drive_mod: float, NMB_frac: float) -> float:
        """
        VO2 effettiva [mL/min].

        Contributi:
          VO2_base × Q10^((T-37)/10) × SIRS
          - riduzione da NMB (blocco muscolare)
          - riduzione da sedazione profonda
        """
        wt   = self.params["weight_kg"]
        Q10  = self.params["Q10"]
        SIRS = self.params["SIRS_factor"]

        # Effetto temperatura (Q10)
        VO2_temp = (self.params["VO2_baseline_per_kg"] * wt *
                    Q10 ** ((T_core - 37.0) / 10.0))

        # Effetto SIRS
        VO2_temp *= SIRS

        # Riduzione NMB (muscoli paralizzati)
        muscle_red = NMB_frac * self.params["VO2_muscle_frac"]

        # Riduzione sedazione (cerebrale)
        sed_red = (1.0 - drive_mod) * self.params["VO2_sedation_frac"]

        VO2 = VO2_temp * (1.0 - muscle_red - sed_red)
        return float(max(VO2, 20.0))   # floor fisiologico

    def _update_temperature(self, T_core: float, VO2: float, dt: float) -> float:
        """
        dT/dt = (T_setpoint - T_core) / τ_thermo
        + brivido/diaforesi modellati implicitamente nel setpoint.
        """
        tau = self.params["tau_thermo_s"]
        dT  = (self._T_setpoint - T_core) * dt / tau
        return float(np.clip(T_core + dT, 30.0, 43.0))

    def _update_setpoint(self, dt: float) -> None:
        """Modifica del setpoint per antipiretici."""
        if self.params["paracetamol_active"]:
            rate = self.params["paracetamol_effect_per_h"] / 3600.0  # °C/s
            self._T_setpoint = max(
                self._T_setpoint - rate * dt,
                self.params["T_ambient"] + 13.0   # minimo fisiologico 37°C
            )

    def _update_lactate(self, DO2: float, MAP: float, dt: float) -> float:
        """
        Lattato: produzione quando DO2 < DO2_crit, clearance epatica MAP-dep.

        Scala temporale fisiologica:
          - Clearance epatica normale: t½ ~60 min (k = ln2/60 min = 0.0116/min)
          - In shock severo (MAP<50): clearance quasi azzerata
          - Produzione da anaerobiosi: proporzionale al deficit DO2

        Riferimento: Levraut 1998, Jansen 2010 — t½ lattato ~44-72 min
        in sepsi trattata; in shock non trattato la clearance è quasi nulla.
        """
        # Clearance epatica: primo ordine con t½ = 60 min a MAP normale
        # k_clear = ln(2) / t½ = 0.693 / 3600 s = 1.93e-4 s-1
        import math
        t_half_s    = 3600.0   # 60 min in secondi
        k_clear_base = math.log(2) / t_half_s   # s-1 = 1.93e-4

        # MAP-dependence: clearance si riduce proporzionalmente sotto MAP 70
        # A MAP<40: clearance ~5% (produzione domina)
        MAP_factor = float(np.clip((MAP - 40.0) / 30.0, 0.05, 1.0))
        hepatic_clear_mod = float(getattr(self, "_hepatic_lactate_clearance_mod", 1.0))
        shock_clear_mod = float(getattr(self, "_shock_lactate_clearance_mod", 1.0))
        k_clear = k_clear_base * MAP_factor * hepatic_clear_mod * shock_clear_mod   # s-1 effettiva

        # Produzione da anaerobiosi (DO2 < DO2_crit)
        DO2_deficit  = max(self.params["lactate_DO2_crit"] - DO2, 0.0)
        # prod_gain in mmol/L/h per mL/min di deficit → converti in /s
        prod_rate_s  = self.params["lactate_prod_gain"] * DO2_deficit / 3600.0
        # v0.14: microcirculatory failure in sepsis increases lactate generation
        # even when global DO2 appears acceptable.
        try:
            sepsis_lactate_mod = float(getattr(self, "_sepsis_lactate_prod_mod", 1.0))
        except Exception:
            sepsis_lactate_mod = 1.0
        shock_lactate_prod_mod = float(getattr(self, "_shock_lactate_prod_mod", 1.0))
        prod_rate_s *= sepsis_lactate_mod * shock_lactate_prod_mod

        # dL/dt = produzione - clearance × [lattato]
        dL = (prod_rate_s - k_clear * self._lactate) * dt

        return float(np.clip(self._lactate + dL, 0.2, 25.0))

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        T_core     = bus.get("T_core")
        DO2        = bus.get("DO2")
        MAP        = bus.get("MAP")
        drive_mod  = bus.get("drug_drive_mod")
        NMB_frac   = bus.get("drug_NMB_frac")

        # v0.31: setpoint/temperature dynamics are owned by Thermoregulation.
        # Metabolism only reads T_core.

        # VO2 effettiva
        VO2 = self._compute_VO2(T_core, drive_mod, NMB_frac)
        sed_VO2_mod = bus.get("sed_VO2_mod") if hasattr(bus.state, "sed_VO2_mod") else 1.0
        sepsis_VO2_mod = bus.get("sepsis_VO2_mod") if hasattr(bus.state, "sepsis_VO2_mod") else 1.0
        endocrine_VO2_mod = bus.get("endocrine_VO2_mod") if hasattr(bus.state, "endocrine_VO2_mod") else 1.0
        thermo_VO2_mod = bus.get("thermo_VO2_mod") if hasattr(bus.state, "thermo_VO2_mod") else 1.0
        cerebral_metabolic_rate_mod = bus.get("cerebral_metabolic_rate_mod") if hasattr(bus.state, "cerebral_metabolic_rate_mod") else 1.0
        self._sepsis_lactate_prod_mod = bus.get("sepsis_lactate_prod_mod") if hasattr(bus.state, "sepsis_lactate_prod_mod") else 1.0
        self._shock_lactate_prod_mod = bus.get("shock_lactate_prod_mod") if hasattr(bus.state, "shock_lactate_prod_mod") else 1.0
        self._shock_lactate_clearance_mod = bus.get("shock_lactate_clearance_mod") if hasattr(bus.state, "shock_lactate_clearance_mod") else 1.0
        endocrine_lactate_mod = bus.get("endocrine_lactate_mod") if hasattr(bus.state, "endocrine_lactate_mod") else 1.0
        thermo_lactate_mod = bus.get("thermo_lactate_mod") if hasattr(bus.state, "thermo_lactate_mod") else 1.0
        infection_lactate_mod = bus.get("infection_lactate_mod") if hasattr(bus.state, "infection_lactate_mod") else 1.0
        self._sepsis_lactate_prod_mod *= endocrine_lactate_mod * thermo_lactate_mod * infection_lactate_mod
        self._hepatic_lactate_clearance_mod = bus.get("hepatic_lactate_clearance_mod") if hasattr(bus.state, "hepatic_lactate_clearance_mod") else 1.0
        VO2 = float(np.clip(VO2 * sed_VO2_mod * sepsis_VO2_mod * endocrine_VO2_mod * thermo_VO2_mod * cerebral_metabolic_rate_mod, 20.0, self.params["VO2_baseline_per_kg"] * self.params["weight_kg"] * 3.6))

        # Lattato (owner). CRRT/liver/sepsis write modifiers or targets.
        self._lactate = self._update_lactate(DO2, MAP, dt)
        crrt_eff = bus.get("CRRT_active_effective") if hasattr(bus.state, "CRRT_active_effective") else 0.0
        if crrt_eff > 0.0 and hasattr(bus.state, "CRRT_lactate_target_mmol_L"):
            crrt_target = float(bus.get("CRRT_lactate_target_mmol_L"))
            self._lactate = float(np.clip(min(self._lactate, crrt_target), 0.2, 25.0))

        bus.update({
            "VO2":        float(VO2),
            "lactate":    float(self._lactate),
        })

"""
Glucose & Nutrition Module
===========================
Glicemia dinamica e bilancio nutrizionale in PICU.

Fisica:
  Glicemia [mmol/L] come variabile di stato continua.

  Sorgenti di glucosio:
    - GIR (glucose infusion rate) [mg/kg/min] — configurabile
    - Gluconeogenesi epatica (baseline + stress)
    - Nutrizione parenterale/enterale (TPN/NE)

  Consumo di glucosio:
    - Tessuti periferici (insulino-indipendente: cervello, RBC)
    - Tessuti insulino-sensibili (modulati da SIRS, steroidi)
    - VO2 metabolica (proporzionale al consumo O2)

  Perturbatori:
    - SIRS: insulino-resistenza → glicemia ↑
    - Steroidi: gluconeogenesi ↑, insulino-resistenza ↑
    - Ipoglicemia < 3.5 mmol/L → effetto su drive neurale
    - Iperglicemia > 12 mmol/L → diuresi osmotica

  Insulina (semplificata):
    - v1.16: usa il segnale PK/PD insulinico se prodotto da PharmacologyModule
    - fallback legacy: clearance proporzionale all'infusione insulinica [UI/h]

Output:
  glucose_mmol_L     : glicemia [mmol/L]
  GIR_mg_kg_min      : infusion rate glucosio corrente
  insulin_UI_h       : infusione insulina corrente
  glucose_hypoglycemia: bool — allarme ipoglicemia
  glucose_hyperglycemia: bool — allarme iperglicemia
  caloric_balance_kcal_h: bilancio calorico [kcal/h]
"""

from __future__ import annotations
import numpy as np
from typing import List

from core.base_module import BaseModule
from core.bus import PhysiologicalBus
from core.profile_scaling import bus_patient_scalars


# Costanti
_GLUCOSE_MW = 180.16   # g/mol
_KCAL_PER_G_GLUCOSE = 3.75
_KCAL_PER_ML_O2 = 0.0048  # kcal/mL O2 (equivalente calorico medio)


class GlucoseModule(BaseModule):
    """
    Glicemia e nutrizione dinamica.

    Parametri
    ---------
    glucose_baseline_mmol_L : float  Glicemia baseline [mmol/L] (5.0)
    weight_kg               : float  Peso [kg]
    GIR_mg_kg_min           : float  Glucose infusion rate [mg/kg/min] (default 4.0)
    insulin_UI_h            : float  Insulina in infusione [UI/h] (default 0)
    SIRS_insulin_resistance : float  Fattore insulino-resistenza da SIRS (0-1)
    hepatic_gluconeogenesis_rate : float  Gluconeogenesi epatica [mmol/L/h] (0.3)
    glucose_hypoglycemia_thresh  : float  Soglia ipoglicemia [mmol/L] (3.5)
    glucose_hyperglycemia_thresh : float  Soglia iperglicemia [mmol/L] (10.0)
    caloric_target_kcal_kg_h     : float  Target calorico [kcal/kg/h] (4.0)
    """

    DEFAULT_PARAMS = {
        "glucose_baseline_mmol_L":       5.0,
        "weight_kg":                    20.0,
        # Infusioni default
        "GIR_mg_kg_min":                 4.0,   # glucosio infuso
        "insulin_UI_h":                  0.0,
        "TPN_kcal_kg_h":                 0.0,   # nutrizione parenterale totale
        "EN_kcal_kg_h":                  0.0,   # nutrizione enterale
        # Metabolismo basale del glucosio
        "glucose_consumption_mmol_L_h": 1.2,   # consumo basale (tessuti non-insulino-dip)
        "insulin_sensitivity":          0.8,    # clearance insulinica relativa
        "hepatic_gluconeogenesis_rate": 0.3,    # mmol/L/h baseline
        # Stress response
        "SIRS_glucose_gain":            0.5,   # mmol/L/h per unità SIRS extra (>1.0)
        # Effetti glicemia estrema
        "glucose_hypoglycemia_thresh":  3.5,
        "glucose_hyperglycemia_thresh": 10.0,
        "osmotic_diuresis_gain":        0.15,  # aumento diuresi per mmol/L sopra soglia
        "insulin_pk_max_clearance_mmol_L_h": 4.0,
        # Calorie
        "caloric_target_kcal_kg_h":     4.0,
    }

    def __init__(self, params: dict | None = None):
        merged = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(name="Glucose", params=merged)
        self._glucose: float = merged["glucose_baseline_mmol_L"]
        self._caloric_intake_kcal_h: float = 0.0

    @property
    def input_keys(self) -> List[str]:
        return ["VO2", "T_core", "steroid_glucose_add",
                "steroid_SIRS_mod", "MAP", "urine_rate_mL_h",
                "C_insulin_mU_L", "insulin_glucose_clearance_signal",
                "insulin_effective_clearance_mmol_L_h"]

    @property
    def output_keys(self) -> List[str]:
        return ["glucose_mmol_L", "glucose_hypoglycemia",
                "glucose_hyperglycemia", "caloric_balance_kcal_h"]

    def initialize(self, bus: PhysiologicalBus) -> None:
        info = bus_patient_scalars(bus, self.params)
        self.params["weight_kg"] = info["weight_kg"]
        age_group = info["age_group"]
        # v0.45: pragmatic age-specific glucose handling anchors.
        if age_group == "neonate":
            self.params["GIR_mg_kg_min"] = max(float(self.params.get("GIR_mg_kg_min", 4.0)), 5.0)
            self.params["glucose_hypoglycemia_thresh"] = 2.6
            self.params["glucose_consumption_mmol_L_h"] *= 1.20
        elif age_group == "infant":
            self.params["GIR_mg_kg_min"] = max(float(self.params.get("GIR_mg_kg_min", 4.0)), 4.5)
            self.params["glucose_hypoglycemia_thresh"] = 3.0
            self.params["glucose_consumption_mmol_L_h"] *= 1.10
        elif age_group == "adolescent":
            self.params["insulin_sensitivity"] = float(self.params.get("insulin_sensitivity", 0.8)) * 0.90
        self._glucose = float(bus.get("glucose_mmol_L") if hasattr(bus.state, "glucose_mmol_L") else self.params["glucose_baseline_mmol_L"])
        bus.update({
            "glucose_mmol_L":       self._glucose,
            "glucose_hypoglycemia": False,
            "glucose_hyperglycemia": False,
            "caloric_balance_kcal_h": 0.0,
        })

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        info  = bus_patient_scalars(bus, self.params)
        wt    = info["weight_kg"]
        self.params["weight_kg"] = wt
        VO2   = bus.get("VO2")         # mL/min
        MAP   = bus.get("MAP")

        # --- Sorgenti glucosio ---
        # 1. GIR (infusione EV)
        GIR   = bus.get("GIR_mg_kg_min") if hasattr(bus.state, "GIR_mg_kg_min") \
                else self.params["GIR_mg_kg_min"]
        GIR_mmol_min = GIR * wt / _GLUCOSE_MW        # mmol/min
        # Distribuzione in volume plasmatico + LEC (approssimato: 0.2 L/kg)
        V_dist_L     = wt * ({"neonate": 0.30, "infant": 0.25, "toddler": 0.22}.get(info["age_group"], 0.20))
        GIR_mmol_L_h = GIR_mmol_min * 60.0 / V_dist_L   # mmol/L/h

        # 2. Gluconeogenesi epatica (ridotta se MAP bassa)
        MAP_hepatic_frac = float(np.clip((MAP - 40.0) / 40.0, 0.0, 1.0))
        gluco_neo = self.params["hepatic_gluconeogenesis_rate"] * MAP_hepatic_frac

        # 3. Steroidi + endocrine stress axis → gluconeogenesi extra
        steroid_gluc = bus.get("steroid_glucose_add") / 24.0   # mmol/L/h (spread su 24h)
        endocrine_glucose_mod = bus.get("endocrine_glucose_prod_mod") if hasattr(bus.state, "endocrine_glucose_prod_mod") else 1.0
        insulin_sensitivity_mod = bus.get("insulin_sensitivity_mod") if hasattr(bus.state, "insulin_sensitivity_mod") else 1.0
        # Stress hormones increase hepatic output; applied as a modifier to baseline gluconeogenesis.
        gluco_neo *= float(np.clip(endocrine_glucose_mod, 0.8, 2.8))

        # --- Consumo glucosio ---
        # Basale (insulino-indipendente: cervello ~0.4, RBC ~0.2)
        consumption_basal = self.params["glucose_consumption_mmol_L_h"] * 0.6

        # Insulino-dipendente (muscolo, fegato) — ridotto da insulino-resistenza
        # SIRS_mod < 1 → anti-infiammatorio, ma insulino-resistenza è separata
        SIRS_factor = bus.get("steroid_SIRS_mod") if hasattr(bus.state, "steroid_SIRS_mod") else 1.0
        # SIRS_insulin_resistance: SIRS > 1 → resistenza
        sirs_raw = getattr(bus.state, "SIRS_factor", 1.0) if hasattr(bus.state, "SIRS_factor") else 1.0
        insulin_resist = 1.0 + self.params["SIRS_glucose_gain"] * max(sirs_raw - 1.0, 0.0)
        # Consumo insulino-dipendente (ridotto per resistenza)
        consumption_insulin = (self.params["glucose_consumption_mmol_L_h"] * 0.4
                               / insulin_resist)

        # Consumo proporzionale a VO2 (metabolismo cellulare)
        VO2_correction = VO2 / 120.0    # normalizzato a baseline 120 mL/min
        consumption_total = (consumption_basal + consumption_insulin) * VO2_correction

        # Insulina: v1.16 usa il segnale PK/PD centralizzato se disponibile.
        # Fallback legacy: effetto immediato proporzionale all'infusione UI/h.
        if hasattr(bus.state, "insulin_effect_revision") and int(getattr(bus.state, "insulin_effect_revision", 0)) >= 116:
            pk_signal = float(np.clip(getattr(bus.state, "insulin_glucose_clearance_signal", 0.0), 0.0, 1.0))
            pk_clearance = float(getattr(bus.state, "insulin_effective_clearance_mmol_L_h", 0.0))
            insulin_clearance = pk_clearance * float(np.clip(insulin_sensitivity_mod, 0.20, 1.10))
        else:
            insulin_clearance = ((bus.get("insulin_UI_h")
                                  if hasattr(bus.state, "insulin_UI_h")
                                  else self.params["insulin_UI_h"]) * 0.10
                                 * float(self.params.get("insulin_sensitivity", 0.8))
                                 * float(np.clip(insulin_sensitivity_mod, 0.20, 1.10)))

        # --- Bilancio glicemico ---
        dG_dt_h = (GIR_mmol_L_h + gluco_neo + steroid_gluc
                   - consumption_total - insulin_clearance)
        dG = dG_dt_h * dt / 3600.0   # mmol/L per timestep

        self._glucose = float(np.clip(self._glucose + dG, 0.5, 30.0))

        # --- Effetti soglie ---
        hypo  = self._glucose < self.params["glucose_hypoglycemia_thresh"]
        hyper = self._glucose > self.params["glucose_hyperglycemia_thresh"]

        # Ipoglicemia → riduce drive neurale (effetto su bus)
        if hypo and hasattr(bus.state, "drug_drive_mod"):
            deficit = max(self.params["glucose_hypoglycemia_thresh"] - self._glucose, 0)
            bus.set("drug_drive_mod",
                    float(np.clip(bus.get("drug_drive_mod") * (1.0 - 0.10 * deficit), 0.1, 1.5)))

        # Iperglicemia → diuresi osmotica (aumenta urine_rate)
        if hyper and hasattr(bus.state, "urine_rate_mL_h"):
            osmotic_extra = (self._glucose - self.params["glucose_hyperglycemia_thresh"]) \
                            * self.params["osmotic_diuresis_gain"] * wt
            bus.set("urine_rate_mL_h",
                    float(bus.get("urine_rate_mL_h") + osmotic_extra))

        # --- Bilancio calorico ---
        kcal_GIR   = GIR * wt / 1000.0 * _KCAL_PER_G_GLUCOSE * 60.0   # kcal/h
        kcal_TPN   = self.params["TPN_kcal_kg_h"] * wt
        kcal_EN    = self.params["EN_kcal_kg_h"] * wt
        kcal_intake = kcal_GIR + kcal_TPN + kcal_EN

        kcal_consumed = VO2 * _KCAL_PER_ML_O2 * 60.0   # kcal/h
        caloric_balance = kcal_intake - kcal_consumed

        bus.update({
            "glucose_mmol_L":        float(self._glucose),
            "glucose_hypoglycemia":  bool(hypo),
            "glucose_hyperglycemia": bool(hyper),
            "caloric_balance_kcal_h": float(caloric_balance),
        })

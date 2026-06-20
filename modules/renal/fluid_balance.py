"""
Renal & Fluid Balance Module — completo
==========================================
Modella il rene e il bilancio idrico in PICU.

Fisica implementata:

RENE
  - GFR pressure-dependent (autoregolazione miogena 50-90 mmHg)
  - Effetto noradrenalina su GFR (vasocostrizione afferente)
  - Riassorbimento tubulare (frazione filtrazione → urina)
  - Diuresi oraria come output
  - AKI: progressivo deterioramento GFR con MAP bassa prolungata

BILANCIO IDRICO
  - Apporti: infusioni continue (mL/h configurabili per scenario)
  - Perdite: diuresi, insensibili (perspiratio + febbre)
  - Bilancio idrico cumulativo [mL]
  - Emodiluizione: Hb scende con fluid overload significativo

EFFETTI EMODINAMICI
  - Fluid overload: aumenta CVP (→ bus), riduce compliance polmonare
  - Ipovolemia: riduce CVP e preload

Output principali:
  GFR [mL/min], urine_rate_mL_h, fluid_balance [mL],
  Hb [g/dL], CVP_fluid_correction
"""

from __future__ import annotations
import numpy as np
from typing import List

from core.base_module import BaseModule
from core.bus import PhysiologicalBus
from core.profile_scaling import bus_patient_scalars, bsa_m2


class FluidBalanceModule(BaseModule):
    """
    Rene + bilancio idrico completo.

    Parametri
    ---------
    weight_kg : float
        Peso [kg] — per scaling
    GFR_baseline : float
        GFR baseline [mL/min] (default 70 per bambino 20 kg)
    tubular_reabs_frac : float
        Frazione di riassorbimento tubulare (default 0.9929 → ~0.7% urina)
    infusion_rate_mL_h : float
        Infusione basale [mL/h] (fluido di mantenimento)
    insensible_mL_h : float
        Perdite insensibili baseline [mL/h]
    T_insensible_gain : float
        Aumento perdite insensibili per grado sopra 37°C [mL/h/°C]
    Hb_baseline : float
        Hb iniziale del paziente [g/dL]
    Hb_dilution_per_100mL : float
        Riduzione Hb per 100 mL di bilancio positivo [g/dL]
    AKI_time_const_s : float
        Costante di tempo per danno renale da ipoperfusione prolungata [s]
    MAP_autoregulation_low : float
        Soglia inferiore autoregolazione MAP [mmHg]
    MAP_autoregulation_high : float
        Soglia superiore autoregolazione MAP [mmHg]
    """

    DEFAULT_PARAMS = {
        "weight_kg":             20.0,
        # GFR (bambino 20 kg, eGFR ~100 mL/min/1.73m2 → ~70 mL/min per BSA~0.7)
        "GFR_baseline":          70.0,   # mL/min
        "tubular_reabs_frac":    0.9929, # → urina = 0.71% del filtrato
        # Autoregolazione renale
        "MAP_autoregulation_low":  50.0, # mmHg
        "MAP_autoregulation_high": 90.0, # mmHg
        # Effetto norad su GFR (vasocostrizione afferente)
        "norad_GFR_effect":      -0.08,  # riduzione relativa per mcg/kg/min
        # Infusioni
        "infusion_rate_mL_h":    30.0,   # 1.5 mL/kg/h fluido mantenimento
        # Perdite insensibili
        "insensible_mL_h":       15.0,   # mL/h baseline
        "T_insensible_gain":      3.0,   # mL/h per °C sopra 37
        # Emodiluizione
        "Hb_baseline":           11.0,   # g/dL
        "plasma_volume_L":        1.0,   # L (approssimato per 20 kg)
        # Solo una quota dei cristalloidi resta nel compartimento intravascolare.
        # Usare tutto il bilancio positivo sovrastimava l'emodiluizione.
        "crystalloid_intravascular_frac": 0.25,
        "Hb_transfusion_trigger": 7.0,   # g/dL — threshold trasfusionale
        # AKI da ipoperfusione
        "AKI_MAP_threshold":     45.0,   # mmHg
        "AKI_time_const_s":   7200.0,    # 2 ore → danno significativo
        # Fluid overload: effetto su CVP e compliance polmonare
        # +2 mmHg di CVP per ogni 250 mL di bilancio positivo (10 mL/kg)
        "fluid_CVP_gain":        0.008,  # mmHg per mL di bilancio positivo
        "fluid_C_rs_reduction":  0.005,  # riduzione C_rs per 100 mL positivo
    }

    def __init__(self, params: dict | None = None):
        merged = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(name="FluidBalance", params=merged)

        # Stato interno
        self._fluid_balance: float = 0.0      # mL (cumulativo)
        self._urine_cumulative: float = 0.0   # mL
        self._AKI_index: float = 0.0          # [0-1] progressione danno
        self._GFR_current: float = merged["GFR_baseline"]
        self._Hb_current: float = merged["Hb_baseline"]
        self._last_external_fluid_input_mL: float = 0.0

    @property
    def input_keys(self) -> List[str]:
        return ["MAP", "T_core", "norad_mcg_kg_min", "fluid_balance", "Hb",
                "endothelial_leak_index", "sepsis_GFR_mod",
                "furosemide_effect_signal", "diuretic_response_index",
                "external_fluid_input_mL", "CRRT_UF_mL_h_effective",
                "crystalloid_rate_mL_h", "crystalloid_type", "GIR_mg_kg_min",
                "shock_hypovolemia_index"]

    @property
    def output_keys(self) -> List[str]:
        return ["GFR", "urine_rate_mL_h", "fluid_balance",
                "AKI_index", "fluid_CVP_correction",
                "fluid_responsiveness", "preload_reserve", "capillary_leak_index",
                "furosemide_effective_diuretic_signal", "furosemide_urine_gain",
                "furosemide_additional_urine_mL_h", "diuretic_hypovolemia_risk",
                "cumulative_fluid_input_mL", "cumulative_urine_output_mL",
                "cumulative_insensible_loss_mL", "fluid_balance_error_mL",
                "crystalloid_active", "crystalloid_effective_mL_h",
                "crystalloid_balanced_fraction", "crystalloid_chloride_load_index",
                "crystalloid_glucose_GIR_mg_kg_min", "crystalloid_preload_response",
                "crystalloid_MAP_support_mmHg", "crystalloid_renal_perfusion_gain",
                "cumulative_crystalloid_input_mL"]

    def initialize(self, bus: PhysiologicalBus) -> None:
        info = bus_patient_scalars(bus, self.params)
        wt = info["weight_kg"]
        prof = info["profile"]
        self.params["weight_kg"] = wt
        self.params["GFR_baseline"] = float(prof.get("GFR_ml_min_1_73m2", self.params["GFR_baseline"])) * bsa_m2(wt, info["age_y"]) / 1.73
        self.params["infusion_rate_mL_h"] = max(1.5 * wt, 1.0)
        self.params["insensible_mL_h"] = max(0.6 * wt, 1.0)
        self.params["plasma_volume_L"] = max(0.045 * wt, 0.08)
        map_anchor = float(prof.get("MAP", getattr(bus.state, "MAP", 65.0)))
        self.params["MAP_autoregulation_low"] = max(25.0, 0.65 * map_anchor)
        self.params["MAP_autoregulation_high"] = max(self.params["MAP_autoregulation_low"] + 10.0, map_anchor + 15.0)
        self._fluid_balance = bus.get("fluid_balance")
        self._Hb_current    = self.params["Hb_baseline"]
        self._AKI_index     = 0.0
        self._GFR_current   = self.params["GFR_baseline"]
        self._last_external_fluid_input_mL = float(getattr(bus.state, "external_fluid_input_mL", 0.0))

        bus.update({
            "GFR":                  self._GFR_current,
            "urine_rate_mL_h":      self._compute_urine_rate(
                                        self._GFR_current),
            "AKI_index":            0.0,
            "fluid_CVP_correction": 0.0,
            "crystalloid_active": False,
            "crystalloid_effective_mL_h": 0.0,
            "crystalloid_balanced_fraction": 0.0,
            "crystalloid_chloride_load_index": 0.0,
            "crystalloid_glucose_GIR_mg_kg_min": 0.0,
            "crystalloid_preload_response": 0.0,
            "crystalloid_MAP_support_mmHg": 0.0,
            "crystalloid_renal_perfusion_gain": 0.0,
        })

    # ------------------------------------------------------------------
    # GFR pressure-dependent con autoregolazione
    # ------------------------------------------------------------------

    def _GFR_pressure_frac(self, MAP: float) -> float:
        """
        Frazione della GFR baseline in funzione di MAP.
        Curva autoregolazione miogena (sigmoide approssimata con lineare
        a tratti tra MAP_low e MAP_high).
        """
        lo = self.params["MAP_autoregulation_low"]
        hi = self.params["MAP_autoregulation_high"]

        if MAP < lo:
            # Oliguria/anuria sotto soglia
            frac = 0.05 * np.clip(MAP / lo, 0.0, 1.0)
        elif MAP <= hi:
            # Zona autoregolazione: lineare da 5% a 100%
            frac = 0.05 + 0.95 * (MAP - lo) / (hi - lo)
        else:
            # Iperfiltrazione leggera sopra la soglia
            frac = 1.0 + 0.003 * (MAP - hi)   # +0.3% per mmHg

        return float(np.clip(frac, 0.0, 1.30))

    def _update_AKI(self, MAP: float, dt: float) -> None:
        """
        Accumulo danno renale da ipoperfusione prolungata.
        AKI_index [0-1]: 0=normale, 1=anuria completa.
        """
        thresh = self.params["AKI_MAP_threshold"]
        tau    = max(float(self.params["AKI_time_const_s"]), 60.0)

        if MAP < thresh:
            # Accumulo progressivo
            damage_rate = (thresh - MAP) / thresh / tau
            self._AKI_index = min(self._AKI_index + damage_rate * dt, 1.0)
        else:
            # Lenta recovery (τ × 3)
            self._AKI_index = max(
                self._AKI_index - dt / (tau * 3.0), 0.0
            )

    def _compute_urine_rate(self, GFR: float) -> float:
        """Diuresi [mL/h] da GFR effettiva."""
        reabs = self.params["tubular_reabs_frac"]
        return float(GFR * (1.0 - reabs) * 60.0)   # mL/min × 60 → mL/h

    def _update_Hb(self, fluid_balance: float) -> float:
        """
        Emodiluizione: Hb scende con bilancio positivo.
        Modello lineare: Hb(t) = Hb_base × Vplasma / (Vplasma + ΔV_pos)
        ΔV positivo → emodiluizione.
        """
        V_plasma_mL = self.params["plasma_volume_L"] * 1000.0
        frac = float(self.params.get("crystalloid_intravascular_frac", 0.25))
        pos_balance = max(fluid_balance, 0.0) * frac
        Hb_diluted  = (self.params["Hb_baseline"] *
                        V_plasma_mL / (V_plasma_mL + pos_balance))
        return float(np.clip(Hb_diluted, 3.0, self.params["Hb_baseline"]))

    # ------------------------------------------------------------------
    # Step
    # ------------------------------------------------------------------

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        MAP   = bus.get("MAP")
        T_c   = bus.get("T_core")
        norad = bus.get("norad_mcg_kg_min")

        # Sincronizza fluid_balance interno col bus (cattura perturbazioni esterne)
        # Questo permette ai boli (perturbazioni one-shot) di essere recepiti
        self._fluid_balance = bus.get("fluid_balance")

        # --- 1. AKI index ---
        self._update_AKI(MAP, dt)

        # --- 2. GFR effettiva ---
        GFR_frac  = self._GFR_pressure_frac(MAP)
        # Effetto noradrenalina: vasocostrizione afferente → riduce GFR
        norad_mod = 1.0 + self.params["norad_GFR_effect"] * norad
        norad_mod = float(np.clip(norad_mod, 0.3, 1.0))
        # Effetto AKI cumulativo
        AKI_mod   = 1.0 - self._AKI_index * 0.95
        sepsis_GFR_mod = bus.get("sepsis_GFR_mod") if hasattr(bus.state, "sepsis_GFR_mod") else 1.0
        endocrine_GFR_mod = bus.get("endocrine_GFR_mod") if hasattr(bus.state, "endocrine_GFR_mod") else 1.0
        hepatic_fluid_leak_mod = bus.get("hepatic_fluid_leak_mod") if hasattr(bus.state, "hepatic_fluid_leak_mod") else 1.0

        GFR_eff = self.params["GFR_baseline"] * GFR_frac * norad_mod * AKI_mod * sepsis_GFR_mod * endocrine_GFR_mod
        self._GFR_current = float(np.clip(GFR_eff, 0.0, 150.0))

        # --- 3. Diuresi ---
        urine_rate_h = self._compute_urine_rate(self._GFR_current)
        ADH = bus.get("ADH_water_retention_index") if hasattr(bus.state, "ADH_water_retention_index") else 0.0
        urine_rate_h = float(np.clip(urine_rate_h * (1.0 - 0.45 * float(np.clip(ADH, 0.0, 1.0))), 0.0, 9999.0))
        # v3.1 Step 3.8: furosemide no longer acts from the raw cumulative
        # dose counter.  Pharmacology owns concentration/effect-site signal;
        # AKI_CRRT may expose a renal-adjusted diuretic_response_index;
        # FluidBalance is the only module that writes final urine_rate/fluid
        # ledger.  Use max(), not a sum, to avoid double-counting the same
        # loop-diuretic effect through PK signal + renal audit signal.
        furo_pk_signal = float(np.clip(getattr(bus.state, "furosemide_effect_signal", 0.0), 0.0, 1.0))
        diur_idx = float(np.clip(getattr(bus.state, "diuretic_response_index", 0.0), 0.0, 1.0))
        gfr_frac_for_diuretic = float(np.clip(self._GFR_current / max(self.params["GFR_baseline"], 1e-6), 0.0, 1.2))
        renal_delivery = float(np.clip(gfr_frac_for_diuretic * (1.0 - 0.80 * self._AKI_index), 0.0, 1.2))
        local_pk_response = float(np.clip(furo_pk_signal * renal_delivery, 0.0, 1.0))
        effective_diuretic_signal = float(np.clip(max(diur_idx, local_pk_response), 0.0, 1.0))
        furosemide_urine_gain = 1.0 + 3.0 * effective_diuretic_signal
        furosemide_additional_urine_h = 0.35 * self.params["weight_kg"] * effective_diuretic_signal
        if effective_diuretic_signal > 0.0:
            urine_rate_h = float(np.clip(urine_rate_h * furosemide_urine_gain + furosemide_additional_urine_h,
                                         0.0, 8.0 * self.params["weight_kg"]))
        urine_dt     = urine_rate_h / 3600.0 * dt   # mL nel timestep

        # --- 4. Perdite insensibili ---
        insensible_h   = (self.params["insensible_mL_h"] +
                          self.params["T_insensible_gain"] *
                          max(T_c - 37.0, 0.0))
        insensible_dt  = insensible_h / 3600.0 * dt   # mL nel timestep

        # --- 5. Apporti ---
        infusion_dt = self.params["infusion_rate_mL_h"] / 3600.0 * dt
        crystalloid_type = str(getattr(bus.state, "crystalloid_type", "normal_saline") or "normal_saline").strip().lower()
        crystalloid_alias = {
            "sf": "normal_saline", "saline": "normal_saline", "soluzione_fisiologica": "normal_saline",
            "ringer": "ringer_lactate", "ringer_lattato": "ringer_lactate", "ringer_lactate": "ringer_lactate",
            "sterofundin": "sterofundin", "balanced": "sterofundin",
            "glucosata": "dextrose_5", "glucose": "dextrose_5", "d5w": "dextrose_5", "dextrose_5": "dextrose_5",
        }
        crystalloid_type = crystalloid_alias.get(crystalloid_type, crystalloid_type)
        if crystalloid_type not in {"normal_saline", "ringer_lactate", "sterofundin", "dextrose_5"}:
            crystalloid_type = "normal_saline"
        crystalloid_rate_h = float(np.clip(getattr(bus.state, "crystalloid_rate_mL_h", 0.0), 0.0, 2500.0))
        crystalloid_dt = crystalloid_rate_h / 3600.0 * dt
        balanced_fraction = 1.0 if crystalloid_type in {"ringer_lactate", "sterofundin"} else 0.0
        chloride_load_index = float(np.clip((crystalloid_rate_h / max(12.0 * self.params["weight_kg"], 1.0)) * (1.0 - balanced_fraction), 0.0, 1.0))
        glucose_gir = 0.0
        if crystalloid_type == "dextrose_5":
            # 5% dextrose = 50 mg/mL. Convert mL/h to mg/kg/min.
            glucose_gir = crystalloid_rate_h * 50.0 / max(self.params["weight_kg"], 1.0) / 60.0
            base_gir = float(getattr(bus.state, "GIR_mg_kg_min", 0.0))
            bus.set("GIR_mg_kg_min", float(np.clip(max(base_gir, glucose_gir), 0.0, 20.0)))

        # v0.31: all non-maintenance fluid inputs are routed through a
        # cumulative ledger; FluidBalance is the sole final owner of
        # fluid_balance and cumulative_fluid_input_mL.
        external_total = float(getattr(bus.state, "external_fluid_input_mL", 0.0))
        external_dt = max(external_total - self._last_external_fluid_input_mL, 0.0)
        self._last_external_fluid_input_mL = external_total
        # CRRT module suggests an effective net UF rate; FluidBalance applies it.
        crrt_uf_h = max(float(getattr(bus.state, "CRRT_UF_mL_h_effective", 0.0)), 0.0)
        crrt_uf_dt = crrt_uf_h / 3600.0 * dt

        # --- 6. Bilancio idrico cumulativo ---
        self._fluid_balance += infusion_dt + crystalloid_dt + external_dt - urine_dt - insensible_dt - crrt_uf_dt
        self._urine_cumulative += urine_dt
        bus.set("cumulative_fluid_input_mL", float(bus.get("cumulative_fluid_input_mL") + infusion_dt + crystalloid_dt + external_dt))
        bus.set("cumulative_crystalloid_input_mL", float(bus.get("cumulative_crystalloid_input_mL") + crystalloid_dt))
        bus.set("cumulative_urine_output_mL", float(bus.get("cumulative_urine_output_mL") + urine_dt))
        bus.set("cumulative_insensible_loss_mL", float(bus.get("cumulative_insensible_loss_mL") + insensible_dt))
        bus.set("cumulative_crrt_UF_mL", float(bus.get("cumulative_crrt_UF_mL") + crrt_uf_dt))

        # --- 7. Emodiluizione ---
        self._Hb_current = self._update_Hb(self._fluid_balance)

        # --- 8. Fluid responsiveness v0.11 ---
        wt = max(float(self.params.get("weight_kg", 20.0)), 1.0)
        CVP = float(bus.get("CVP")) if hasattr(bus.state, "CVP") else 5.0
        PEEP = float(bus.get("PEEP")) if hasattr(bus.state, "PEEP") else 5.0
        T_c = float(T_c)
        # Sepsi/febbre → leak; overload e PEEP alta riducono la risposta ai fluidi.
        endothelial_leak = bus.get("endothelial_leak_index") if hasattr(bus.state, "endothelial_leak_index") else 0.0
        ADH = bus.get("ADH_water_retention_index") if hasattr(bus.state, "ADH_water_retention_index") else 0.0
        capillary_leak_index = float(np.clip((0.10 * max(T_c - 37.5, 0.0) + 0.18 * max(norad, 0.0) + 0.55 * endothelial_leak + 0.08 * ADH) * hepatic_fluid_leak_mod, 0.0, 0.9))
        preload_reserve = float(np.clip(1.0 - (CVP - 4.0) / 12.0 - max(PEEP - 8.0, 0.0) / 18.0, 0.0, 1.0))
        overload_index = float(np.clip(max(self._fluid_balance, 0.0) / (25.0 * wt), 0.0, 1.0))
        fluid_responsiveness = float(np.clip(preload_reserve * (1.0 - capillary_leak_index) * (1.0 - 0.55 * overload_index), 0.0, 1.0))
        hypovolemia_index = float(np.clip((-self._fluid_balance) / max(20.0 * wt, 1.0), 0.0, 1.0))
        shock_hypovolemia = float(np.clip(getattr(bus.state, "shock_hypovolemia_index", 0.0), 0.0, 1.0))
        deficit_signal = float(np.clip(max(hypovolemia_index, shock_hypovolemia), 0.0, 1.0))
        rate_index = float(np.clip(crystalloid_rate_h / max(10.0 * wt, 1.0), 0.0, 1.5))
        crystalloid_preload_response = float(np.clip(rate_index * fluid_responsiveness * (0.30 + 0.70 * deficit_signal) * (1.0 - 0.65 * overload_index), 0.0, 1.0))
        crystalloid_MAP_support = float(np.clip(8.0 * crystalloid_preload_response, 0.0, 10.0))
        crystalloid_renal_gain = float(np.clip(crystalloid_preload_response * np.clip((MAP - 35.0) / 35.0, 0.0, 1.0), 0.0, 1.0))
        if crystalloid_renal_gain > 0.0 and effective_diuretic_signal <= 0.05:
            urine_rate_h = float(np.clip(urine_rate_h * (1.0 + 0.30 * crystalloid_renal_gain), 0.0, 6.0 * wt))

        # --- 9. Effetti emodinamici del fluid overload ---
        # Solo la quota intravascolare effettiva contribuisce alla CVP; la quota
        # cala se leak capillare è alto.
        intravascular_effective = max(self._fluid_balance, 0.0) * (1.0 - capillary_leak_index)
        CVP_corr = float(np.clip(
            intravascular_effective * self.params["fluid_CVP_gain"],
            -5.0, 10.0
        ))

        expected_balance = float(bus.get("cumulative_fluid_input_mL") - bus.get("cumulative_urine_output_mL") - bus.get("cumulative_crrt_UF_mL") - bus.get("cumulative_insensible_loss_mL"))
        fluid_balance_error = float(self._fluid_balance - expected_balance)
        diuretic_hypovolemia_risk = float(np.clip((-self._fluid_balance - 0.08 * wt * 1000.0) / max(0.12 * wt * 1000.0, 1.0), 0.0, 1.0))

        bus.update({
            "GFR":                  float(self._GFR_current),
            "urine_rate_mL_h":      float(urine_rate_h),
            "fluid_balance":        float(self._fluid_balance),
            "AKI_index":            float(self._AKI_index),
            "fluid_CVP_correction": float(CVP_corr),
            "fluid_responsiveness":  float(fluid_responsiveness),
            "preload_reserve":       float(preload_reserve),
            "capillary_leak_index":  float(capillary_leak_index),
            "furosemide_effective_diuretic_signal": float(effective_diuretic_signal),
            "furosemide_urine_gain": float(furosemide_urine_gain),
            "furosemide_additional_urine_mL_h": float(furosemide_additional_urine_h),
            "diuretic_hypovolemia_risk": float(diuretic_hypovolemia_risk),
            "fluid_balance_error_mL": float(fluid_balance_error),
            "crystalloid_type": crystalloid_type,
            "crystalloid_active": bool(crystalloid_rate_h > 0.0),
            "crystalloid_effective_mL_h": float(crystalloid_rate_h),
            "crystalloid_balanced_fraction": float(balanced_fraction),
            "crystalloid_chloride_load_index": float(chloride_load_index),
            "crystalloid_glucose_GIR_mg_kg_min": float(glucose_gir),
            "crystalloid_preload_response": float(crystalloid_preload_response),
            "crystalloid_MAP_support_mmHg": float(crystalloid_MAP_support),
            "crystalloid_renal_perfusion_gain": float(crystalloid_renal_gain),
        })

"""
ScenarioLoader
==============
Carica profili paziente da file YAML e costruisce:
  - BusState con parametri baseline del paziente
  - Lista di Perturbation ordinate per tempo

YAML schema: vedi /scenarios/*.yaml
"""

from __future__ import annotations
import yaml
import os
from typing import List, Dict, Any, Optional

from .bus import BusState, PhysiologicalBus
from .engine import Perturbation
from .profiles import get_profile
from .profile_scaling import bsa_m2
from .cardiovascular_scaling import build_cardiovascular_scaling
from .events import build_event_perturbations
from .airway_events import build_airway_event_perturbations
from .cardiac_arrest_events import build_cardiac_event_perturbations


# ---------------------------------------------------------------------------
# Formule antropometriche pediatriche
# ---------------------------------------------------------------------------

def ideal_weight_kg(age_y: float, sex: str = "M") -> float:
    """Peso ideale pediatrico (formula approssimata >1 anno)."""
    if age_y < 1:
        return 4.5 + age_y * 6
    return 8 + 2 * age_y  # Broselow-like


def FRC_ml(weight_kg: float) -> float:
    """FRC stimata = ~30 mL/kg."""
    return 30.0 * weight_kg


def Vt_target_ml(weight_kg: float, ml_per_kg: float = 6.0) -> float:
    """Volume tidal target protettivo."""
    return ml_per_kg * weight_kg


def CO_baseline(weight_kg: float) -> float:
    """Gittata cardiaca baseline [L/min]: ~200 mL/kg/min."""
    return weight_kg * 0.200


def HR_baseline(age_y: float) -> float:
    """FC baseline [bpm] per età."""
    if age_y < 1:    return 140.0
    elif age_y < 3:  return 125.0
    elif age_y < 6:  return 110.0
    elif age_y < 12: return 95.0
    else:            return 80.0


def MAP_baseline(age_y: float) -> float:
    """MAP baseline [mmHg]."""
    return 50.0 + 1.5 * age_y


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

class ScenarioLoader:
    """
    Carica uno scenario da file YAML o dizionario Python.
    
    Usage
    -----
    >>> loader = ScenarioLoader.from_yaml("scenarios/ards_mild.yaml")
    >>> bus = loader.build_bus()
    >>> perturbations = loader.build_perturbations()
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @classmethod
    def from_yaml(cls, path: str) -> "ScenarioLoader":
        with open(path, "r") as f:
            config = yaml.safe_load(f)
        return cls(config)

    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> "ScenarioLoader":
        return cls(config)

    # --- Costruzione BusState ---

    def build_bus(self) -> PhysiologicalBus:
        """
        Costruisce un PhysiologicalBus inizializzato con i parametri
        del paziente dello scenario.
        """
        state = BusState()
        patient = self.config.get("patient", {})

        # Parametri antropometrici e profilo pediatrico v0.11
        # Se lo scenario specifica patient.profile lo usiamo; altrimenti scegliamo
        # il profilo più vicino al peso o child_20kg. Gli override YAML restano
        # sempre prioritari sotto.
        requested_profile = patient.get("profile")
        age_hint = patient.get("age_y", None)
        weight_hint = patient.get("weight_kg", None)
        profile_name, prof = get_profile(requested_profile, weight_hint)

        age_y  = float(patient.get("age_y", prof.get("age_y", 5)))
        weight = float(patient.get("weight_kg", prof.get("weight_kg", ideal_weight_kg(age_y))))
        sex    = patient.get("sex", "M")

        # Baseline fisiologiche da profilo pediatrico
        state.patient_profile = profile_name
        state.age_group = str(prof.get("age_group", "child"))
        state.age_y = age_y
        state.weight_kg = weight
        state.BSA_m2 = bsa_m2(weight, age_y)
        state.blood_volume_mL = float(prof.get("blood_volume_ml_kg", 75.0)) * weight
        state.FRC    = float(prof.get("FRC_ml_kg", 30.0)) * weight
        state.EELV   = state.FRC
        state.Vt     = float(prof.get("Vt_ml_kg", 6.0)) * weight
        state.Vt_set_mL = state.Vt
        state.V_lung = 0.0
        state.HR     = float(prof.get("HR", HR_baseline(age_y)))
        state.RR     = float(prof.get("RR", 25.0))
        state.CO     = float(prof.get("CO_L_min", CO_baseline(weight)))
        state.SV     = (state.CO / state.HR) * 1000  # mL
        state.MAP    = float(prof.get("MAP", MAP_baseline(age_y)))
        state.Hb     = float(prof.get("Hb", state.Hb))
        state.VO2    = weight * float(prof.get("VO2_ml_kg_min", 6.0))
        state.C_rs   = float(prof.get("C_rs_ml_cmH2O_kg", 0.8)) * weight
        state.GFR    = float(prof.get("GFR_ml_min_1_73m2", state.GFR)) * state.BSA_m2 / 1.73
        state.urine_rate_mL_h = max(1.0 * weight, 0.5)

        # Override respiratorio da scenario
        resp = self.config.get("respiratory", {})
        for key in ["Paw", "Palv", "PEEP", "FiO2", "RR", "Vt", "R_rs",
                    "C_rs", "E_rs", "EELV", "FRC", "SaO2", "PaO2", "PaCO2"]:
            if key in resp:
                setattr(state, key, float(resp[key]))

        # Parametri ventilatore nel Bus. Importante: evita che i default del
        # BusState (es. Pinsp=20) sovrascrivano lo scenario al primo step del
        # VentilatorModule.
        vent = self.config.get("ventilator", {})
        if "mode" in vent or "mode" in resp:
            state.vent_mode = str(vent.get("mode", resp.get("mode", state.vent_mode)))
        if "Pinsp" in vent:
            state.Pinsp_cmH2O = float(vent["Pinsp"])
        elif "Paw" in resp:
            # Nel blocco respiratory, Paw è interpretata come pressione picco
            # assoluta; il ventilatore PCV usa invece Pinsp sopra PEEP.
            state.Pinsp_cmH2O = float(max(float(resp["Paw"]) - float(resp.get("PEEP", state.PEEP)), 0.0))
        if "PS" in vent:
            state.PS_cmH2O = float(vent["PS"])
        if "Vt_set_mL" in vent:
            state.Vt_set_mL = float(vent["Vt_set_mL"])
        elif "Vt" in resp:
            state.Vt_set_mL = float(resp["Vt"])
        if "IE_ratio" in vent:
            state.IE_ratio = float(vent["IE_ratio"])
        if "T_rise_s" in vent:
            state.T_rise_s = float(vent["T_rise_s"])
        if "trigger_thresh" in vent:
            state.trigger_thresh = float(vent["trigger_thresh"])
        if "cycling_frac" in vent:
            state.cycling_frac = float(vent["cycling_frac"])

        # Override cardiovascolare da scenario
        cv = self.config.get("cardiovascular", {})
        for key in ["HR", "CO", "MAP", "CVP", "PAWP", "PAP_mean", "SVR", "PVR", "Hb", "SvO2"]:
            if key in cv:
                setattr(state, key, float(cv[key]))

        # Cardiovascular profile scaling v1.05. This keeps the child_20kg anchor
        # but prevents 20 kg ventricular volumes/elastance from leaking into
        # neonatal, infant, toddler, or adolescent scenarios. Explicit scenario
        # overrides remain authoritative.
        cv_scaling = build_cardiovascular_scaling(
            weight_kg=weight,
            age_y=age_y,
            age_group=state.age_group,
            patient_profile=profile_name,
            HR_ref=(state.HR if "HR" not in cv else None),
            MAP_ref=(state.MAP if "MAP" not in cv else None),
            CO_ref_L_min=None,
            CVP_ref=(state.CVP if "CVP" not in cv else None),
            PAWP_ref=(state.PAWP if "PAWP" not in cv else None),
            PAP_ref=(state.PAP_mean if "PAP_mean" not in cv else None),
        )
        if "CO" not in cv:
            state.CO = float(cv_scaling["CO_ref_L_min"])
        state.SV = float(state.CO / max(state.HR, 1.0) * 1000.0)
        state.EDV_lv = float(cv_scaling["EDV0_lv"])
        state.ESV_lv = float(max(state.EDV_lv - state.SV, 0.1))
        state.EF_lv = float(state.SV / max(state.EDV_lv, 1e-6))
        state.cv_scaling_weight_kg = float(cv_scaling["weight_kg"])
        state.cv_scaling_profile = str(cv_scaling["patient_profile"])
        state.cv_scaling_revision = str(cv_scaling["cv_scaling_revision"])
        state.cv_EDV0_lv_ref = float(cv_scaling["EDV0_lv"])
        state.cv_Emax_lv_ref = float(cv_scaling["Emax_lv"])
        state.cv_R_systemic_ref = float(cv_scaling["R_systemic"])

        # Modifiers rapidi (es. preload_mod)
        if "preload_mod" in cv:
            state.EDV_lv *= float(cv["preload_mod"])

        # Override metabolismo
        meta = self.config.get("metabolism", {})
        for key in ["T_core", "VO2", "lactate"]:
            if key in meta:
                setattr(state, key, float(meta[key]))

        # Override acid-base / electrolytes v0.17
        acidbase = self.config.get("acidbase", {})
        for key in ["Na_mmol_L", "K_mmol_L", "Cl_mmol_L", "HCO3_mmol_L",
                    "urea_mmol_L", "normal_saline_mL", "balanced_crystalloid_mL",
                    "bicarbonate_mmol", "hypertonic_saline_3pct_mL",
                    "potassium_mmol", "diuretic_effect"]:
            if key in acidbase:
                setattr(state, key, float(acidbase[key]))

        # Override AKI / CRRT-lite v0.18
        renal = self.config.get("renal", {})
        for key in ["creatinine_mg_dL", "creatinine_baseline_mg_dL", "furosemide_mg_kg",
                    "CRRT_effluent_mL_kg_h", "CRRT_net_UF_mL_h",
                    "CRRT_dialysate_K_mmol_L", "CRRT_bicarbonate_mmol_L"]:
            if key in renal:
                setattr(state, key, float(renal[key]))
        if "CRRT_active" in renal:
            state.CRRT_active = bool(renal["CRRT_active"])
        if "CRRT_anticoagulation" in renal:
            state.CRRT_anticoagulation = str(renal["CRRT_anticoagulation"])

        # Override airway obstruction / bronchiolite / asthma
        airway = self.config.get("airway", {})
        for key in ["bronchospasm_index", "mucus_load", "small_airway_obstruction",
                    "salbutamol_mcg_kg_min", "ipratropium_mcg_kg_h", "magnesium_mg_kg_h",
                    "nebulized_epinephrine_mcg_kg_min",
                    "adrenaline_mcg_kg_min", "dopamine_mcg_kg_min", "vasopressin_mU_kg_min"]:
            if key in airway:
                setattr(state, key, float(airway[key]))

        # Airway interface base v1.23/v1.23.1: separates intubated/mechanically
        # connected patients from spontaneous breathing and adds simple oxygen/HFNC
        # delivery fields. Exact oxygen entrainment physics is intentionally not modeled.
        airway_interface_cfg = self.config.get("airway_interface", {}) or {}
        if airway_interface_cfg:
            interface = str(airway_interface_cfg.get("interface", airway_interface_cfg.get("airway_interface", state.airway_interface))).upper()
            aliases = {"NONE": "UNASSISTED", "ROOM_AIR": "UNASSISTED", "LOW_FLOW": "LOW_FLOW_OXYGEN", "NASAL_CANNULA": "LOW_FLOW_OXYGEN", "HIGH_FLOW": "HFNC", "NIV": "NIV_BIPAP", "BIPAP": "NIV_BIPAP", "NONINVASIVE_BIPAP": "NIV_BIPAP", "NONINVASIVE_CPAP": "NIV_CPAP", "MASK_CPAP": "NIV_CPAP"}
            interface = aliases.get(interface, interface)
            state.airway_interface = interface
            state.intubated = bool(airway_interface_cfg.get("intubated", interface in ("ETT", "TRACHEOSTOMY")))
            state.ventilator_connected = bool(airway_interface_cfg.get("ventilator_connected", interface in ("ETT", "TRACHEOSTOMY", "NIV_CPAP", "NIV_BIPAP")))
            state.spontaneous_airway_mode = bool(airway_interface_cfg.get("spontaneous_airway_mode", interface in ("UNASSISTED", "NONE", "LOW_FLOW_OXYGEN", "SIMPLE_MASK", "HFNC", "NIV_CPAP", "NIV_BIPAP")))
            state.airway_pressure_delivery_enabled = bool(airway_interface_cfg.get("airway_pressure_delivery_enabled", state.ventilator_connected and interface not in ("UNASSISTED", "NONE", "LOW_FLOW_OXYGEN", "SIMPLE_MASK", "HFNC")))
            state.ambient_airway_pressure_cmH2O = float(airway_interface_cfg.get("ambient_airway_pressure_cmH2O", 0.0))
            state.oxygen_interface = str(airway_interface_cfg.get("oxygen_interface", interface if interface in ("LOW_FLOW_OXYGEN", "SIMPLE_MASK", "HFNC") else ("ROOM_AIR" if interface in ("UNASSISTED", "NONE") else "VENTILATOR"))).upper()
            state.oxygen_flow_L_min = float(airway_interface_cfg.get("oxygen_flow_L_min", state.oxygen_flow_L_min))
            state.oxygen_FiO2_set = float(airway_interface_cfg.get("oxygen_FiO2_set", airway_interface_cfg.get("FiO2_set", state.FiO2)))
            state.HFNC_flow_L_min = float(airway_interface_cfg.get("HFNC_flow_L_min", state.HFNC_flow_L_min))
            state.HFNC_FiO2_set = float(airway_interface_cfg.get("HFNC_FiO2_set", state.oxygen_FiO2_set))
            state.mouth_leak_fraction = float(airway_interface_cfg.get("mouth_leak_fraction", state.mouth_leak_fraction))
            state.NIV_mode = str(airway_interface_cfg.get("NIV_mode", "CPAP" if interface == "NIV_CPAP" else ("BIPAP" if interface == "NIV_BIPAP" else state.NIV_mode))).upper()
            state.NIV_CPAP_cmH2O = float(airway_interface_cfg.get("NIV_CPAP_cmH2O", airway_interface_cfg.get("CPAP_cmH2O", state.NIV_CPAP_cmH2O)))
            state.NIV_IPAP_cmH2O = float(airway_interface_cfg.get("NIV_IPAP_cmH2O", airway_interface_cfg.get("IPAP_cmH2O", state.NIV_IPAP_cmH2O)))
            state.NIV_EPAP_cmH2O = float(airway_interface_cfg.get("NIV_EPAP_cmH2O", airway_interface_cfg.get("EPAP_cmH2O", state.NIV_EPAP_cmH2O)))
            state.NIV_pressure_support_cmH2O = float(airway_interface_cfg.get("NIV_pressure_support_cmH2O", max(state.NIV_IPAP_cmH2O - state.NIV_EPAP_cmH2O, 0.0)))
            state.NIV_FiO2_set = float(airway_interface_cfg.get("NIV_FiO2_set", airway_interface_cfg.get("FiO2_set", state.oxygen_FiO2_set)))
            state.NIV_leak_fraction = float(airway_interface_cfg.get("NIV_leak_fraction", airway_interface_cfg.get("mask_leak_fraction", state.NIV_leak_fraction)))
            state.mask_leak_fraction = float(airway_interface_cfg.get("mask_leak_fraction", state.NIV_leak_fraction))
            state.tube_internal_diameter_mm = float(airway_interface_cfg.get("tube_internal_diameter_mm", airway_interface_cfg.get("tube_ID_mm", state.tube_internal_diameter_mm)))
            state.tube_length_cm = float(airway_interface_cfg.get("tube_length_cm", state.tube_length_cm))
            state.tube_obstruction_score = float(airway_interface_cfg.get("tube_obstruction_score", state.tube_obstruction_score))
            state.cuff_leak_fraction = float(airway_interface_cfg.get("cuff_leak_fraction", state.cuff_leak_fraction))
            state.cuff_pressure_cmH2O = float(airway_interface_cfg.get("cuff_pressure_cmH2O", state.cuff_pressure_cmH2O))
            state.ETT_position_score = float(airway_interface_cfg.get("ETT_position_score", state.ETT_position_score))
            if interface in ("UNASSISTED", "NONE", "LOW_FLOW_OXYGEN", "SIMPLE_MASK", "HFNC"):
                state.vent_mode = "NONE"
                state.PEEP = 0.0
                state.Paw = state.ambient_airway_pressure_cmH2O
                state.Paw_current = state.ambient_airway_pressure_cmH2O
            elif interface == "NIV_CPAP":
                state.vent_mode = str(self.config.get("ventilator", {}).get("mode", "CPAP")).upper()
                state.PEEP = state.NIV_CPAP_cmH2O
                state.Paw = state.PEEP
                state.Paw_current = state.PEEP
            elif interface == "NIV_BIPAP":
                state.vent_mode = str(self.config.get("ventilator", {}).get("mode", "PSV")).upper()
                state.PEEP = state.NIV_EPAP_cmH2O
                state.PS_cmH2O = state.NIV_pressure_support_cmH2O
                state.Paw = state.NIV_IPAP_cmH2O
                state.Paw_current = state.NIV_EPAP_cmH2O
            state.airway_interface_revision = 1233 if interface in ("ETT", "TRACHEOSTOMY") else (1232 if interface in ("NIV_CPAP", "NIV_BIPAP") else 1231)
            state.oxygen_delivery_revision = 1233 if interface in ("ETT", "TRACHEOSTOMY") else (1232 if interface in ("NIV_CPAP", "NIV_BIPAP") else 1231)
            state.airway_interface_note = str(airway_interface_cfg.get("note", "v1.23.3_artificial_airway" if interface in ("ETT", "TRACHEOSTOMY") else ("v1.23.2_niv_interface" if interface in ("NIV_CPAP", "NIV_BIPAP") else "v1.23.1_oxygen_delivery_interface")))

        # Override infection / antimicrobial v0.26 and sepsis phenotype
        infection = self.config.get("infection", {})
        if infection:
            state.microbial_burden = float(infection.get("microbial_burden", infection.get("infection_load", state.microbial_burden)))
            state.infection_load = float(infection.get("infection_load", state.microbial_burden))
            state.pathogen_virulence = float(infection.get("pathogen_virulence", state.pathogen_virulence))
            state.pathogen_resistance_index = float(infection.get("pathogen_resistance_index", state.pathogen_resistance_index))
            state.antibiotic_coverage = float(infection.get("antibiotic_coverage", state.antibiotic_coverage))
            state.source_control = float(infection.get("source_control", state.source_control))
            state.antibiotic_started = bool(infection.get("antibiotic_started", state.antibiotic_started))
            state.culture_drawn = bool(infection.get("culture_drawn", state.culture_drawn))
            state.infection_focus = str(infection.get("infection_focus", state.infection_focus))
        # Override sepsi avanzata / shock phenotype
        sepsis = self.config.get("sepsis", {})
        if sepsis:
            state.infection_load = float(sepsis.get("infection_load", state.infection_load))
            state.microbial_burden = max(float(state.microbial_burden), float(state.infection_load))
            state.source_control = float(sepsis.get("source_control", state.source_control))
            state.antibiotic_effect = float(sepsis.get("antibiotic_effect", state.antibiotic_effect))
            state.sepsis_phenotype_code = str(sepsis.get("phenotype", state.sepsis_phenotype_code))

        # Override shock engine v3.1 step4.39 / scenario engine v2 v3.1 step4.44
        shock = self.config.get("shock", {})
        if shock:
            aliases = {"type": "shock_type", "severity": "shock_severity", "stage": "shock_stage",
                       "vasoplegia_index": "shock_vasoplegia_index",
                       "hypovolemia_index": "shock_hypovolemia_index",
                       "low_output_index": "shock_low_output_index",
                       "obstruction_index": "shock_obstruction_index",
                       "tamponade_index": "shock_obstruction_index"}
            for src, dst in aliases.items():
                if src in shock:
                    if dst in ("shock_type", "shock_stage"):
                        setattr(state, dst, str(shock[src]).lower())
                    else:
                        setattr(state, dst, float(shock[src]))
            for key in ["shock_SVR_mod", "shock_preload_mod", "shock_contractility_mod",
                        "shock_HR_add", "shock_lactate_prod_mod", "shock_lactate_clearance_mod",
                        "shock_sympathetic_tone", "shock_decompensation_index"]:
                short = key.replace("shock_", "")
                if key in shock:
                    setattr(state, key, float(shock[key]))
                elif short in shock:
                    setattr(state, key, float(shock[short]))

        # v3.2 public-polish: infer educational shock metadata from common
        # scenario-level disease blocks when explicit `shock:` metadata is absent.
        # This keeps clinical teaching labels aligned with the physiology without
        # requiring all legacy YAML scenarios to be hand-edited at once.
        if str(getattr(state, "shock_type", "none")).lower() in ("", "none", "normal"):
            scenario_name = str(self.config.get("name", "")).lower()
            diagnosis = str(patient.get("diagnosis", "")).lower()
            description = str(self.config.get("description", "")).lower()
            lactate = float(getattr(state, "lactate", 1.0))
            map_value = float(getattr(state, "MAP", MAP_baseline(age_y)))
            if sepsis or "sepsis" in scenario_name or "septic" in scenario_name or "septic" in diagnosis or "sepsi" in description:
                state.shock_type = "distributive"
                state.shock_severity = float(max(getattr(state, "shock_severity", 0.0), min(max(state.infection_load, 0.45), 0.95)))
            elif "pneumothorax" in scenario_name or "tamponade" in scenario_name or "obstructive" in diagnosis:
                state.shock_type = "obstructive"
                state.shock_severity = float(max(getattr(state, "shock_severity", 0.0), 0.20))
            elif "excessive_peep" in scenario_name or "high_peep" in scenario_name:
                state.shock_type = "obstructive"
                state.shock_severity = float(max(getattr(state, "shock_severity", 0.0), 0.25))
            elif "hypovole" in scenario_name or "hemorrhag" in scenario_name or "haemorrhag" in scenario_name:
                state.shock_type = "hypovolemic"
                state.shock_severity = float(max(getattr(state, "shock_severity", 0.0), 0.60))
            elif map_value < 50.0 and lactate >= 2.5:
                state.shock_type = "mixed"
                state.shock_severity = float(max(getattr(state, "shock_severity", 0.0), 0.45))

        # Override neuro / ICP v3.1 step4.44 scenario hooks
        neuro = self.config.get("neuro", {})
        for key in ["ICP_mmHg", "CPP_mmHg", "cerebral_edema_index", "cerebral_perfusion_index",
                    "osmo_active", "csf_drain_mL_h"]:
            if key in neuro:
                setattr(state, key, float(neuro[key]) if not isinstance(getattr(state, key, 0.0), bool) else bool(neuro[key]))

        # Override nutrition/glucose/catabolism baseline v0.23
        nutrition = self.config.get("nutrition", {})
        for key in ["glucose_mmol_L", "GIR_mg_kg_min", "insulin_UI_h",
                    "enteral_feed_mL_h", "enteral_kcal_mL", "parenteral_kcal_kg_day",
                    "protein_g_kg_day", "lipid_g_kg_day", "malnutrition_index",
                    "phosphate_mmol_L", "magnesium_mmol_L", "phosphate_supplement_mmol",
                    "magnesium_supplement_mmol", "triglycerides_mmol_L"]:
            if key in nutrition:
                setattr(state, key, float(nutrition[key]))

        # Override hepatic metabolism v0.22
        hepatic = self.config.get("hepatic", {})
        for key in ["albumin_g_dL", "bilirubin_total_mg_dL", "bilirubin_direct_mg_dL",
                    "bilirubin_indirect_mg_dL", "AST_U_L", "ALT_U_L",
                    "ammonia_umol_L", "hepatic_perfusion_index"]:
            if key in hepatic:
                setattr(state, key, float(hepatic[key]))


        # Override neurofunctional v0.25
        neurofunctional = self.config.get("neurofunctional", {})
        for key in ["GCS_proxy", "encephalopathy_index", "seizure_risk_index",
                    "delirium_state_index", "withdrawal_state_index",
                    "seizure_treatment_effect"]:
            if key in neurofunctional:
                setattr(state, key, float(neurofunctional[key]))

        # Override farmaci (completo — tutti i farmaci supportati)
        drugs = self.config.get("drugs", {})
        for key in ["norad_mcg_kg_min", "ketamine_mg_kg_h", "milrinone_mcg_kg_min",
                    "midazolam_mcg_kg_h", "propofol_mg_kg_h", "rocuronium_mg_kg_h",
                    "hydrocortisone_mg_kg_h", "dexamethasone_mcg_kg_h", "ino_ppm",
                    "GIR_mg_kg_min", "insulin_UI_h",
                    "fentanyl_mcg_kg_h", "remifentanil_mcg_kg_min",
                    "morphine_mcg_kg_h", "dexmedetomidine_mcg_kg_h",
                    "clonidine_mcg_kg_h", "vancomycin_mg_kg_h", "furosemide_mg_kg_h",
                    "piperacillin_mg_kg_h", "piperacillin_MIC_mg_L",
                    "salbutamol_mcg_kg_min", "ipratropium_mcg_kg_h", "magnesium_mg_kg_h",
                    "nebulized_epinephrine_mcg_kg_min",
                    "adrenaline_mcg_kg_min", "dopamine_mcg_kg_min", "vasopressin_mU_kg_min"]:
            if key in drugs:
                val = drugs[key]
                setattr(state, key, bool(val) if isinstance(val, str) and val.lower() in ('true','false')
                        else float(val))

        # Override endocrine / stress axis v0.19
        endocrine = self.config.get("endocrine", {})
        for key in ["cortisol_activity", "catecholamine_tone",
                    "adrenal_insufficiency_index", "insulin_resistance_index",
                    "thyroid_suppression_index", "ADH_water_retention_index"]:
            if key in endocrine:
                setattr(state, key, float(endocrine[key]))

        # Override hematology / oxygen transport v0.21
        hematology = self.config.get("hematology", {})
        for key in ["Hct_percent", "RBC_million_uL", "WBC_count", "neutrophil_count",
                    "lymphocyte_count", "reticulocyte_percent", "bleeding_rate_mL_h",
                    "hemolysis_index", "platelet_function_index", "methemoglobin_percent",
                    "transfusion_threshold_Hb"]:
            if key in hematology:
                setattr(state, key, float(hematology[key]))
        if "transfusion_strategy" in hematology:
            state.transfusion_strategy = str(hematology["transfusion_strategy"])

        # Ricalcolo derivati di consistenza
        # DO2 [mL/min] = CO [L/min] × CaO2 [mL/dL] × 10 [dL/L]
        CaO2 = 1.34 * state.Hb * state.SaO2 + 0.003 * state.PaO2  # mL/dL
        state.DO2  = state.CO * CaO2 * 10.0   # mL/min
        state.ERO2 = state.VO2 / (state.DO2 + 1e-6)
        state.SvO2 = max(1.0 - state.ERO2, 0.0)
        state.PvO2 = 23.0 + 30.0 * state.SvO2

        return PhysiologicalBus(initial_state=state)

    # --- Costruzione perturbazioni ---

    def build_perturbations(self) -> List[Perturbation]:
        """
        Costruisce la lista di Perturbation dalla timeline dello scenario.
        """
        perturbs: List[Perturbation] = []
        timeline = self.config.get("perturbations", [])


        _action_map = {
            # Ventilatore
            "set_PEEP":        "PEEP",
            "set_FiO2":        "FiO2",
            "set_RR":          "RR",
            "set_Paw":         "Paw",
            # Cardiovascolare
            "set_HR":          "HR",
            "set_MAP":         "MAP",
            "set_SaO2":        "SaO2",
            "set_PaO2":        "PaO2",
            "set_PaCO2":       "PaCO2",
            "set_EtCO2":       "EtCO2",
            "set_pH_a":        "pH_a",
            "set_lactate":     "lactate",
            # Farmaci base
            "set_norad":       "norad_mcg_kg_min",
            "set_adrenaline":  "adrenaline_mcg_kg_min",
            "set_dopamine":    "dopamine_mcg_kg_min",
            "set_vasopressin": "vasopressin_mU_kg_min",
            "set_milrinone":   "milrinone_mcg_kg_min",
            "set_ketamine":    "ketamine_mg_kg_h",
            "set_midazolam":   "midazolam_mcg_kg_h",
            "set_propofol":    "propofol_mg_kg_h",
            "set_rocuronium":  "rocuronium_mg_kg_h",
            "set_fentanyl":    "fentanyl_mcg_kg_h",
            "set_remifentanil":"remifentanil_mcg_kg_min",
            "set_morphine":    "morphine_mcg_kg_h",
            "set_dexmedetomidine": "dexmedetomidine_mcg_kg_h",
            "set_clonidine":   "clonidine_mcg_kg_h",
            "set_vancomycin": "vancomycin_mg_kg_h",
            "set_piperacillin": "piperacillin_mg_kg_h",
            "set_piptazo": "piperacillin_mg_kg_h",
            "set_furosemide_infusion": "furosemide_mg_kg_h",
            "set_furosemide_rate": "furosemide_mg_kg_h",
            "set_salbutamol":  "salbutamol_mcg_kg_min",
            "set_ipratropium": "ipratropium_mcg_kg_h",
            "set_magnesium":   "magnesium_mg_kg_h",
            "set_nebulized_epinephrine": "nebulized_epinephrine_mcg_kg_min",
            "set_bronchospasm": "bronchospasm_index",
            "set_mucus_load":   "mucus_load",
            "set_small_airway_obstruction": "small_airway_obstruction",
            # Steroidi
            "set_hydrocortisone":  "hydrocortisone_mg_kg_h",
            "set_dexamethasone":   "dexamethasone_mcg_kg_h",
            # iNO
            "set_ino_ppm":     "ino_ppm",
            # Metabolismo/temperatura
            "set_T_core":      "T_core",
            "set_infection_load": "infection_load",
            "set_source_control": "source_control",
            "set_antibiotic_effect": "antibiotic_effect",
            "set_antibiotic_started": "antibiotic_started",
            "set_antibiotic_coverage": "antibiotic_coverage",
            "set_pathogen_resistance": "pathogen_resistance_index",
            "set_pathogen_virulence": "pathogen_virulence",
            "set_culture_drawn": "culture_drawn",
            "set_paracetamol": "paracetamol_active",
            "set_cooling": "cooling_device_active",
            "set_warming": "external_warming_active",
            "set_target_temperature": "target_temperature_C",
            "set_setpoint_T": "setpoint_T",
            # Acid-base / electrolytes v0.17
            "set_normal_saline": "normal_saline_mL",
            "set_balanced_crystalloid": "balanced_crystalloid_mL",
            "set_bicarbonate": "bicarbonate_mmol",
            "set_hypertonic_saline_3pct": "hypertonic_saline_3pct_mL",
            "set_potassium": "potassium_mmol",
            "calcium_given": "calcium_given",
            "set_calcium_given": "calcium_given",
            "set_Na": "Na_mmol_L",
            "set_K": "K_mmol_L",
            "set_Cl": "Cl_mmol_L",
            "set_HCO3": "HCO3_mmol_L",
            "set_diuretic_effect": "diuretic_effect",
            # Endocrine / stress axis v0.19
            "set_cortisol_activity": "cortisol_activity",
            "set_catecholamine_tone": "catecholamine_tone",
            "set_adrenal_insufficiency": "adrenal_insufficiency_index",
            "set_insulin_resistance": "insulin_resistance_index",
            "set_thyroid_suppression": "thyroid_suppression_index",
            "set_ADH_retention": "ADH_water_retention_index",
            # Hematology / oxygen transport v0.21
            "set_Hb": "Hb",
            "set_WBC": "WBC_count",
            "set_neutrophils": "neutrophil_count",
            "set_bleeding_rate": "bleeding_rate_mL_h",
            "set_hemolysis": "hemolysis_index",
            "set_platelet_function": "platelet_function_index",
            "set_methemoglobin": "methemoglobin_percent",
            "set_transfusion_threshold_Hb": "transfusion_threshold_Hb",
            "set_albumin": "albumin_g_dL",
            "set_bilirubin_total": "bilirubin_total_mg_dL",
            "set_bilirubin_direct": "bilirubin_direct_mg_dL",
            "set_AST": "AST_U_L",
            "set_ALT": "ALT_U_L",
            "set_ammonia": "ammonia_umol_L",
            # AKI / CRRT-lite v0.18
            "set_furosemide": "furosemide_mg_kg",
            "set_CRRT_active": "CRRT_active",
            "set_CRRT_effluent": "CRRT_effluent_mL_kg_h",
            "set_CRRT_net_UF": "CRRT_net_UF_mL_h",
            "set_CRRT_dialysate_K": "CRRT_dialysate_K_mmol_L",
            "set_CRRT_bicarbonate": "CRRT_bicarbonate_mmol_L",
            # Nutrizione / catabolismo v0.23
            "set_GIR":         "GIR_mg_kg_min",
            "set_insulin":     "insulin_UI_h",
            "set_enteral_feed": "enteral_feed_mL_h",
            "set_enteral_kcal_mL": "enteral_kcal_mL",
            "set_parenteral_kcal": "parenteral_kcal_kg_day",
            "set_protein":     "protein_g_kg_day",
            "set_lipid":       "lipid_g_kg_day",
            "set_malnutrition": "malnutrition_index",
            "set_phosphate_supplement": "phosphate_supplement_mmol",
            "set_magnesium_supplement": "magnesium_supplement_mmol",
            "set_phosphate": "phosphate_mmol_L",
            "set_Mg": "magnesium_mmol_L",
            "set_triglycerides": "triglycerides_mmol_L",
            # Renale/fluidi
            "set_infusion":    "infusion_rate_mL_h",
            # Neurologia
            "osmo_therapy":    "osmo_active",
            "csf_drain":       "csf_drain_mL_h",
            "set_GCS":         "GCS_proxy",
            "set_seizure_treatment": "seizure_treatment_effect",
            "set_withdrawal_state": "withdrawal_state_index",
            "set_delirium_state": "delirium_state_index",
            # Ventilatore — modalità e parametri
            "set_mode":        "vent_mode",
            "set_Vt":          "Vt_set_mL",
            "set_Pinsp":       "Pinsp_cmH2O",
            "set_PS":          "PS_cmH2O",
            "set_IE":          "IE_ratio",
            "set_trigger":     "trigger_thresh",
            "set_cycling":     "cycling_frac",
            "set_airway_interface": "airway_interface",
            "set_intubated": "intubated",
            "set_ventilator_connected": "ventilator_connected",
            "set_airway_pressure_delivery": "airway_pressure_delivery_enabled",
            "set_oxygen_interface": "oxygen_interface",
            "set_oxygen_flow": "oxygen_flow_L_min",
            "set_oxygen_FiO2": "oxygen_FiO2_set",
            "set_HFNC_flow": "HFNC_flow_L_min",
            "set_HFNC_FiO2": "HFNC_FiO2_set",
            "set_mouth_leak": "mouth_leak_fraction",
            "set_NIV_mode": "NIV_mode",
            "set_NIV_CPAP": "NIV_CPAP_cmH2O",
            "set_NIV_IPAP": "NIV_IPAP_cmH2O",
            "set_NIV_EPAP": "NIV_EPAP_cmH2O",
            "set_NIV_PS": "NIV_pressure_support_cmH2O",
            "set_NIV_FiO2": "NIV_FiO2_set",
            "set_NIV_leak": "NIV_leak_fraction",
            "set_mask_leak": "mask_leak_fraction",
            "set_tube_obstruction": "tube_obstruction_score",
            "set_cuff_leak": "cuff_leak_fraction",
            "set_tube_ID": "tube_internal_diameter_mm",
            "set_tube_length": "tube_length_cm",
            "set_bag_mask_quality": "bag_mask_quality",
            "set_manual_ventilation": "manual_ventilation_active",
            "set_bag_mask_ventilation": "bag_mask_ventilation_active",
            "set_airway_protection": "airway_protection_score",
            "set_aspiration_risk": "aspiration_risk",
            "set_laryngospasm": "laryngospasm_score",
            "set_upper_airway_obstruction": "upper_airway_obstruction_score",
        }

        for item in timeline:
            t_event = float(item["t"])
            action  = item.get("action", "")
            value   = item.get("value")
            label   = item.get("label", action)

            if action == "fluid_bolus_mL":
                vol = float(value)
                def _fluid_cb(bus, v=vol):
                    bus.set("fluid_balance", bus.get("fluid_balance") + v)
                    bus.set("cumulative_fluid_input_mL", bus.get("cumulative_fluid_input_mL") + v)
                    cvp_rise = float(v / 100.0 * 1.5)
                    bus.set("CVP",  float(min(bus.get("CVP")  + cvp_rise, 18.0)))
                    bus.set("PAWP", float(min(bus.get("PAWP") + cvp_rise * 1.3, 25.0)))
                    edv_rise = v * 0.25
                    bus.set("EDV_lv", float(min(bus.get("EDV_lv") + edv_rise, 100.0)))
                p = Perturbation(t=t_event, callback=_fluid_cb,
                                 label=f"Fluid bolus {vol} mL")

            elif action == "transfuse_GRC":
                vol_grc = float(value)   # mL
                def _grc_cb(bus, v=vol_grc):
                    bus.set("GRC_pending_mL", bus.get("GRC_pending_mL") + v)
                p = Perturbation(t=t_event, callback=_grc_cb,
                                 label=f"GRC {vol_grc} mL")

            elif action == "transfuse_FFP":
                vol_ffp = float(value)
                def _ffp_cb(bus, v=vol_ffp):
                    bus.set("FFP_pending_mL", bus.get("FFP_pending_mL") + v)
                p = Perturbation(t=t_event, callback=_ffp_cb,
                                 label=f"PFC {vol_ffp} mL")

            elif action == "transfuse_PLT":
                units = int(value)
                def _plt_cb(bus, u=units):
                    bus.set("PLT_pending_units", int(bus.get("PLT_pending_units") + u))
                p = Perturbation(t=t_event, callback=_plt_cb,
                                 label=f"PLT {units} unità")

            elif action == "fibrinogen_concentrate":
                dose_g = float(value)
                def _fib_cb(bus, d=dose_g):
                    bus.set("fibrinogen_pending_g", bus.get("fibrinogen_pending_g") + d)
                p = Perturbation(t=t_event, callback=_fib_cb,
                                 label=f"Fibrinogeno concentrato {dose_g}g")

            elif action in _action_map:
                bus_key = _action_map[action]
                # selected interface fields are strings; selected flags are bool; all else float
                if bus_key in ("vent_mode", "airway_interface", "oxygen_interface", "NIV_mode"):
                    p = Perturbation(t=t_event, key=bus_key,
                                     value=str(value).upper(), label=label)
                elif bus_key in ("paracetamol_active", "osmo_active", "CRRT_active", "cooling_device_active", "external_warming_active", "antibiotic_started", "culture_drawn", "intubated", "ventilator_connected", "airway_pressure_delivery_enabled", "manual_ventilation_active", "bag_mask_ventilation_active"):
                    p = Perturbation(t=t_event, key=bus_key,
                                     value=bool(str(value).lower() != 'false' and value),
                                     label=label)
                else:
                    p = Perturbation(t=t_event, key=bus_key,
                                     value=float(value), label=label)
            else:
                # Perturbazione generica: action = bus_key diretto
                p = Perturbation(t=t_event, key=action,
                                 value=value, label=label)

            perturbs.append(p)

        # Acute event system v0.43: reusable named events.
        event_items = self.config.get("events", []) or []
        if event_items:
            perturbs.extend(build_event_perturbations(event_items))

        # Airway intubation/extubation event system v1.24.
        airway_event_items = self.config.get("airway_events", []) or []
        if airway_event_items:
            perturbs.extend(build_airway_event_perturbations(airway_event_items))

        # Cardiac rhythm/arrest event system v3.1 step4.33.
        cardiac_event_items = self.config.get("cardiac_events", []) or []
        if cardiac_event_items:
            perturbs.extend(build_cardiac_event_perturbations(cardiac_event_items))

        # Failure-to-rescue clock v3.1 step4.46: deterministic late
        # deterioration if the learner does not rescue within the displayed
        # critical window.
        ftr_block = self.config.get("failure_to_rescue", {}) or {}
        if ftr_block.get("escalation_enabled", False):
            try:
                from .failure_to_rescue import build_failure_escalation_perturbations
                for item in build_failure_escalation_perturbations(self.config):
                    perturbs.append(Perturbation(
                        t=float(item.get("t", 0.0)),
                        key=str(item.get("action", item.get("key", "failure_to_rescue"))),
                        value=item.get("value", 1.0),
                        label=str(item.get("label", "failure_to_rescue")),
                    ))
            except Exception:
                pass

        # Recovery engine v3.1 step4.48: if the scenario contains a correct
        # corrective action after the critical trigger, add delayed recovery
        # perturbations that pull shock/oxygenation/perfusion toward baseline.
        rec_block = self.config.get("recovery_engine", {}) or {}
        if rec_block.get("enabled", False):
            try:
                from .recovery_engine import build_recovery_perturbations
                for item in build_recovery_perturbations(self.config):
                    perturbs.append(Perturbation(
                        t=float(item.get("t", 0.0)),
                        key=str(item.get("action", item.get("key", "recovery_engine"))),
                        value=item.get("value", 1.0),
                        label=str(item.get("label", "recovery_engine")),
                    ))
            except Exception:
                pass

        return sorted(perturbs, key=lambda x: x.t)

    # --- Info ---

    @property
    def simulation_time(self) -> float:
        return float(self.config.get("simulation_time_s", 300.0))

    @property
    def scenario_name(self) -> str:
        return self.config.get("name", "unnamed_scenario")

    @property
    def timing_info(self) -> Dict[str, Any]:
        from .scenario_timing import scenario_timing_metadata
        return scenario_timing_metadata(self.config)

    @property
    def nominal_real_duration(self) -> float:
        return float(self.timing_info["real_duration_s"])

    @property
    def critical_event_trigger_time(self) -> float:
        return float(self.timing_info["critical_event_trigger_at_s"])

    @property
    def failure_to_rescue_info(self) -> Dict[str, Any]:
        from .failure_to_rescue import failure_to_rescue_metadata
        return failure_to_rescue_metadata(self.config)

    @property
    def recovery_info(self) -> Dict[str, Any]:
        from .recovery_engine import recovery_metadata, detect_first_corrective_action_time
        info = recovery_metadata(self.config)
        action_t = detect_first_corrective_action_time(self.config)
        info["first_corrective_action_time_s"] = action_t
        return info

    @property
    def patient_info(self) -> Dict[str, Any]:
        return self.config.get("patient", {})

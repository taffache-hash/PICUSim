#!/usr/bin/env python3
"""
Pediatric Digital Twin — Script di esecuzione standalone
=========================================================
Uso:
    python run_simulation.py --scenario scenarios/ards_mild.yaml
    python run_simulation.py --scenario scenarios/septic_shock.yaml --dt 0.05
    python run_simulation.py --list-scenarios
"""

import sys
import os
import argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# Path handling — funziona sia da /home/claude/pdt che da altrove
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import PhysiologicalBus, SimulationEngine, ScenarioLoader
from core.engine import Perturbation
from core.cardiovascular_scaling import (
    build_cardiovascular_scaling,
    heart_btb_params_from_scaling,
    circulation_params_from_scaling,
    baroreflex_params_from_scaling,
)

from modules.respiratory import (
    RespiratoryMechanicsModule,
    GasExchangeModule,
    ChemoreflexModule,
    AirwayInterfaceModule,
)
from modules.ventilator import VentilatorModule
from modules.cardiovascular import (
    HeartModule, HeartBTBModule,
    CirculationModule, BaroreflexModule,
)
from modules.pharmacology import PharmacologyModule, INOModule, TransfusionModule, SteroidsModule
from modules.metabolism import MetabolismModule
from modules.nutrition import GlucoseModule, NutritionCatabolismModule
from modules.renal import FluidBalanceModule, AKICRRTModule
from modules.coagulation import CoagulationModule
from modules.neurology import ICPModule, NeurofunctionalModule
from modules.analgosedation import PainStressSedationModule
from modules.airway import AirwayObstructionModule
from modules.sepsis import AdvancedSepsisModule
from modules.infection import InfectionAntimicrobialModule
from modules.acidbase import AcidBaseElectrolyteModule
from modules.endocrine import EndocrineStressAxisModule
from modules.hematology import HematologyOxygenTransportModule
from modules.hepatic import HepaticMetabolismModule
from modules.thermoregulation import ThermoregulationModule


# ---------------------------------------------------------------------------
# Costruttore del twin completo
# ---------------------------------------------------------------------------

def build_twin(bus, scenario_config: dict,
               dt: float = 0.02,
               enable_ICP=None,
               enable_ino: bool = True) -> SimulationEngine:
    """
    Assembla il Digital Twin con tutti i moduli (v0.6).
    enable_ICP=None → auto-detect da scenario (neurology section o ICP negli output).
    C_rs scalata per peso: valori YAML <= 5 → mL/cmH2O/kg; > 5 → assoluti (legacy).
    """
    resp_cfg  = scenario_config.get("respiratory", {})
    patient   = scenario_config.get("patient", {})
    cv_cfg    = scenario_config.get("cardiovascular", {})
    meta_cfg  = scenario_config.get("metabolism", {})
    coag_cfg  = scenario_config.get("coagulation", {})
    heme_cfg  = scenario_config.get("hematology", {})
    hepatic_cfg = scenario_config.get("hepatic", {})
    neur_cfg  = scenario_config.get("neurology", {})
    nutr_cfg  = scenario_config.get("nutrition", {})
    weight_kg = float(patient.get("weight_kg", getattr(bus.state, "weight_kg", 20.0)))
    age_y = float(patient.get("age_y", getattr(bus.state, "age_y", 6.0)))
    age_group = str(patient.get("age_group", getattr(bus.state, "age_group", "child")))
    patient_profile = str(patient.get("profile", getattr(bus.state, "patient_profile", "child_20kg")))

    # Auto-detect ICP
    if enable_ICP is None:
        outputs = scenario_config.get("outputs", [])
        enable_ICP = bool(neur_cfg or "ICP_mmHg" in outputs or "CPP_mmHg" in outputs)

    engine = SimulationEngine(bus, dt=dt, snapshot_every=5, verbose=True)

    engine.register(PharmacologyModule({
        "weight_kg": weight_kg,
        "age_y": age_y,
        "age_group": age_group,
        "patient_profile": patient_profile,
    }))
    engine.register(SteroidsModule({"weight_kg": weight_kg}))
    analgo_cfg = scenario_config.get("analgosedation", {})
    engine.register(PainStressSedationModule({
        "weight_kg": weight_kg,
        "baseline_pain": float(analgo_cfg.get("baseline_pain", 2.0)),
    }))
    if enable_ino:
        engine.register(INOModule())

    sepsis_cfg = scenario_config.get("sepsis", {})
    infection_cfg = scenario_config.get("infection", {})
    engine.register(InfectionAntimicrobialModule({
        "infection_load": float(infection_cfg.get("microbial_burden", sepsis_cfg.get("infection_load", 0.0))),
        "pathogen_virulence": float(infection_cfg.get("pathogen_virulence", 0.45)),
        "pathogen_resistance_index": float(infection_cfg.get("pathogen_resistance_index", 0.15)),
        "source_control": float(infection_cfg.get("source_control", sepsis_cfg.get("source_control", 0.0))),
        "antibiotic_coverage": float(infection_cfg.get("antibiotic_coverage", 0.0)),
        "antibiotic_started": bool(infection_cfg.get("antibiotic_started", False)),
        "infection_focus": infection_cfg.get("infection_focus", "unknown"),
    }))
    engine.register(AdvancedSepsisModule({
        "infection_load": float(sepsis_cfg.get("infection_load", infection_cfg.get("microbial_burden", 0.0))),
        "phenotype": sepsis_cfg.get("phenotype", "mixed"),
        "source_control": float(sepsis_cfg.get("source_control", infection_cfg.get("source_control", 0.0))),
        "antibiotic_effect": float(sepsis_cfg.get("antibiotic_effect", 0.0)),
    }))

    engine.register(HepaticMetabolismModule({
        "weight_kg": weight_kg,
        "albumin_baseline_g_dL": float(hepatic_cfg.get("albumin_g_dL", 3.8)),
        "bilirubin_total_baseline_mg_dL": float(hepatic_cfg.get("bilirubin_total_mg_dL", 0.5)),
        "bilirubin_direct_baseline_mg_dL": float(hepatic_cfg.get("bilirubin_direct_mg_dL", 0.15)),
        "AST_baseline_U_L": float(hepatic_cfg.get("AST_U_L", 35.0)),
        "ALT_baseline_U_L": float(hepatic_cfg.get("ALT_U_L", 25.0)),
    }))

    endocrine_cfg = scenario_config.get("endocrine", {})
    engine.register(EndocrineStressAxisModule({
        "weight_kg": weight_kg,
        "baseline_cortisol_activity": float(endocrine_cfg.get("cortisol_activity", 0.22)),
        "baseline_catecholamine_tone": float(endocrine_cfg.get("catecholamine_tone", 0.18)),
    }))

    thermo_cfg = scenario_config.get("thermoregulation", {})
    engine.register(ThermoregulationModule({
        "weight_kg": weight_kg,
        "baseline_setpoint_C": float(thermo_cfg.get("setpoint_T", meta_cfg.get("T_setpoint", 37.0))),
    }))

    neurofunc_cfg = scenario_config.get("neurofunctional", {})
    engine.register(NeurofunctionalModule({
        "weight_kg": weight_kg,
        "baseline_GCS": float(neurofunc_cfg.get("GCS_proxy", 15.0)),
    }))

    SIRS = float(meta_cfg.get("SIRS_factor", 1.0))
    T_sp = float(meta_cfg.get("T_setpoint", 37.0))
    engine.register(MetabolismModule({
        "weight_kg": weight_kg, "SIRS_factor": SIRS,
        "T_setpoint_baseline": T_sp,
        "lactate_DO2_crit": weight_kg * 15.0,
    }))
    engine.register(GlucoseModule({
        "weight_kg": weight_kg,
        "glucose_baseline_mmol_L": float(nutr_cfg.get("glucose_mmol_L", 5.0)),
        "GIR_mg_kg_min": float(nutr_cfg.get("GIR", nutr_cfg.get("GIR_mg_kg_min", 4.0))),
        "TPN_kcal_kg_h": float(nutr_cfg.get("TPN_kcal_kg_h", nutr_cfg.get("parenteral_kcal_kg_day", 0.0) / 24.0)),
        "EN_kcal_kg_h": float(nutr_cfg.get("EN_kcal_kg_h", 0.0)),
    }))
    engine.register(NutritionCatabolismModule({
        "weight_kg": weight_kg,
        "energy_target_kcal_kg_day": float(nutr_cfg.get("energy_target_kcal_kg_day", 55.0)),
        "protein_target_g_kg_day": float(nutr_cfg.get("protein_target_g_kg_day", 1.5)),
        "phosphate_baseline_mmol_L": float(nutr_cfg.get("phosphate_mmol_L", 1.35)),
        "magnesium_baseline_mmol_L": float(nutr_cfg.get("magnesium_mmol_L", 0.82)),
        "triglycerides_baseline_mmol_L": float(nutr_cfg.get("triglycerides_mmol_L", 1.0)),
    }))

    airway_cfg = scenario_config.get("airway", {})
    engine.register(AirwayObstructionModule({
        "baseline_bronchospasm": float(airway_cfg.get("bronchospasm_index", 0.0)),
        "baseline_mucus_load": float(airway_cfg.get("mucus_load", 0.0)),
        "baseline_small_airway_obstruction": float(airway_cfg.get("small_airway_obstruction", 0.0)),
    }))

    engine.register(ChemoreflexModule({"phi": 0.5, "Pmus_baseline": 5.0}))

    airway_interface_cfg = scenario_config.get("airway_interface", {}) or {}
    engine.register(AirwayInterfaceModule({
        "default_interface": str(airway_interface_cfg.get("interface", getattr(bus.state, "airway_interface", "ETT"))).upper(),
        "ambient_airway_pressure_cmH2O": float(airway_interface_cfg.get("ambient_airway_pressure_cmH2O", 0.0)),
    }))

    # Ventilatore — scrive Paw nel Bus prima di RespiratoryMechanics
    vent_cfg = scenario_config.get("ventilator", {})
    engine.register(VentilatorModule({
        "weight_kg":       weight_kg,
        "mode":            vent_cfg.get("mode", resp_cfg.get("mode", "PCV")),
        "RR":              float(resp_cfg.get("RR", 25.0)),
        "Vt_set_mL":       float(vent_cfg.get("Vt_set_mL",
                                  resp_cfg.get("Vt_set_mL", 6.0 * weight_kg))),
        "Pinsp_cmH2O":     float(vent_cfg.get("Pinsp", max(float(resp_cfg.get("Paw", 20.0)) - float(resp_cfg.get("PEEP", 5.0)), 0.0))),
        "PS_cmH2O":        float(vent_cfg.get("PS", 10.0)),
        "PEEP":            float(resp_cfg.get("PEEP", 5.0)),
        "FiO2":            float(resp_cfg.get("FiO2", 0.30)),
        "IE_ratio":        float(vent_cfg.get("IE_ratio", 0.38)),
        "T_rise_s":        float(vent_cfg.get("T_rise_s", 0.08)),
        "T_pause_s":       float(vent_cfg.get("T_pause_s", 0.0)),
        "trigger_thresh":  float(vent_cfg.get("trigger_thresh", 2.0)),
        "cycling_frac":    float(vent_cfg.get("cycling_frac", 0.25)),
        "flow_shape":      vent_cfg.get("flow_shape", "square"),
        "HFOV_freq_Hz":    float(vent_cfg.get("HFOV_freq_Hz", 10.0)),
        "HFOV_amplitude":  float(vent_cfg.get("HFOV_amplitude", 30.0)),
        "MAP_hfov":        float(vent_cfg.get("MAP_hfov", 18.0)),
        "alarm_Ppeak_max": float(vent_cfg.get("alarm_Ppeak_max", 45.0)),
    }))

    # C_rs peso-scalata (FIX radice ipercapnia)
    c_rs_yaml = float(resp_cfg.get("C_rs", 1.0))
    if c_rs_yaml <= 5.0:
        C_rs_max = c_rs_yaml * weight_kg   # mL/cmH2O/kg → mL/cmH2O totale
        C_rs_min = 0.15 * weight_kg
    else:
        C_rs_max = c_rs_yaml               # già valore assoluto (legacy)
        C_rs_min = 0.15 * weight_kg

    non_rec_frac = float(resp_cfg.get("non_recruitable_frac", 0.0))

    engine.register(RespiratoryMechanicsModule({
        "C_rs_max": C_rs_max,
        "C_rs_min": C_rs_min,
        "R_rs":     float(resp_cfg.get("R_rs", 8.0)),
        "weight_kg": weight_kg,
        "non_recruitable_frac": non_rec_frac,
    }))
    engine.register(GasExchangeModule({
        "Qs_Qt": 0.10 + (1.0 - float(resp_cfg.get("SaO2", 0.97))) * 1.5,
    }))

    acid_cfg = scenario_config.get("acidbase", {})
    renal_cfg = scenario_config.get("renal", {})
    engine.register(AcidBaseElectrolyteModule({
        "weight_kg": weight_kg,
        "Na_baseline": float(acid_cfg.get("Na_mmol_L", 138.0)),
        "K_baseline": float(acid_cfg.get("K_mmol_L", 4.0)),
        "Cl_baseline": float(acid_cfg.get("Cl_mmol_L", 103.0)),
        "HCO3_baseline": float(acid_cfg.get("HCO3_mmol_L", 24.0)),
    }))

    cv_scaling = build_cardiovascular_scaling(
        weight_kg=weight_kg,
        age_y=age_y,
        age_group=age_group,
        patient_profile=patient_profile,
        HR_ref=(float(getattr(bus.state, "HR", 100.0)) if "HR" not in cv_cfg else None),
        MAP_ref=(float(getattr(bus.state, "MAP", 65.0)) if "MAP" not in cv_cfg else None),
        CO_ref_L_min=None,
        CVP_ref=(float(getattr(bus.state, "CVP", 5.0)) if "CVP" not in cv_cfg else None),
        PAWP_ref=(float(getattr(bus.state, "PAWP", 8.0)) if "PAWP" not in cv_cfg else None),
        PAP_ref=(float(getattr(bus.state, "PAP_mean", 15.0)) if "PAP_mean" not in cv_cfg else None),
    )
    bus.update({
        "cv_scaling_weight_kg": float(cv_scaling["weight_kg"]),
        "cv_scaling_profile": str(cv_scaling["patient_profile"]),
        "cv_scaling_revision": str(cv_scaling["cv_scaling_revision"]),
        "cv_EDV0_lv_ref": float(cv_scaling["EDV0_lv"]),
        "cv_Emax_lv_ref": float(cv_scaling["Emax_lv"]),
        "cv_R_systemic_ref": float(cv_scaling["R_systemic"]),
    })

    engine.register(HeartBTBModule(heart_btb_params_from_scaling(cv_scaling)))
    engine.register(CirculationModule(circulation_params_from_scaling(cv_scaling)))
    engine.register(BaroreflexModule(baroreflex_params_from_scaling(cv_scaling, auto_setpoint=False)))

    engine.register(CoagulationModule({
        "INR_baseline":        float(coag_cfg.get("INR", 1.0)),
        "PLT_baseline":        float(coag_cfg.get("PLT", 200.0)),
        "fibrinogen_baseline": float(coag_cfg.get("fibrinogen", 2.5)),
    }))
    engine.register(FluidBalanceModule({
        "weight_kg":          weight_kg,
        "Hb_baseline":        float(cv_cfg.get("Hb", 11.0)),
        "plasma_volume_L":    weight_kg * 0.05,
        "infusion_rate_mL_h": weight_kg * 1.5,
        "GFR_baseline":       float(renal_cfg.get("GFR_baseline", weight_kg * 3.5)),
    }))
    engine.register(AKICRRTModule({
        "weight_kg": weight_kg,
        "GFR_baseline": float(renal_cfg.get("GFR_baseline", weight_kg * 3.5)),
        "creatinine_baseline_mg_dL": float(renal_cfg.get("creatinine_baseline_mg_dL", 0.25 + 0.005 * weight_kg)),
        "urea_baseline_mmol_L": float(renal_cfg.get("urea_baseline_mmol_L", acid_cfg.get("urea_mmol_L", 5.0))),
    }))
    engine.register(TransfusionModule({
        "weight_kg":      weight_kg,
        "plasma_volume_L": weight_kg * 0.05,
        "Hb_baseline":    float(cv_cfg.get("Hb", 11.0)),
        "auto_transfuse": False,
    }))
    engine.register(HematologyOxygenTransportModule({
        "weight_kg": weight_kg,
        "Hb_baseline": float(cv_cfg.get("Hb", heme_cfg.get("Hb", 11.0))),
        "WBC_baseline": float(heme_cfg.get("WBC_count", 8.0)),
        "neutrophil_baseline": float(heme_cfg.get("neutrophil_count", 5.0)),
        "lymphocyte_baseline": float(heme_cfg.get("lymphocyte_count", 2.2)),
        "transfusion_threshold_Hb": float(heme_cfg.get("transfusion_threshold_Hb", 7.0)),
    }))

    if enable_ICP:
        engine.register(ICPModule({
            "ICP_baseline":        float(neur_cfg.get("ICP", 10.0)),
            "V_edema_baseline":    float(neur_cfg.get("V_edema", 0.0)),
            "autoregulation_gain": float(neur_cfg.get("autoregulation", 1.0)),
        }))

    return engine


# ---------------------------------------------------------------------------
# Plot risultati
# ---------------------------------------------------------------------------

def plot_results(df, scenario_name: str = ""):
    """Pannello di 12 variabili chiave."""
    t = df.index

    fig = plt.figure(figsize=(16, 12))
    fig.suptitle(f"Pediatric Digital Twin — {scenario_name}",
                 fontsize=14, fontweight="bold")

    gs = gridspec.GridSpec(4, 3, hspace=0.45, wspace=0.35)

    panels = [
        ("Paw",          "Paw [cmH2O]",       "#2196F3"),
        ("EELV",         "EELV [mL]",          "#4CAF50"),
        ("recruited_frac","Frazione reclutata", "#FF9800"),
        ("SaO2",         "SaO2 [%]",           "#E91E63"),
        ("PaO2",         "PaO2 [mmHg]",        "#9C27B0"),
        ("PaCO2",        "PaCO2 [mmHg]",       "#607D8B"),
        ("MAP",          "MAP [mmHg]",          "#F44336"),
        ("CO",           "CO [L/min]",          "#009688"),
        ("HR",           "FC [bpm]",            "#795548"),
        ("MP",           "MP [J/min]",          "#FF5722"),
        ("Pdriving",     "Pdriving [cmH2O]",    "#3F51B5"),
        ("DO2",          "DO2 [mL/min]",        "#8BC34A"),
    ]

    for idx, (col, label, color) in enumerate(panels):
        row, c = divmod(idx, 3)
        ax = fig.add_subplot(gs[row, c])

        if col in df.columns:
            y = df[col].values
            if col == "SaO2":
                y = y * 100.0    # → %
            elif col == "recruited_frac":
                y = y * 100.0    # → %
            ax.plot(t, y, color=color, linewidth=1.5)
            ax.set_ylabel(label, fontsize=8)
            ax.set_xlabel("t [s]", fontsize=7)
            ax.grid(True, alpha=0.3)
            ax.tick_params(labelsize=7)
        else:
            ax.text(0.5, 0.5, f"{col}\nnon disponibile",
                    ha="center", va="center", transform=ax.transAxes,
                    fontsize=8, color="gray")
            ax.set_xlabel("t [s]", fontsize=7)

    return fig


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Pediatric Digital Twin")
    parser.add_argument("--scenario", default="scenarios/ards_mild.yaml",
                        help="Path al file YAML dello scenario")
    parser.add_argument("--dt", type=float, default=0.02,
                        help="Timestep [s] (default 0.02)")
    parser.add_argument("--no-plot", action="store_true",
                        help="Disabilita il plot")
    parser.add_argument("--save-csv", default=None,
                        help="Salva risultati in CSV")
    parser.add_argument("--list-scenarios", action="store_true",
                        help="Lista scenari disponibili")
    args = parser.parse_args()

    if args.list_scenarios:
        scen_dir = os.path.join(os.path.dirname(__file__), "scenarios")
        yamls = [f for f in os.listdir(scen_dir) if f.endswith(".yaml")]
        print("Scenari disponibili:")
        for y in yamls:
            print(f"  scenarios/{y}")
        return

    # Carica scenario
    scen_path = args.scenario
    if not os.path.isabs(scen_path):
        scen_path = os.path.join(os.path.dirname(__file__), scen_path)

    print(f"\n[PDT] Caricamento scenario: {scen_path}")
    loader  = ScenarioLoader.from_yaml(scen_path)
    bus     = loader.build_bus()
    perturbs = loader.build_perturbations()
    T_sim   = loader.simulation_time

    print(f"[PDT] Paziente: {loader.patient_info}")
    print(f"[PDT] T_sim={T_sim}s, perturbazioni={len(perturbs)}")
    print(f"[PDT] {bus}")

    # Assembla e esegui
    engine = build_twin(bus, loader.config, dt=args.dt)
    engine.add_perturbations(perturbs)
    df = engine.run(T=T_sim)

    print(f"\n[PDT] Snapshot finali:")
    final_cols = ["SaO2", "PaO2", "PaCO2", "pH_a", "HCO3_mmol_L", "base_excess_mmol_L",
                  "Na_mmol_L", "K_mmol_L", "Cl_mmol_L", "anion_gap_mmol_L",
                  "creatinine_mg_dL", "urea_mmol_L", "AKI_stage", "urine_output_mL_kg_h",
                  "fluid_overload_percent", "RRT_indication_score", "CRRT_active_effective",
                  "cortisol_activity", "catecholamine_tone", "adrenal_insufficiency_index",
                  "insulin_resistance_index", "stress_hyperglycemia_index",
                  "ADH_water_retention_index", "endocrine_severity_score",
                  "MAP", "CO", "HR", "EELV", "recruited_frac", "MP", "DO2",
                  "T_core", "setpoint_T", "fever_drive", "shivering_index",
                  "hypothermia_index", "hyperthermia_index", "thermo_VO2_mod",
                  "thermo_HR_add", "temperature_instability_score",
                  "GCS_proxy", "AVPU_state", "encephalopathy_index", "seizure_risk_index",
                  "delirium_state_index", "withdrawal_state_index", "neuro_severity_score",
                  "RASS_proxy",
                  "airway_interface", "intubated", "ventilator_connected",
                  "airway_pressure_delivery_enabled", "unassisted_breathing_active",
                  "airway_pressure_source", "airway_interface_revision",
                  "oxygen_interface", "oxygen_flow_L_min", "oxygen_FiO2_set",
                  "FiO2_delivered", "FiO2_delivery_efficiency",
                  "HFNC_flow_L_min", "HFNC_FiO2_set", "HFNC_distending_pressure_cmH2O",
                  "HFNC_deadspace_washout", "HFNC_failure_risk", "mouth_leak_fraction",
                  "oxygen_delivery_revision",
                  "tube_internal_diameter_mm", "tube_length_cm", "tube_resistance_cmH2O_L_s",
                  "tube_resistance_factor", "tube_dead_space_mL", "tube_VdVt_add",
                  "tube_obstruction_score", "cuff_leak_fraction", "ETT_failure_risk",
                  "artificial_airway_revision",
                  "energy_balance_kcal_day", "protein_balance_g_day", "catabolism_index",
                  "feeding_intolerance_index", "refeeding_risk_index", "phosphate_mmol_L",
                  "magnesium_mmol_L", "triglycerides_mmol_L", "nutrition_severity_score",
                  "microbial_burden", "antibiotic_coverage", "antibiotic_effect",
                  "culture_positivity_probability", "antimicrobial_escalation_score",
                  "antimicrobial_deescalation_readiness", "inadequate_coverage_index",
                  "infection_severity_score",
                  "C_adrenaline_ng_mL", "C_dopamine_ng_mL", "C_fentanyl_ng_mL",
                  "C_morphine_ng_mL", "C_clonidine_ng_mL", "C_insulin_mU_L", "C_piperacillin_mg_L", "C_dexmedetomidine_ng_mL", "C_vancomycin_mg_L", "C_furosemide_mg_L",
                  "vancomycin_target_attainment", "vancomycin_coverage_mod",
                  "piperacillin_ft_above_MIC", "piperacillin_target_attainment",
                  "piperacillin_kill_signal", "piperacillin_coverage_mod",
                  "furosemide_effect_signal", "furosemide_renal_clearance_factor",
                  "morphine_analgesia_signal", "morphine_resp_depression_signal",
                  "morphine_renal_accumulation_risk", "M6G_accumulation_proxy",
                  "clonidine_sedation_signal", "clonidine_sympatholysis_signal",
                  "clonidine_bradycardia_risk", "clonidine_hypotension_risk",
                  "clonidine_withdrawal_mod",
                  "insulin_glucose_clearance_signal", "insulin_potassium_shift_signal",
                  "insulin_hypoglycemia_risk", "insulin_effective_clearance_mmol_L_h",
                  "pk_supported_drug_count",
                  "pk_extension_revision", "pk_crrt_active", "pk_crrt_effluent_L_min",
                  "pk_crrt_midazolam_CL_L_min", "pk_crrt_rocuronium_CL_L_min",
                  "pk_crrt_vancomycin_CL_L_min", "pk_crrt_furosemide_CL_L_min",
                  "pk_crrt_morphine_CL_L_min", "pk_crrt_clonidine_CL_L_min",
                  "pk_crrt_insulin_CL_L_min", "pk_crrt_piperacillin_CL_L_min"]
    for col in final_cols:
        if col in df.columns:
            val = df[col].iloc[-1]
            if col in ("SaO2", "recruited_frac"):
                print(f"  {col:20s} = {val*100:.1f}%")
            elif isinstance(val, str):
                print(f"  {col:20s} = {val}")
            else:
                print(f"  {col:20s} = {val:.2f}")

    # CSV
    if args.save_csv:
        df.to_csv(args.save_csv)
        print(f"[PDT] CSV salvato: {args.save_csv}")

    # Plot
    if not args.no_plot:
        fig = plot_results(df, loader.scenario_name)
        out_plot = os.path.join(
            os.path.dirname(__file__), "outputs",
            f"{loader.scenario_name}_results.png"
        )
        os.makedirs(os.path.dirname(out_plot), exist_ok=True)
        fig.savefig(out_plot, dpi=150, bbox_inches="tight")
        print(f"[PDT] Plot salvato: {out_plot}")
        plt.show()


if __name__ == "__main__":
    main()

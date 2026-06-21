"""
PhysiologicalBus
================
Dizionario tipizzato di variabili fisiologiche condivise.
Ogni modulo legge le proprie variabili di input dal Bus
e scrive le proprie output al Bus al termine di ogni step.

Convenzione di naming:
  - Pressioni in cmH2O (respiratorie) o mmHg (cardiovascolari)
  - Volumi in mL
  - Flussi in mL/s o L/min (specificato per dominio)
  - Tempo in secondi
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, Any, List
import copy


# ---------------------------------------------------------------------------
# Stato del Bus a un singolo timestep
# ---------------------------------------------------------------------------

@dataclass
class BusState:
    """
    Stato fisiologico completo a un istante t.
    Tutti i campi hanno un valore di default fisiologicamente plausibile
    per un bambino sano di ~20 kg. I moduli sovrascrivono i loro campi.
    """
    t: float = 0.0           # [s] tempo corrente

    # --- PAZIENTE / PROFILO PEDIATRICO ---
    age_y: float = 6.0
    weight_kg: float = 20.0
    BSA_m2: float = 0.80

    # --- RESPIRATORIO ---
    Paw: float      = 12.0   # [cmH2O] pressione alle vie aeree (ventilatore)
    Palv: float     = 5.0    # [cmH2O] pressione alveolare media
    Ppl: float      = -5.0   # [cmH2O] pressione pleurica (media respiratoria)
    Pmus: float     = 0.0    # [cmH2O] pressione muscolare inspiratoria (+ = sforzo)
    V_lung: float   = 25.0   # [mL] volume corrente istantaneo (Vt)
    EELV: float     = 320.0  # [mL] volume polmonare a fine espirazione (FRC + reclutato)
    FRC: float      = 320.0  # [mL] FRC baseline (costante per il paziente)
    recruited_frac: float = 0.75  # [0-1] frazione alveolare reclutata
    R_rs: float     = 8.0    # [cmH2O/L/s] resistenza vie aeree totali
    C_rs: float     = 1.5    # [mL/cmH2O] compliance sistema respiratorio (per mL/cmH2O)
    E_rs: float     = 40.0   # [cmH2O/L] elastanza sistema respiratorio

    # Gas arteriosi
    PaO2: float     = 90.0   # [mmHg]
    PaCO2: float    = 40.0   # [mmHg]
    EtCO2: float    = 35.0   # [mmHg] model-coupled end-tidal CO2 estimate
    EtCO2_proxy: float = 35.0 # [mmHg] backward-compatible alias for waveform clients
    etco2_pa_gradient: float = 5.0   # [mmHg] PaCO2 - EtCO2 audit gradient
    etco2_perfusion_factor: float = 1.0   # capnography attenuation from low pulmonary blood flow/CO
    etco2_deadspace_factor: float = 0.30  # effective dead-space burden used for EtCO2
    etco2_source: str = "initialized"
    SaO2: float     = 0.97   # [0-1] saturazione ossiemoglobina arteriosa
    pH_a: float     = 7.40   # [-] pH arterioso
    FiO2: float     = 0.30   # [0-1] frazione inspiratoria O2
    PEEP: float     = 5.0    # [cmH2O] PEEP impostata
    RR: float       = 25.0   # [atti/min] frequenza respiratoria
    ventilator_RR_set: float = 0.0  # [atti/min] comando ventilatore separato da RR fisiologica
    Vt: float       = 200.0  # [mL] volume tidal per atto

    # --- v1.23 AIRWAY INTERFACE BASE ---
    airway_interface: str = "ETT"              # ETT|UNASSISTED|NONE|LOW_FLOW_OXYGEN|SIMPLE_MASK|HFNC|NIV_CPAP|NIV_BIPAP|TRACHEOSTOMY
    intubated: bool = True                      # explicit educational flag
    ventilator_connected: bool = True           # active ventilator/circuit connected
    airway_pressure_delivery_enabled: bool = True # ventilator Paw can be delivered to patient
    unassisted_breathing_active: bool = False   # true when Paw is ambient/HFNC and Pmus drives breathing
    spontaneous_airway_mode: bool = False       # true for non-invasive/spontaneous interfaces
    ambient_airway_pressure_cmH2O: float = 0.0  # ambient airway pressure used in NONE/UNASSISTED
    effective_external_PEEP_cmH2O: float = 5.0  # interface-level distending pressure proxy
    airway_interface_revision: int = 0          # schema marker, 123 from v1.23; 1231 for oxygen/HFNC
    airway_interface_note: str = "pre-v1.23"
    airway_pressure_source: str = "ventilator" # ventilator|ambient|oxygen_interface|HFNC_flow|future_NIV

    # --- v1.23.1 OXYGEN DELIVERY / HFNC BASE ---
    oxygen_interface: str = "VENTILATOR"        # ROOM_AIR|LOW_FLOW_OXYGEN|SIMPLE_MASK|HFNC|VENTILATOR
    oxygen_flow_L_min: float = 0.0              # total flow for low-flow/mask/HFNC proxy
    oxygen_FiO2_set: float = 0.21               # oxygen source setting [0-1]
    FiO2_delivered: float = 0.30                # effective inspired oxygen after interface/leak
    FiO2_delivery_efficiency: float = 1.0       # educational delivery efficiency [0-1]
    HFNC_flow_L_min: float = 0.0                # high-flow nasal cannula flow
    HFNC_FiO2_set: float = 0.21                 # high-flow oxygen blender setting
    HFNC_distending_pressure_cmH2O: float = 0.0 # qualitative CPAP-like pressure from high flow
    HFNC_deadspace_washout: float = 0.0         # qualitative reduction in effective dead-space burden [0-1]
    HFNC_failure_risk: float = 0.0              # qualitative risk marker [0-1]
    mouth_leak_fraction: float = 0.25           # leak/open-mouth proxy for HFNC/NIV [0-1]
    oxygen_delivery_revision: int = 0           # schema marker, 1231 from v1.23.1; 1232 for NIV

    # --- v1.23.2 NIV / CPAP / BiPAP BASE ---
    NIV_mode: str = "OFF"                       # OFF|CPAP|BIPAP
    NIV_CPAP_cmH2O: float = 6.0                 # mask CPAP setting
    NIV_IPAP_cmH2O: float = 14.0                # bilevel inspiratory pressure setting
    NIV_EPAP_cmH2O: float = 6.0                 # bilevel expiratory pressure setting
    NIV_pressure_support_cmH2O: float = 8.0     # IPAP-EPAP proxy
    NIV_FiO2_set: float = 0.40                  # NIV oxygen blender/source setting
    NIV_leak_fraction: float = 0.28             # mask leak proxy [0-1]
    mask_leak_fraction: float = 0.28            # alias/proxy for mask leak [0-1]
    NIV_delivered_PEEP_cmH2O: float = 0.0       # leak-adjusted EPAP/CPAP proxy
    NIV_delivered_PS_cmH2O: float = 0.0         # leak-adjusted pressure support proxy
    NIV_delivered_PIP_cmH2O: float = 0.0        # delivered PEEP + delivered PS
    NIV_deadspace_washout: float = 0.0          # qualitative NIV washout/ventilation assistance [0-1]
    NIV_failure_risk: float = 0.0               # qualitative NIV failure marker [0-1]

    # --- v1.23.3 ARTIFICIAL AIRWAY / ETT-TRACHEOSTOMY BASE ---
    tube_internal_diameter_mm: float = 5.0       # ETT/tracheostomy internal diameter [mm]
    tube_length_cm: float = 16.0                 # approximate artificial-airway length [cm]
    tube_resistance_cmH2O_L_s: float = 6.0       # qualitative tube resistance at 1 L/s
    tube_resistance_factor: float = 1.0          # multiplier applied to airway_resistance_mod
    tube_dead_space_mL: float = 5.0              # tube + connector apparatus dead-space proxy [mL]
    tube_VdVt_add: float = 0.0                   # additive dead-space fraction from artificial airway [0-1]
    tube_obstruction_score: float = 0.0          # secretion/kink/biting obstruction proxy [0-1]
    cuff_leak_fraction: float = 0.0              # leak around tube/cuff [0-1]
    cuff_pressure_cmH2O: float = 20.0            # cuff pressure proxy, not clinical guidance
    ETT_position_score: float = 1.0              # 1 ideal, lower = malposition proxy
    ETT_pressure_delivery_efficiency: float = 1.0# pressure delivery after leak/obstruction [0-1]
    ETT_FiO2_delivery_efficiency: float = 1.0    # FiO2 delivery after leak [0-1]
    ETT_failure_risk: float = 0.0                # qualitative artificial-airway concern [0-1]
    artificial_airway_revision: int = 0          # schema marker, 1233 from v1.23.3

    # --- v1.24 AIRWAY INTUBATION / EXTUBATION EVENT SYSTEM ---
    airway_event_revision: int = 0              # schema marker, 1240 from v1.24
    airway_event_active: bool = False           # true when an airway event has occurred
    airway_event_type: str = "none"             # perform_intubation|failed_intubation|extubation|...
    airway_event_label: str = "none"            # human-readable last airway event label
    airway_event_status: str = "none"           # pending|success|failed|rescue
    airway_event_time_s: float = -1.0           # last airway event time [s]
    airway_rescue_state: str = "stable"         # stable|at_risk|failed_attempt|secured_ETT|extubated|rescued_BVM
    intubation_attempt_count: int = 0            # cumulative educational counter
    failed_intubation_count: int = 0             # cumulative failed attempts
    intubation_success_time_s: float = -1.0      # time of successful intubation [s]
    extubation_time_s: float = -1.0              # time of last planned/accidental extubation [s]
    manual_ventilation_active: bool = False      # bag-mask/manual ventilation proxy
    bag_mask_ventilation_active: bool = False    # explicit BVM proxy flag
    bag_mask_quality: float = 0.0                # quality proxy [0-1]
    airway_protection_score: float = 1.0         # qualitative airway protection [0-1]
    aspiration_risk: float = 0.0                 # qualitative aspiration risk [0-1]
    laryngospasm_score: float = 0.0              # qualitative upper airway closure [0-1]
    upper_airway_obstruction_score: float = 0.0  # obstruction above ETT/trachea [0-1]
    airway_event_hypoxia_burden: float = 0.0     # event-related hypoxia burden proxy [0-1]

    # --- v3.1 STEP 4.41 PERI-INTUBATION PHYSIOLOGY ---
    intubation_physiology_revision: int = 0
    preoxygenation_active: bool = False
    preoxygenation_reservoir: float = 0.45       # qualitative oxygen reserve [0-1]
    apnea_active: bool = False
    apnea_timer_s: float = 0.0                   # continuous apnea burden [s]
    safe_apnea_time_remaining_s: float = 0.0     # bounded educational reserve timer [s]
    rsi_effect_active: bool = False
    rsi_resp_suppression_index: float = 0.0      # NMB/sedation-related respiratory suppression [0-1]
    peri_intubation_desaturation_risk: float = 0.0
    peri_intubation_desaturation_slope: float = 0.0
    peri_intubation_phase: str = "stable"
    peri_intubation_warning: str = "none"

    # Gas venosi (per calcolo DO2/VO2)
    PvO2: float     = 35.0   # [mmHg]
    SvO2: float     = 0.70   # [0-1]
    ScvO2: float    = 0.70   # [0-1] central venous oxygen saturation proxy
    ScvO2_source: str = "initialized"
    ScvO2_revision: int = 0

    # --- v1.06 PUBLIC V/Q GAS EXCHANGE AUDIT ---
    vq_shunt_frac: float = 0.10              # perfused non-ventilated fraction [0-1]
    vq_deadspace_frac: float = 0.30          # ventilated poorly/non-perfused fraction [0-1]
    vq_exchange_frac: float = 0.90           # perfused ventilated exchange fraction [0-1]
    vq_logsd: float = 0.35                   # log-normal V/Q dispersion proxy
    vq_adaptive_sigma: float = 0.35          # v1.20 pathology-adaptive V/Q dispersion proxy
    vq_ards_weight: float = 0.0              # [0-1] ARDS/derecruitment driver for V/Q mismatch
    vq_obstruction_weight: float = 0.0       # [0-1] obstructive/dead-space driver for V/Q mismatch
    vq_shock_weight: float = 0.0             # [0-1] sepsis/shock perfusion driver for V/Q mismatch
    vq_neonatal_weight: float = 0.0          # [0-1] neonatal/RDS-like driver for V/Q mismatch
    vq_pathology_driver: str = "none"        # dominant qualitative V/Q driver
    vq_low_vq_burden: float = 0.0            # weight of low V/Q bins inside exchange zone
    vq_high_vq_burden: float = 0.0           # weight of high V/Q bins inside exchange zone
    alveolar_ventilation_L_min: float = 3.0  # effective alveolar ventilation [L/min]
    gas_exchange_revision: str = "pre-v1.06"
    vq_adaptive_revision: int = 0            # schema marker for v1.20 adaptive V/Q dispersion

    # Meccanica polmonare avanzata
    MP: float       = 0.0    # [J/min] conventional Mechanical Power, when applicable
    MP_applicable: bool = True              # conventional MP formula applicable to current mode
    MP_method: str = "conventional_bedside_approximation"
    HFOV_power_proxy: float = 0.0           # qualitative HFOV-specific audit proxy, not J/min
    Pdriving: float = 0.0    # [cmH2O] driving pressure (Pplat - PEEP)
    WOB: float      = 0.0    # [J/L] work of breathing paziente

    # Chemoreflex
    drive_level: float = 1.0  # [0-2] livello di drive chemioriflessivo normalizzato

    # --- CARDIOVASCOLARE ---
    HR: float       = 110.0  # [bpm] frequenza cardiaca
    SV: float       = 35.0   # [mL] stroke volume
    CO: float       = 3.85   # [L/min] gittata cardiaca

    # Pressioni cardiache
    MAP: float      = 65.0   # [mmHg] pressione arteriosa media sistemica
    SAP: float      = 90.0   # [mmHg] pressione arteriosa sistolica
    DAP: float      = 50.0   # [mmHg] pressione arteriosa diastolica
    SBP: float      = 90.0   # [mmHg] bedside alias for SAP used by waveform/UI profiles
    DBP: float      = 50.0   # [mmHg] bedside alias for DAP used by waveform/UI profiles
    arterial_pulse_pressure: float = 40.0  # [mmHg] SBP-DBP audit signal for ABP waveform
    arterial_pressure_source: str = "initialized"  # source marker for bedside ABP values
    SAP_btb: float  = 90.0   # [mmHg] systolic pressure feature from beat-to-beat heart model (non-bedside master)
    DAP_btb: float  = 50.0   # [mmHg] diastolic pressure feature from beat-to-beat heart model (non-bedside master)
    CVP: float      = 5.0    # [mmHg] pressione venosa centrale
    PAP_mean: float = 15.0   # [mmHg] pressione arteria polmonare media
    PAWP: float     = 8.0    # [mmHg] wedge pressure polmonare

    # --- v3.1 C.1 CARDIAC RHYTHM / ARREST STATE ---
    cardiac_event_revision: int = 0
    cardiac_event_active: bool = False
    cardiac_event_type: str = "none"
    cardiac_event_time_s: float = -1.0
    cardiac_arrest_cause: str = "none"
    cardiac_rhythm: str = "sinus"              # sinus|bradycardia|vt_with_pulse|pulseless_vt|vf|pea|asystole
    rhythm_category: str = "pulsed"            # pulsed|shockable|nonshockable
    has_pulse: bool = True
    cardiac_arrest_active: bool = False
    shockable_rhythm: bool = False
    ROSC: bool = False
    post_arrest_phase: bool = False
    cardiac_arrest_time_s: float = -1.0
    rosc_time_s: float = -1.0
    CPR_active: bool = False
    CPR_quality: float = 0.0                   # [0-1] qualitative compression quality
    compression_fraction: float = 0.0          # [0-1] no-flow minimisation proxy
    last_shock_energy_J: float = 0.0
    last_shock_time_s: float = -1.0
    last_shock_mode: str = "none"
    last_shock_appropriate: bool = False
    last_shock_effective: bool = False
    last_shock_result: str = "none"
    defibrillation_attempt_count: int = 0
    synchronized_cardioversion_count: int = 0
    epinephrine_bolus_count: int = 0
    amiodarone_bolus_count: int = 0
    atropine_bolus_count: int = 0
    last_rcp_drug: str = "none"
    last_rcp_drug_result: str = "none"
    last_rcp_drug_appropriate: bool = False
    last_rcp_drug_time_s: float = -1.0
    reperfusion_injury_risk: float = 0.0       # [0-1] post-ROSC qualitative risk
    renal_hypoperfusion_index: float = 0.0     # [0-1] arrest/shock renal perfusion burden
    post_rosc_care_status: str = "none"        # none|needed|active
    post_rosc_care_time_s: float = -1.0
    post_rosc_oxygenation_optimized: bool = False
    post_rosc_ventilation_optimized: bool = False
    post_rosc_perfusion_support_active: bool = False
    post_rosc_acidosis_burden: float = 0.0      # [0-1] qualitative post-arrest acidosis burden
    post_rosc_myocardial_dysfunction_risk: float = 0.0  # [0-1] qualitative low-output risk

    # Volumi cardiaci
    EDV_lv: float   = 55.0   # [mL] volume telediastolico LV
    ESV_lv: float   = 20.0   # [mL] volume telesistolico LV
    EF_lv: float    = 0.64   # [-] frazione di eiezione LV

    # Resistenze vascolari
    SVR: float      = 1200.0 # [dyne·s/cm5] resistenza vascolare sistemica
    PVR: float      = 80.0   # [dyne·s/cm5] resistenza vascolare polmonare

    # Trasporto O2
    Hb: float       = 11.0   # [g/dL] emoglobina
    DO2: float      = 500.0  # [mL/min] delivery O2 sistemica
    VO2: float      = 120.0  # [mL/min] consumo O2
    ERO2: float     = 0.24   # [-] extraction ratio O2

    # --- METABOLISMO / FLUIDI ---
    T_core: float   = 37.0   # [°C] temperatura corporea

    # --- v0.24 THERMOREGULATION ---
    fever_drive: float = 0.0                 # [0-1] drive febbrile/ipotalamico
    hypothermia_index: float = 0.0           # [0-1] burden ipotermico
    hyperthermia_index: float = 0.0          # [0-1] burden ipertermico
    shivering_index: float = 0.0             # [0-1] brivido/termogenesi muscolare
    cooling_effect: float = 0.0              # [0-1] raffreddamento attivo
    warming_effect: float = 0.0              # [0-1] riscaldamento attivo
    antipyretic_effect: float = 0.0          # [0-1] effetto antipiretico
    heat_loss_index: float = 0.0             # [0-1] dispersione termica/cooling
    thermo_VO2_mod: float = 1.0              # moltiplicatore VO2 da temperatura/brivido
    thermo_HR_add: float = 0.0               # bpm additivi da febbre/brivido
    thermo_coag_mod: float = 1.0             # peggioramento qualitativo coagulazione da ipo/ipertermia
    thermo_lactate_mod: float = 1.0          # moltiplicatore produzione lattato da brivido/temperatura
    temperature_instability_score: float = 0.0
    cooling_device_active: bool = False
    external_warming_active: bool = False
    target_temperature_C: float = 37.0
    fluid_balance: float = 0.0  # [mL] bilancio idrico cumulativo
    cumulative_fluid_input_mL: float = 0.0
    cumulative_urine_output_mL: float = 0.0
    cumulative_crrt_UF_mL: float = 0.0
    cumulative_insensible_loss_mL: float = 0.0
    fluid_balance_error_mL: float = 0.0
    # --- v3.1 Step 5.6A CRYSTALLOID INFUSIONS ---
    crystalloid_type: str = "normal_saline"      # normal_saline|ringer_lactate|sterofundin|dextrose_5
    crystalloid_rate_mL_h: float = 0.0            # user-controlled crystalloid infusion rate
    crystalloid_active: bool = False
    crystalloid_effective_mL_h: float = 0.0       # accepted/current crystalloid rate after bounds
    crystalloid_balanced_fraction: float = 0.0    # balanced crystalloid marker [0-1]
    crystalloid_chloride_load_index: float = 0.0  # saline-associated chloride burden proxy [0-1]
    crystalloid_glucose_GIR_mg_kg_min: float = 0.0
    crystalloid_preload_response: float = 0.0     # qualitative fluid responsiveness signal [0-1]
    crystalloid_MAP_support_mmHg: float = 0.0     # bounded transient pressure support from fluid response
    crystalloid_renal_perfusion_gain: float = 0.0 # bounded diuresis/perfusion support [0-1]
    crystalloid_CO_mod: float = 1.0
    cumulative_crystalloid_input_mL: float = 0.0
    lactate: float  = 1.0    # [mmol/L] lattato

    # --- iNO ---
    ino_ppm:             float = 0.0    # [ppm] dose iNO impostata
    ino_PVR_mod:         float = 1.0   # moltiplicatore PVR da iNO
    ino_Qs_Qt_mod:       float = 1.0   # moltiplicatore shunt da iNO
    ino_pulmonary_vasodilation_signal: float = 0.0
    ino_oxygenation_signal: float = 0.0
    ino_rebound_risk_signal: float = 0.0

    # --- STEROIDI ---
    hydrocortisone_mg_kg_h:  float = 0.0
    dexamethasone_mcg_kg_h:  float = 0.0
    C_hydrocort_mcg_mL:  float = 0.0
    C_dexa_ng_mL:        float = 0.0
    steroid_SVR_mod:     float = 1.0
    steroid_SIRS_mod:    float = 1.0
    steroid_glucose_add: float = 0.0
    steroid_ICP_mod:     float = 1.0
    hydrocortisone_adrenal_support_signal: float = 0.0
    hydrocortisone_vasopressor_sensitization_signal: float = 0.0
    hydrocortisone_antiinflammatory_signal: float = 0.0
    dexamethasone_antiinflammatory_signal: float = 0.0
    dexamethasone_ICP_edema_signal: float = 0.0
    steroid_glucose_signal: float = 0.0
    steroid_delayed_effect_signal: float = 0.0

    # --- TRASFUSIONE ---
    INR:                 float = 1.0
    PLT_count:           float = 200.0  # ×10^9/L
    fibrinogen:          float = 2.5    # g/L
    d_dimer:             float = 0.3    # mg/L FEU
    AT3:                 float = 100.0  # %
    coag_score:          int   = 0
    GRC_units_given:     int   = 0
    FFP_mL_given:        float = 0.0
    PLT_units_given:     int   = 0

    # --- v0.21 EMATOLOGIA / OXYGEN TRANSPORT ---
    Hct_percent:          float = 33.0   # [%] ematocrito stimato
    RBC_million_uL:       float = 4.0    # [10^6/µL] emazie stimate
    WBC_count:            float = 8.0    # [×10^9/L]
    neutrophil_count:     float = 5.0    # [×10^9/L]
    lymphocyte_count:     float = 2.2    # [×10^9/L]
    reticulocyte_percent: float = 1.0    # [%]
    anemia_severity_index: float = 0.0   # [0-1]
    oxygen_carrying_capacity_mL_dL: float = 14.5
    oxygen_transport_reserve: float = 1.0
    transfusion_trigger_score: float = 0.0
    bleeding_risk_index:  float = 0.0
    thrombosis_risk_index: float = 0.0
    hemolysis_index:      float = 0.0
    LDH_index:            float = 0.0
    indirect_bilirubin_mg_dL: float = 0.4
    methemoglobin_percent: float = 0.5
    marrow_suppression_index: float = 0.0
    platelet_function_index: float = 1.0
    heme_severity_score:  float = 0.0
    bleeding_rate_mL_h:   float = 0.0
    transfusion_strategy: str   = "restrictive"
    transfusion_threshold_Hb: float = 7.0
    RBC_transfused_mL:    float = 0.0
    GRC_pending_mL:       float = 0.0
    FFP_pending_mL:       float = 0.0
    PLT_pending_units:    int   = 0
    fibrinogen_pending_g: float = 0.0

    # --- v0.22 FEGATO / HEPATIC METABOLISM ---
    hepatic_perfusion_index: float = 1.0
    hepatic_hypoxic_injury_index: float = 0.0
    hepatocellular_injury_index: float = 0.0
    cholestasis_index: float = 0.0
    bilirubin_total_mg_dL: float = 0.5
    bilirubin_direct_mg_dL: float = 0.15
    bilirubin_indirect_mg_dL: float = 0.35
    AST_U_L: float = 35.0
    ALT_U_L: float = 25.0
    albumin_g_dL: float = 3.8
    oncotic_pressure_proxy: float = 1.0
    hepatic_lactate_clearance_mod: float = 1.0
    hepatic_drug_clearance_mod: float = 1.0
    hepatic_INR_contribution: float = 0.0
    ammonia_umol_L: float = 35.0
    hepatic_encephalopathy_index: float = 0.0
    hepatic_severity_score: float = 0.0
    liver_SOFA_proxy: int = 0
    hepatic_fluid_leak_mod: float = 1.0

    # --- GLUCOSIO / NUTRIZIONE ---
    GIR_mg_kg_min:           float = 4.0
    insulin_UI_h:            float = 0.0
    glucose_mmol_L:          float = 5.0
    glucose_hypoglycemia:    bool  = False
    glucose_hyperglycemia:   bool  = False
    caloric_balance_kcal_h:  float = 0.0
    # v1.16 insulin PK/PD scaffold outputs
    C_insulin_mU_L:          float = 0.0
    insulin_glucose_clearance_signal: float = 0.0
    insulin_potassium_shift_signal: float = 0.0
    insulin_hypoglycemia_risk: float = 0.0
    insulin_effect_revision: int = 319
    insulin_effective_clearance_mmol_L_h: float = 0.0
    insulin_effective_potassium_shift_mmol_L_h: float = 0.0
    insulin_glucose_safety_factor: float = 1.0
    insulin_potassium_safety_factor: float = 1.0
    insulin_action_signal: float = 0.0
    respiratory_quotient:    float = 0.85   # [-] substrate-dependent RQ used by gas exchange
    VCO2_mod:                float = 1.0    # multiplier for CO2 production from nutrition/RQ


    # --- v0.23 NUTRITION / CATABOLISM ---
    enteral_feed_mL_h: float = 0.0
    enteral_kcal_mL: float = 1.0
    parenteral_kcal_kg_day: float = 0.0
    protein_g_kg_day: float = 0.8
    lipid_g_kg_day: float = 0.0
    energy_intake_kcal_day: float = 0.0
    energy_expenditure_kcal_day: float = 0.0
    energy_balance_kcal_day: float = 0.0
    cumulative_energy_balance_kcal: float = 0.0
    protein_intake_g_day: float = 0.0
    protein_requirement_g_day: float = 0.0
    protein_balance_g_day: float = 0.0
    cumulative_protein_balance_g: float = 0.0
    catabolism_index: float = 0.0
    nitrogen_balance_proxy: float = 0.0
    malnutrition_index: float = 0.0
    feeding_intolerance_index: float = 0.0
    refeeding_risk_index: float = 0.0
    phosphate_mmol_L: float = 1.35
    magnesium_mmol_L: float = 0.82
    phosphate_supplement_mmol: float = 0.0
    magnesium_supplement_mmol: float = 0.0
    triglycerides_mmol_L: float = 1.0
    CRRT_protein_loss_g_day: float = 0.0
    nutrition_albumin_mod: float = 1.0
    nutrition_severity_score: float = 0.0

    # --- NEUROLOGIA / ICP ---
    ICP_mmHg:        float = 10.0
    CPP_mmHg:        float = 55.0
    CBF_relative:    float = 1.0
    V_blood_cc:      float = 100.0
    PbtO2_mmHg:      float = 25.0
    cushing_active:  bool  = False
    ICP_alert:       bool  = False

    # --- v0.25 NEUROFUNCTIONAL / CONSCIOUSNESS ---
    GCS_proxy: float = 15.0
    AVPU_state: str = "A"
    consciousness_index: float = 0.0          # [0-1] depressione stato coscienza
    encephalopathy_index: float = 0.0         # [0-1] encefalopatia globale
    septic_encephalopathy_index: float = 0.0  # [0-1]
    metabolic_encephalopathy_index: float = 0.0
    hypoxic_ischemic_neuro_index: float = 0.0
    seizure_risk_index: float = 0.0
    delirium_state_index: float = 0.0
    withdrawal_state_index: float = 0.0
    cerebral_metabolic_rate_mod: float = 1.0
    neuro_resp_drive_mod: float = 1.0
    neuro_HR_add: float = 0.0
    neuro_sympathetic_mod: float = 1.0
    neuro_severity_score: float = 0.0
    neuro_alert: bool = False
    RASS_proxy: float = 0.0                   # [-5,+4] qualitativo
    seizure_treatment_effect: float = 0.0


    # --- CARDIOVASCOLARE BEAT-TO-BEAT ---
    P_lv_t:          float = 5.0      # [mmHg] pressione LV istantanea
    P_rv_t:          float = 2.0      # [mmHg] pressione RV istantanea
    V_lv_t:          float = 55.0     # [mL]   volume LV istantaneo
    V_rv_t:          float = 60.0     # [mL]   volume RV istantaneo
    cardiac_phase:   str   = "FILL"   # IVC|EJECT|IVR|FILL
    P_la:            float = 8.0      # [mmHg] pressione atriale sx
    P_ra:            float = 3.0      # [mmHg] pressione atriale dx
    Q_ao:            float = 0.0      # [mL/s] flusso aortico istantaneo
    Q_pul:           float = 0.0      # [mL/s] flusso polmonare
    Q_mitral:        float = 0.0      # [mL/s] flusso transmitralico
    dPdt_max:        float = 0.0      # [mmHg/s] dP/dt max (contrattilità)
    dPdt_min:        float = 0.0      # [mmHg/s] dP/dt min (lusitropismo)
    Tau_relax:       float = 0.05     # [s] costante rilassamento isovolum.
    LVEDP:           float = 4.0      # [mmHg] pressione telediastolica LV
    LVESV:           float = 18.3     # [mL]   volume telesistolico LV
    Ea:              float = 1.7      # [mmHg/mL] elastanza arteriosa eff.
    VAC:             float = 1.0      # [-] coupling ventricolo-arterioso
    SW_lv:           float = 0.0      # [mJ] stroke work LV
    PVA_lv:          float = 0.0      # [mJ] pressure-volume area
    MVO2_lv:         float = 8.0      # [mL/min] consumo O2 miocardico
    vent_mode:           str   = "PCV"     # VCV|PCV|PSV|SIMV|CPAP|HFOV
    Vt_set_mL:          float = 150.0     # [mL] volume tidal impostato (VCV)
    Pinsp_cmH2O:        float = 20.0      # [cmH2O] pressione inspiratoria (PCV)
    PS_cmH2O:           float = 10.0      # [cmH2O] pressure support (PSV)
    IE_ratio:           float = 0.40      # T_insp/T_ciclo
    T_rise_s:           float = 0.08      # [s] rise time
    trigger_thresh:     float = 2.0       # [cmH2O] soglia trigger
    cycling_frac:       float = 0.25      # PSV cycling fraction
    # HFOV
    HFOV_freq_Hz:       float = 10.0
    HFOV_amplitude:     float = 30.0
    MAP_hfov:           float = 18.0
    # Monitoraggio ventilatore
    Paw_current:        float = 5.0       # [cmH2O] Paw istantanea
    Paw_mean:           float = 5.0       # [cmH2O] pressione media stimata su ciclo respiratorio
    Paw_display:        float = 5.0       # [cmH2O] valore stabile per monitor numerico/CLI
    Flow_current_mL_s:  float = 0.0       # [mL/s] flow istantaneo
    Ppeak:              float = 0.0        # [cmH2O] picco pressione ciclo
    Pplat:              float = 0.0        # [cmH2O] pressione plateau
    auto_PEEP:          float = 0.0        # [cmH2O] PEEP intrinseca
    patient_triggered:  bool  = False
    RR_total:           float = 25.0       # [/min] RR totale (set + spontanei)
    MV_L_min:           float = 0.0        # [L/min] ventilazione minuto
    compliance_dyn:     float = 0.0        # [mL/cmH2O] compliance dinamica
    resistance_meas:    float = 0.0        # [cmH2O/L/s] resistenza misurata
    alarm_active:       bool  = False
    osmo_active:         bool  = False   # osmoterapia attiva
    csf_drain_mL_h:      float = 0.0    # drenaggio CSF [mL/h]
    norad_mcg_kg_min:    float = 0.0
    ketamine_mg_kg_h:    float = 0.0
    milrinone_mcg_kg_min: float = 0.0
    midazolam_mcg_kg_h:  float = 0.0
    propofol_mg_kg_h:    float = 0.0
    rocuronium_mg_kg_h:  float = 0.0
    # v1.08 priority PICU drugs (public, educational PK/PD placeholders)
    adrenaline_mcg_kg_min: float = 0.0
    dopamine_mcg_kg_min:   float = 0.0
    paracetamol_active:  bool  = False

    # Concentrazioni plasmatiche PK
    C_ketamine_mg_L:     float = 0.0
    C_norad_ng_mL:       float = 0.0
    C_midazolam_ng_mL:   float = 0.0
    C_propofol_mg_L:     float = 0.0
    C_rocuronium_ng_mL:  float = 0.0
    C_adrenaline_ng_mL:  float = 0.0
    C_dopamine_ng_mL:    float = 0.0
    C_insulin_mU_L:      float = 0.0

    # Audit scaling PK v1.01 — trasparenza profilo/peso/maturazione
    pk_scaling_weight_kg: float = 20.0
    pk_scaling_age_y: float = 6.0
    pk_scaling_maturation_factor: float = 1.0
    pk_scaling_revision: int = 101
    pk_extension_revision: int = 0
    pk_supported_drug_count: int = 5
    pk_crrt_revision: int = 0
    pk_crrt_active: bool = False
    pk_crrt_effluent_L_min: float = 0.0
    pk_crrt_total_extra_clearance_L_min: float = 0.0
    pk_crrt_midazolam_CL_L_min: float = 0.0
    pk_crrt_rocuronium_CL_L_min: float = 0.0
    pk_crrt_insulin_CL_L_min: float = 0.0

    # Modificatori PD (applicati dai moduli downstream)
    drug_MAP_mod:        float = 1.0
    drug_HR_mod:         float = 1.0
    drug_drive_mod:      float = 1.0
    drug_SVR_mod:        float = 1.0
    drug_NMB_frac:       float = 0.0
    drug_inotropy_mod:   float = 1.0

    # Step 3.5 audit signals for neuromuscular blockade/paralysis
    rocuronium_nmb_signal: float = 0.0
    neuromuscular_blockade_active: bool = False
    spontaneous_effort_available: float = 1.0
    nmb_trigger_block_active: bool = False

    # Step 3.4B audit signals for GABA sedatives (educational, non-clinical)
    midazolam_sedation_signal: float = 0.0
    midazolam_vasodilation_signal: float = 0.0
    propofol_sedation_signal: float = 0.0
    propofol_vasodilation_signal: float = 0.0
    gaba_sedation_signal: float = 0.0
    sedative_drive_depression_signal: float = 0.0
    sedation_non_gaba_resp_signal: float = 0.0
    ketamine_analgesia_signal: float = 0.0
    ketamine_dissociation_signal: float = 0.0
    ketamine_resp_depression_signal: float = 0.0
    ketamine_sympathomimetic_signal: float = 0.0
    ketamine_hemodynamic_support_signal: float = 0.0

    # --- METABOLISMO ---
    setpoint_T:          float = 37.0   # [°C] setpoint termico
    GFR:                 float = 70.0   # [mL/min] filtrazione glomerulare
    urine_rate_mL_h:     float = 22.0   # [mL/h] diuresi
    AKI_index:           float = 0.0    # [0-1] indice danno renale
    fluid_CVP_correction: float = 0.0  # [mmHg] correzione CVP da fluidi

    # --- v0.11 PHYSIOLOGY QUALITY / INTERACTIONS ---
    patient_profile:       str   = "child_20kg"
    age_group:             str   = "child"
    blood_volume_mL:       float = 1600.0
    fluid_responsiveness:  float = 0.6    # [0-1] risposta attesa ai fluidi
    preload_reserve:       float = 0.6    # [0-1] riserva di Frank-Starling
    # v1.05 cardiovascular pediatric scaling audit fields
    cv_scaling_weight_kg:  float = 20.0
    cv_scaling_profile:    str   = "child_20kg"
    cv_scaling_revision:   str   = "pre-v1.05"
    cv_EDV0_lv_ref:        float = 55.0
    cv_Emax_lv_ref:        float = 5.10
    cv_R_systemic_ref:     float = 1.060
    capillary_leak_index:  float = 0.0    # [0-1] quota di leak/sepsi
    venous_return_mod:     float = 1.0    # moltiplicatore ritorno venoso
    heart_lung_CO_mod:     float = 1.0    # effetto Paw/PEEP/RV su CO
    RV_afterload_index:    float = 0.0    # [0-1] carico RV da PVR/Paw/ipossia
    overdistension_index:  float = 0.0    # [0-1]
    atelectrauma_index:    float = 0.0    # [0-1]
    VILI_risk:             float = 0.0    # [0-1] indice composito qualitativo
    PEEP_hemodynamic_penalty: float = 0.0 # [0-1]
    vasoactive_SVR_mod:    float = 1.0    # v3.1 Step 3.3: primary vasoactive vascular tone
    vasoactive_CO_mod:     float = 1.0    # v3.1 Step 3.3: direct non-PK inodilator CO effect

    # v3.1 Step 4.43 advanced vasoactive engine audit fields
    vasoactive_engine_revision: int = 0
    vasoactive_alpha1_signal: float = 0.0
    vasoactive_beta1_signal: float = 0.0
    vasoactive_beta2_signal: float = 0.0
    vasoactive_v1_signal: float = 0.0
    vasoactive_pde3_signal: float = 0.0
    vasoactive_effective_norad: float = 0.0
    vasoactive_effective_adrenaline: float = 0.0
    vasoactive_effective_dopamine: float = 0.0
    vasoactive_effective_milrinone: float = 0.0
    vasoactive_effective_vasopressin: float = 0.0
    vasoactive_tachyphylaxis_index: float = 0.0
    vasoactive_hysteresis_index: float = 0.0
    vasoactive_interaction_index: float = 0.0
    vasoactive_HR_mod: float = 1.0
    vasoactive_inotropy_mod: float = 1.0



    # --- v0.12 PAIN / STRESS / ANALGOSEDATION ---
    pain_score:            float = 2.0    # [0-10] dolore/procedural stress
    stress_index:          float = 0.10   # [0-1] drive neuroendocrino complessivo
    sedation_score:        float = 0.0    # [0-1] profondità sedazione composita
    analgesia_score:       float = 0.0    # [0-1] analgesia composita
    sympathetic_tone:      float = 1.0    # moltiplicatore simpatico su HR/SVR/VO2
    delirium_risk:         float = 0.05   # [0-1] rischio qualitativo delirium
    withdrawal_risk:       float = 0.00   # [0-1] rischio qualitativo withdrawal
    sed_resp_mod:          float = 1.0    # moltiplicatore drive respiratorio da analgosedazione
    sed_VO2_mod:           float = 1.0    # moltiplicatore VO2 da sedazione/stress
    sed_HR_mod:            float = 1.0    # moltiplicatore HR da stress/farmaci sedativi
    sed_SVR_mod:           float = 1.0    # moltiplicatore SVR da stress/farmaci sedativi
    opioid_resp_depression: float = 0.0   # [0-1] depressione respiratoria da oppioidi
    opioid_analgesia_signal: float = 0.0  # [0-1] analgesia oppioide composita
    C_fentanyl_ng_mL:      float = 0.0
    C_remifentanil_ng_mL:  float = 0.0
    C_morphine_ng_mL:      float = 0.0
    fentanyl_analgesia_signal: float = 0.0
    fentanyl_resp_depression_signal: float = 0.0
    remifentanil_analgesia_signal: float = 0.0
    remifentanil_resp_depression_signal: float = 0.0
    morphine_analgesia_signal: float = 0.0
    morphine_resp_depression_signal: float = 0.0
    morphine_renal_accumulation_risk: float = 0.0
    M6G_accumulation_proxy: float = 0.0
    C_dexmedetomidine_ng_mL: float = 0.0
    C_clonidine_ng_mL:     float = 0.0
    dexmedetomidine_sedation_signal: float = 0.0
    dexmedetomidine_sympatholysis_signal: float = 0.0
    dexmedetomidine_bradycardia_risk: float = 0.0
    dexmedetomidine_hypotension_risk: float = 0.0
    alpha2_sedation_signal: float = 0.0
    alpha2_sympatholysis_signal: float = 0.0
    alpha2_resp_depression_signal: float = 0.0
    clonidine_sedation_signal: float = 0.0
    clonidine_sympatholysis_signal: float = 0.0
    clonidine_bradycardia_risk: float = 0.0
    clonidine_hypotension_risk: float = 0.0
    clonidine_withdrawal_mod: float = 0.0
    C_vancomycin_mg_L:     float = 0.0
    C_furosemide_mg_L:     float = 0.0
    C_piperacillin_mg_L:   float = 0.0
    piperacillin_ft_above_MIC: float = 0.0
    piperacillin_target_attainment: float = 0.0
    piperacillin_kill_signal: float = 0.0
    piperacillin_coverage_mod: float = 0.0
    piperacillin_renal_clearance_factor: float = 1.0
    piperacillin_MIC_mg_L: float = 16.0
    furosemide_effect_signal: float = 0.0
    furosemide_diuresis_signal: float = 0.0
    furosemide_effective_diuretic_signal: float = 0.0
    furosemide_tubular_delivery_factor: float = 1.0
    furosemide_urine_gain: float = 1.0
    furosemide_additional_urine_mL_h: float = 0.0
    diuretic_hypovolemia_risk: float = 0.0
    furosemide_renal_clearance_factor: float = 1.0
    vancomycin_target_attainment: float = 0.0
    vancomycin_coverage_mod: float = 0.0
    vancomycin_renal_clearance_factor: float = 1.0
    fentanyl_mcg_kg_h:     float = 0.0
    remifentanil_mcg_kg_min: float = 0.0
    morphine_mcg_kg_h:     float = 0.0
    dexmedetomidine_mcg_kg_h: float = 0.0
    clonidine_mcg_kg_h:    float = 0.0
    vancomycin_mg_kg_h:    float = 0.0
    furosemide_mg_kg_h:    float = 0.0
    piperacillin_mg_kg_h:  float = 0.0

    # --- v0.13 AIRWAY OBSTRUCTION / ASTHMA / BRONCHIOLITIS ---
    airway_obstruction_index: float = 0.0   # [0-1] burden ostruttivo complessivo
    bronchospasm_index:      float = 0.0   # [0-1] broncospasmo reversibile
    mucus_load:              float = 0.0   # [0-1] tappi/edema/muco
    small_airway_obstruction: float = 0.0  # [0-1] componente bronchiolite/small airways
    air_trapping_index:      float = 0.0   # [0-1] intrappolamento dinamico
    dynamic_hyperinflation:  float = 0.0   # [0-1] iperinflazione dinamica qualitativa
    airway_resistance_mod:   float = 1.0   # moltiplicatore Rrs da ostruzione
    airway_VdVt_add:         float = 0.0   # dead-space additivo da ostruzione
    airway_shunt_add:        float = 0.0   # shunt/VQ additivo da mucus/atelettasia
    expiratory_time_constant_s: float = 0.35 # [s] tau espiratoria R*C
    auto_PEEP_obstructive:   float = 0.0   # [cmH2O] PEEP intrinseca da ostruzione
    bronchodilator_effect:   float = 0.0   # [0-1] effetto broncodilatatore complessivo
    salbutamol_mcg_kg_min:   float = 0.0
    ipratropium_mcg_kg_h:    float = 0.0
    magnesium_mg_kg_h:       float = 0.0
    nebulized_epinephrine_mcg_kg_min: float = 0.0
    salbutamol_bronchodilation_signal: float = 0.0
    salbutamol_tachycardia_signal: float = 0.0
    ipratropium_bronchodilation_signal: float = 0.0
    magnesium_bronchodilation_signal: float = 0.0
    nebulized_epinephrine_bronchodilation_signal: float = 0.0
    nebulized_epinephrine_upper_airway_relief_signal: float = 0.0
    nebulized_epinephrine_tachycardia_signal: float = 0.0
    upper_airway_relief_signal: float = 0.0
    bronchodilator_HR_mod: float = 1.0



    # --- v0.26 INFECTION / ANTIMICROBIAL BASIC ---
    microbial_burden: float = 0.0
    pathogen_virulence: float = 0.45
    pathogen_resistance_index: float = 0.15
    infection_focus: str = "unknown"
    antibiotic_started: bool = False
    antibiotic_coverage: float = 0.0
    antibiotic_delay_harm_index: float = 0.0
    antimicrobial_kill_rate: float = 0.0
    infection_resolution_rate: float = 0.0
    culture_drawn: bool = False
    culture_positive: bool = False
    culture_positivity_probability: float = 0.0
    source_control_need_index: float = 0.0
    antimicrobial_escalation_score: float = 0.0
    antimicrobial_deescalation_readiness: float = 0.0
    inadequate_coverage_index: float = 0.0
    infection_severity_score: float = 0.0
    procalcitonin_proxy: float = 0.0
    CRP_proxy: float = 0.0
    infection_fever_drive: float = 0.0
    infection_lactate_mod: float = 1.0

    # --- v0.31 OWNER/MODIFIER LEDGER FIELDS ---
    # These fields support owner-only writes for variables that used to be
    # overwritten by multiple modules. Modifying modules should write here;
    # the owner module applies the effect to the final physiological variable.
    external_fluid_input_mL: float = 0.0        # [mL] cumulative non-maintenance fluid input ledger
    CRRT_UF_mL_h_effective: float = 0.0         # [mL/h] effective net UF suggested by AKI/CRRT
    CRRT_K_target_mmol_L: float = 4.0           # [mmol/L] electrolyte target suggested by CRRT
    CRRT_HCO3_target_mmol_L: float = 24.0       # [mmol/L] bicarbonate target suggested by CRRT
    CRRT_lactate_target_mmol_L: float = 1.0     # [mmol/L] lactate target suggested by CRRT
    owner_modifier_revision: int = 31           # schema marker for v0.31 refactor
    residual_owner_modifier_revision: int = 35  # schema marker for v0.35 residual writer refactor

    # --- v3.1 Step 4.39 SHOCK ENGINE ---
    shock_engine_revision: int = 439
    shock_type: str = "none"                 # none|distributive|hypovolemic|cardiogenic|obstructive|mixed
    shock_severity: float = 0.0              # [0-1] composite educational shock burden
    shock_stage: str = "none"                # none|compensated|decompensated|critical
    shock_SVR_mod: float = 1.0               # disease-level systemic vascular tone modifier
    shock_preload_mod: float = 1.0           # venous-return/preload modifier
    shock_contractility_mod: float = 1.0     # myocardial contractility modifier
    shock_HR_add: float = 0.0                # additive sympathetic tachycardia proxy [bpm]
    shock_lactate_prod_mod: float = 1.0      # lactate production multiplier
    shock_lactate_clearance_mod: float = 1.0 # lactate clearance multiplier
    shock_sympathetic_tone: float = 1.0      # compensatory sympathetic activation proxy
    shock_decompensation_index: float = 0.0  # [0-1] pressure/perfusion failure marker
    shock_obstruction_index: float = 0.0     # [0-1] tamponade/tension/PE load proxy
    shock_hypovolemia_index: float = 0.0     # [0-1] effective intravascular depletion proxy
    shock_vasoplegia_index: float = 0.0      # [0-1] vasodilatory shock proxy
    shock_low_output_index: float = 0.0      # [0-1] cardiogenic/obstructive low-flow proxy
    shock_perfusion_pressure_mmHg: float = 60.0 # MAP-CVP proxy

    # --- v3.1 Step 4.42 ORGAN PERFUSION MODEL ---
    organ_perfusion_revision: int = 0
    organ_perfusion_pressure_mmHg: float = 60.0
    pediatric_MAP_low_threshold_mmHg: float = 55.0
    renal_perfusion_index: float = 1.0
    hepatic_hypoperfusion_index: float = 0.0
    organ_hypoperfusion_burden: float = 0.0
    organ_lactate_clearance_mod: float = 1.0
    GFR_mod_from_perfusion: float = 1.0
    renal_warning: str = "none"
    hepatic_warning: str = "none"
    
    # --- v3.1 Step 4.48 RECOVERY ENGINE ---
    recovery_engine_revision: int = 0
    recovery_engine_active: bool = False
    recovery_phase: str = "not_started"  # not_started|first_response|partial_response|near_baseline
    recovery_first_response_abs_s: float = 0.0
    recovery_partial_response_abs_s: float = 0.0
    recovery_near_baseline_abs_s: float = 0.0
    recovery_requires_corrective_action: bool = True
    recovery_corrective_action_time_s: float = -1.0
    recovery_target_summary: str = ""
    lactate_multiplier: float = 1.0
    organ_perfusion_multiplier: float = 1.0
    SaO2_multiplier: float = 1.0
    PaCO2_multiplier: float = 1.0
    CO_multiplier: float = 1.0

    # --- v3.1 Step 4.40 EPALS-LIKE DECISION ENGINE ---
    decision_engine_revision: int = 440
    decision_priority: str = "routine_monitoring"        # educational priority bucket
    decision_pattern: str = "stable"                     # recognized pattern label
    decision_pattern_confidence: float = 0.0              # [0-1] qualitative rule confidence
    decision_recommendation_primary: str = ""            # instructor-facing primary prompt
    decision_recommendation_secondary: str = ""          # instructor-facing secondary prompt
    decision_warning: str = ""                           # incoherence/omission warning
    decision_warning_level: str = "none"                 # none|low|medium|high|critical
    decision_abcde_step: str = "E"                       # A|B|C|D|E or combined priority
    decision_escalation_needed: bool = False              # simulation escalation flag
    decision_context_flags: str = ""                     # comma-separated context flags
    decision_last_update_s: float = 0.0                   # [s] last decision refresh

    # --- v0.14 ADVANCED SEPSIS / SHOCK PHENOTYPES ---
    infection_load:         float = 0.0    # [0-1] burden infettivo/infiammatorio
    source_control:         float = 0.0    # [0-1] efficacia source control
    antibiotic_effect:      float = 0.0    # [0-1] effetto antimicrobico globale
    sepsis_phenotype_code:  str   = "none" # warm|cold|mixed|vasoplegic|myocardial
    cytokine_drive:         float = 0.0
    vasoplegia_index:       float = 0.0
    myocardial_depression_index: float = 0.0
    endothelial_leak_index: float = 0.0
    microcirculatory_failure_index: float = 0.0
    sepsis_SVR_mod:         float = 1.0
    sepsis_CO_mod:          float = 1.0
    sepsis_HR_add:          float = 0.0
    sepsis_VO2_mod:         float = 1.0
    sepsis_lactate_prod_mod: float = 1.0
    sepsis_GFR_mod:         float = 1.0
    sepsis_coag_mod:        float = 1.0
    sepsis_severity_score:  float = 0.0
    vasopressin_mU_kg_min: float = 0.0

    # --- v0.17 ACID-BASE / ELECTROLYTES ---
    Na_mmol_L:             float = 138.0
    K_mmol_L:              float = 4.0
    Cl_mmol_L:             float = 103.0
    HCO3_mmol_L:           float = 24.0
    base_excess_mmol_L:    float = 0.0
    anion_gap_mmol_L:      float = 15.0
    corrected_anion_gap_mmol_L: float = 15.0
    SID_apparent_mmol_L:   float = 39.0
    osmolarity_mOsm_L:     float = 286.0
    urea_mmol_L:           float = 5.0
    acid_base_status:      str   = "near_normal"
    metabolic_acidosis_index: float = 0.0
    respiratory_acidosis_index: float = 0.0
    hyperchloremia_index:  float = 0.0
    hypokalemia_index:     float = 0.0
    hyperkalemia_index:    float = 0.0
    normal_saline_mL:      float = 0.0    # cumulative 0.9% saline load
    balanced_crystalloid_mL: float = 0.0  # cumulative balanced crystalloid load
    bicarbonate_mmol:      float = 0.0    # cumulative sodium bicarbonate dose
    hypertonic_saline_3pct_mL: float = 0.0
    potassium_mmol:        float = 0.0    # cumulative potassium supplement
    calcium_given:         bool  = False    # educational hyperkalemia membrane-stabilization marker
    diuretic_effect:       float = 0.0

    # --- v0.18 AKI / CRRT-LITE ---
    creatinine_mg_dL:       float = 0.35
    creatinine_baseline_mg_dL: float = 0.35
    creatinine_ratio:       float = 1.0
    AKI_stage:              int   = 0
    urine_output_mL_kg_h:   float = 1.0
    fluid_overload_percent: float = 0.0
    diuretic_response_index: float = 0.0
    furosemide_mg_kg:       float = 0.0    # cumulative dose counter
    CRRT_active:            bool  = False
    CRRT_effluent_mL_kg_h:  float = 0.0
    CRRT_net_UF_mL_h:       float = 0.0
    CRRT_dialysate_K_mmol_L: float = 4.0
    CRRT_bicarbonate_mmol_L: float = 32.0
    CRRT_anticoagulation:   str   = "none"
    CRRT_active_effective:  float = 0.0
    CRRT_clearance_mod:     float = 0.0
    GFR_baseline:           float = 70.0
    RRT_indication_score:   float = 0.0
    renal_severity_score:   float = 0.0
    pk_crrt_vancomycin_CL_L_min: float = 0.0
    pk_crrt_furosemide_CL_L_min: float = 0.0
    pk_crrt_morphine_CL_L_min: float = 0.0
    pk_crrt_clonidine_CL_L_min: float = 0.0
    pk_crrt_insulin_CL_L_min: float = 0.0
    pk_crrt_piperacillin_CL_L_min: float = 0.0


    # --- v0.19 ENDOCRINE / STRESS AXIS ---
    cortisol_activity:       float = 0.22   # [0-1] HPA/glucocorticoid activity
    catecholamine_tone:      float = 0.18   # [0-1] endogenous stress catecholamine tone
    HPA_axis_activation:     float = 0.22
    adrenal_insufficiency_index: float = 0.0
    critical_illness_steroid_need_index: float = 0.0
    insulin_resistance_index: float = 0.0
    stress_hyperglycemia_index: float = 0.0
    endocrine_glucose_prod_mod: float = 1.0
    insulin_sensitivity_mod: float = 1.0
    endocrine_SVR_mod:      float = 1.0
    endocrine_HR_add:       float = 0.0
    endocrine_VO2_mod:      float = 1.0
    endocrine_lactate_mod:  float = 1.0
    ADH_water_retention_index: float = 0.0
    endocrine_GFR_mod:      float = 1.0
    thyroid_suppression_index: float = 0.0
    endocrine_severity_score: float = 0.0

    def copy(self) -> "BusState":
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# Bus principale
# ---------------------------------------------------------------------------

class PhysiologicalBus:
    """
    Bus fisiologico centralizzato.
    
    Mantiene lo stato corrente e la storia completa della simulazione.
    I moduli chiamano bus.get() per leggere e bus.set() per scrivere.
    """

    def __init__(self, initial_state: BusState | None = None):
        self.state: BusState = initial_state if initial_state else BusState()
        self.history: List[BusState] = []
        self._dt: float = 0.01  # timestep default [s]

    # --- API lettura/scrittura ---

    def get(self, key: str) -> Any:
        """Legge una variabile dal Bus."""
        return getattr(self.state, key)

    def set(self, key: str, value: Any) -> None:
        """Scrive una variabile nel Bus."""
        if not hasattr(self.state, key):
            raise KeyError(f"BusState non ha il campo '{key}'. "
                           f"Aggiungilo a BusState prima di usarlo.")
        setattr(self.state, key, value)

    def update(self, updates: Dict[str, Any]) -> None:
        """Aggiornamento batch: dict {key: value}."""
        for k, v in updates.items():
            self.set(k, v)

    def snapshot(self) -> None:
        """Salva lo stato corrente nella history."""
        self.history.append(self.state.copy())

    def get_timeseries(self, key: str) -> np.ndarray:
        """Estrae la serie temporale di una variabile dalla history."""
        return np.array([getattr(s, key) for s in self.history])

    def get_time(self) -> np.ndarray:
        """Array dei tempi dalla history."""
        return np.array([s.t for s in self.history])

    def reset_history(self) -> None:
        self.history.clear()

    def __repr__(self) -> str:
        s = self.state
        return (f"PhysiologicalBus [t={s.t:.1f}s | "
                f"Paw={s.Paw:.1f} cmH2O | SaO2={s.SaO2*100:.1f}% | "
                f"MAP={s.MAP:.0f} mmHg | CO={s.CO:.2f} L/min]")



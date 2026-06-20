# PDT v1.19 Score Assumption Registry Hardening

This report audits qualitative scores, proxies, risk indices and modifiers.
It is a transparency and software-range check, **not clinical validation**.

Registry version: **v1.19**

## Registry completeness

Score-like BusState variables: **204**
Registered variables: **212**
Entries with numeric ranges: **207**
Missing score-like variables: **0**

## High-priority heuristic variables

| Variable | Module | Hard range | Validation status |
|---|---|---:|---|
| GCS_proxy | NeuroFunctionalModule/ICPModule | 3.0–15.0 | requires expert review and/or external benchmark before scientific use |
| M6G_accumulation_proxy | Pharmacology/PainStressSedationModules | -1000.0–1000.0 | requires expert review and/or external benchmark before scientific use |
| VILI_risk | HeartLung/RespiratoryMechanicsModule | 0.0–1.0 | requires expert review and/or external benchmark before scientific use |
| antibiotic_effect | InfectionAntimicrobialBasicModule | 0.0–1.0 | requires expert review and/or external benchmark before scientific use |
| clonidine_withdrawal_mod | Neurofunctional/PainStressSedationModules | 0.0–5.0 | requires expert review and/or external benchmark before scientific use |
| furosemide_effect_signal | Pharmacology/RenalModules | 0.0–1.0 | requires expert review and/or external benchmark before scientific use |
| hepatic_lactate_clearance_mod | HepaticMetabolismModule | 0.0–5.0 | requires expert review and/or external benchmark before scientific use |
| infection_severity_score | InfectionAntimicrobialBasicModule | 0.0–1.0 | requires expert review and/or external benchmark before scientific use |
| insulin_hypoglycemia_risk | Pharmacology/GlucoseModules | 0.0–1.0 | requires expert review and/or external benchmark before scientific use |
| neuro_severity_score | NeuroFunctionalModule/ICPModule | 0.0–1.0 | requires expert review and/or external benchmark before scientific use |
| piperacillin_ft_above_MIC | Pharmacology/InfectionModules | nan–nan | requires expert review and/or external benchmark before scientific use |
| renal_severity_score | AKICRRTModule/FluidBalanceModule | 0.0–1.0 | requires expert review and/or external benchmark before scientific use |
| sedation_score | PainStressSedationModule | 0.0–1.0 | requires expert review and/or external benchmark before scientific use |
| sepsis_severity_score | AdvancedSepsisModule | 0.0–1.0 | requires expert review and/or external benchmark before scientific use |
| vancomycin_target_attainment | Pharmacology/InfectionModules | 0.0–1.0 | requires expert review and/or external benchmark before scientific use |
| vq_deadspace_frac | RespiratoryGasExchangeModule | 0.0–1.0 | requires expert review and/or external benchmark before scientific use |
| vq_high_vq_burden | RespiratoryGasExchangeModule | 0.0–1.0 | requires expert review and/or external benchmark before scientific use |
| vq_low_vq_burden | RespiratoryGasExchangeModule | 0.0–1.0 | requires expert review and/or external benchmark before scientific use |
| vq_shunt_frac | RespiratoryGasExchangeModule | 0.0–1.0 | requires expert review and/or external benchmark before scientific use |
| withdrawal_risk | PainStressSedationModule | 0.0–1.0 | requires expert review and/or external benchmark before scientific use |
| vq_adaptive_sigma | GasExchangeModule | 0.0–2.0 | internal plausibility only; not externally validated |

## Scenario range audit

PASS cells: **616**  
REVIEW cells: **5**  
FAIL cells: **0**  

| Scenario | PASS | REVIEW | FAIL | NOT_PRESENT |
|---|---:|---:|---:|---:|
| healthy_child_20kg | 206 | 1 | 0 | 0 |
| ards_mild | 205 | 2 | 0 | 0 |
| picu_insulin_stress_hyperglycemia_v1_16 | 205 | 2 | 0 | 0 |

### First REVIEW/FAIL cells

| Scenario | Variable | Min | Max | Expected | Hard | Status |
|---|---|---:|---:|---:|---:|---|
| healthy_child_20kg | drive_level | 1 | 2.5 | 0.0–2.0 | 0.0–3.0 | REVIEW |
| ards_mild | drive_level | 1 | 2.314 | 0.0–2.0 | 0.0–3.0 | REVIEW |
| ards_mild | hepatic_perfusion_index | 0.2863 | 1 | 0.3–1.5 | 0.0–2.0 | REVIEW |
| picu_insulin_stress_hyperglycemia_v1_16 | drive_level | 1 | 2.248 | 0.0–2.0 | 0.0–3.0 | REVIEW |
| picu_insulin_stress_hyperglycemia_v1_16 | EtCO2_proxy | 35 | 81.29 | 15.0–80.0 | 0.0–150.0 | REVIEW |
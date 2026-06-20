# v3.1 Step 3.4D — Alpha-2 agonist response contract

Educational/research alpha only. Not for clinical use. Not a medical device.

## Scope

This step is intentionally limited to the alpha-2 agonists:

- dexmedetomidine
- clonidine

It does not modify rocuronium, the ventilator, hemodynamic waveforms, Docker packaging, opioids, GABA sedatives, ketamine, or vasoactive drug logic.

## Problem identified

Before Step 3.4D, dexmedetomidine and clonidine could suppress respiratory drive and hemodynamics through more than one path:

- `PharmacologyModule.drug_drive_mod`
- `PainStressSedationModule.sed_resp_mod`
- `PharmacologyModule.drug_HR_mod` / `drug_SVR_mod`
- `PainStressSedationModule.sed_HR_mod` / `sed_SVR_mod`

This made alpha-2 agonists look too similar to GABA sedatives/opioids and made the HR/SVR response harder to interpret.

## Change made

Step 3.4D assigns single ownership:

- `PharmacologyModule` owns alpha-2 PK concentrations and audit signals.
- `PainStressSedationModule` owns cooperative sedation and sympatholysis coupling.
- Alpha-2 agonists no longer reduce `drug_drive_mod`.
- Alpha-2 agonists no longer reduce `drug_HR_mod` or `drug_SVR_mod` directly.
- Respiratory drive remains preserved unless another drug class or NMB is present.

## New/clarified audit signals

- `dexmedetomidine_sedation_signal`
- `dexmedetomidine_sympatholysis_signal`
- `dexmedetomidine_bradycardia_risk`
- `dexmedetomidine_hypotension_risk`
- `alpha2_sedation_signal`
- `alpha2_sympatholysis_signal`
- `alpha2_resp_depression_signal`

Existing clonidine signals are preserved:

- `clonidine_sedation_signal`
- `clonidine_sympatholysis_signal`
- `clonidine_bradycardia_risk`
- `clonidine_hypotension_risk`
- `clonidine_withdrawal_mod`

## Expected behavior

### Dexmedetomidine

Dose increases should produce:

- higher `C_dexmedetomidine_ng_mL`
- higher `dexmedetomidine_sedation_signal`
- higher `dexmedetomidine_sympatholysis_signal`
- lower `sed_HR_mod`
- preserved `drug_drive_mod == 1.0`
- preserved `sed_resp_mod == 1.0` when no opioid/GABA/NMB is present

### Clonidine

Dose increases should produce:

- higher `C_clonidine_ng_mL`
- higher `clonidine_sedation_signal`
- higher `clonidine_sympatholysis_signal`
- higher `clonidine_withdrawal_mod`
- lower `sed_HR_mod`
- preserved primary respiratory drive

## Regression tests

Added:

- `tests/test_v309_alpha2_agonist_response_contract.py`

Tested contracts:

- dexmedetomidine cooperative sedation with preserved primary respiratory drive
- clonidine slow alpha-2 sedation and withdrawal signal
- monotonic dose-response for sedation/sympatholysis
- no duplicate alpha-2 effects in `drug_HR_mod`, `drug_SVR_mod`, or `drug_drive_mod`
- source-level contract markers for Step 3.4D

## Validation run

Targeted tests:

- `test_v309_alpha2_agonist_response_contract.py`
- `test_v308_ketamine_response_contract.py`
- `test_v307_gaba_sedative_response_contract.py`
- `test_v306_opioid_response_contract.py`
- `test_v305_vasoactive_response_contract.py`
- `test_v304_drug_map_mod_direction.py`
- `test_v303_drug_control_surface.py`
- `test_v302_ui_backend_bidirectional.py`
- `test_v301_ui_live_controls.py`
- `test_v210_web_monitor.py`
- `test_v260_ui_polish_tablet.py`
- `test_v200_api_server.py`
- `test_v220_emergency_training_mode.py`
- `test_v230_instructor_mode.py`
- `test_v114_morphine_pkpd.py`
- `test_v115_clonidine_pkpd.py`

Result:

- `33 passed` for the Step 3.4A-D/core control group
- `23 passed` for web/API/legacy morphine-clonidine group
- total targeted validation: `56 passed`

The full slow suite was not run in this step.

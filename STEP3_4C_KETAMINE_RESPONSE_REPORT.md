# Step 3.4C — Ketamine response contract

## Scope

This step only revises ketamine behavior. It does not modify opioids, midazolam, propofol, alpha-2 agonists, rocuronium, the ventilator, Docker, or the graphical arterial waveform.

## Problem

Ketamine already had qualitative analgesic, sedative and hemodynamic effects, but the dissociative-sedation term was included inside the non-GABA respiratory-sedation burden. This made ketamine behave too similarly to respiratory depressants in the UI/monitor contract.

## Changes

- Ketamine remains a PK/PD drug with concentration `C_ketamine_mg_L`.
- Ketamine supports HR/MAP qualitatively through `drug_HR_mod` and `drug_MAP_mod`.
- Ketamine analgesia and dissociative sedation are represented in `PainStressSedationModule`.
- Ketamine is explicitly excluded from primary respiratory-depressant pathways:
  - no direct ketamine reduction of `drug_drive_mod`;
  - no ketamine reduction of `sed_resp_mod`.

## New audit signals

- `ketamine_analgesia_signal`
- `ketamine_dissociation_signal`
- `ketamine_resp_depression_signal`
- `ketamine_sympathomimetic_signal`
- `ketamine_hemodynamic_support_signal`

## Expected behavior

Increasing ketamine infusion should produce:

- increasing `C_ketamine_mg_L`;
- increasing analgesia;
- increasing dissociative sedation;
- lower `pain_score`;
- modest qualitative HR/MAP support;
- preserved respiratory drive compared with GABA sedatives/opioids.

## Tests

Added:

- `tests/test_v308_ketamine_response_contract.py`

Regression command used:

```bash
python -m py_compile modules/pharmacology/pk_pd.py modules/analgosedation/pain_stress_sedation.py core/bus.py
python -m pytest -q \
  tests/test_v308_ketamine_response_contract.py \
  tests/test_v307_gaba_sedative_response_contract.py \
  tests/test_v306_opioid_response_contract.py \
  tests/test_v305_vasoactive_response_contract.py \
  tests/test_v304_drug_map_mod_direction.py \
  tests/test_v303_drug_control_surface.py \
  tests/test_v302_ui_backend_bidirectional.py \
  tests/test_v301_ui_live_controls.py \
  tests/test_v210_web_monitor.py \
  tests/test_v260_ui_polish_tablet.py \
  tests/test_v200_api_server.py \
  tests/test_v220_emergency_training_mode.py \
  tests/test_v230_instructor_mode.py \
  tests/test_v114_morphine_pkpd.py
```

Result: 47 passed.

## Remaining work

Next medication sub-step should be alpha-2 agonists: dexmedetomidine and clonidine.

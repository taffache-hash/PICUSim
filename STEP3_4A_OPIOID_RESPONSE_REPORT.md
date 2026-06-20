# Step 3.4A — Opioid response contract

Scope: fentanyl, morphine and remifentanil only.

## Problem found

Before this step, opioid respiratory depression could be applied through two paths:

1. `PharmacologyModule` reduced `drug_drive_mod` using fentanyl/morphine PD signals.
2. `PainStressSedationModule` also reduced `sed_resp_mod` using fentanyl/remifentanil/morphine opioid respiratory depression.

`ChemoreflexModule` multiplies both `drug_drive_mod` and `sed_resp_mod`, so the same opioid effect could become a double respiratory-drive penalty.

## Decision

- `PharmacologyModule` owns PK concentrations and audit PD signals for fentanyl/morphine.
- `PainStressSedationModule` owns opioid respiratory coupling through `sed_resp_mod` and `opioid_resp_depression`.
- Remifentanil remains local to `PainStressSedationModule` because it is not currently represented in the central Pharmacology PK module.

## New audit signals

- `opioid_analgesia_signal`
- `fentanyl_analgesia_signal`
- `fentanyl_resp_depression_signal`
- `remifentanil_analgesia_signal`
- `remifentanil_resp_depression_signal`

Existing morphine signals are preserved:

- `morphine_analgesia_signal`
- `morphine_resp_depression_signal`
- `morphine_renal_accumulation_risk`
- `M6G_accumulation_proxy`

## Expected behavior

- Higher opioid dose increases analgesia signal.
- Higher opioid dose increases `opioid_resp_depression`.
- Higher opioid dose lowers `sed_resp_mod`.
- `drug_drive_mod` is not reduced by fentanyl/morphine alone.
- Remifentanil has faster offset than fentanyl in the simplified model.

## Tests

Added `tests/test_v306_opioid_response_contract.py`.

Targeted regression pack result: 39 passed.

Full slow suite was not rerun in this step.

# Step 3.4B — GABA sedative response contract

## Scope

This step revises only the educational response contract for midazolam and propofol.
It does not change opioids, ketamine, dexmedetomidine, clonidine, rocuronium, Docker, the web monitor waveform renderer, or the vasoactive cleanup from Step 3.3.

## Problem found

Midazolam and propofol could reduce respiratory drive through two channels at the same time:

1. `PharmacologyModule.drug_drive_mod`
2. `PainStressSedationModule.sed_resp_mod`, because `sed_resp_mod` was derived from total `sedation_score` and total sedation included the GABA sedative component.

The downstream chemorespiratory module multiplies both channels, so the same GABA sedation could be applied twice.

## Change made

GABA sedative respiratory-drive depression is now owned by `PharmacologyModule.drug_drive_mod`.

`PainStressSedationModule.sed_resp_mod` no longer applies total sedation. Instead, it applies opioid respiratory depression and non-GABA respiratory sedation burden. This preserves the Step 3.4A opioid contract and avoids double-counting midazolam/propofol.

## New audit signals

- `midazolam_sedation_signal`
- `midazolam_vasodilation_signal`
- `propofol_sedation_signal`
- `propofol_vasodilation_signal`
- `gaba_sedation_signal`
- `sedative_drive_depression_signal`
- `sedation_non_gaba_resp_signal`

## Expected qualitative behavior

- Midazolam: dose-dependent sedation and respiratory-drive reduction; mild vasodilation; no direct HR effect.
- Propofol: stronger GABA sedation at higher concentrations, respiratory-drive reduction, vasodilation, mild HR reduction signal.
- No opioid-style double respiratory depression for midazolam/propofol.

## Tests

Added `tests/test_v307_gaba_sedative_response_contract.py`.

Targeted regression set passed.

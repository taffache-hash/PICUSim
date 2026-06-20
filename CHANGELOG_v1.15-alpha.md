# CHANGELOG v1.15-alpha

## Added

- Added clonidine as the 13th centralized drug in `PharmacologyModule`.
- Added qualitative PK/PD outputs for clonidine sedation, sympatholysis, bradycardia risk, hypotension risk and withdrawal modulation.
- Added CRRT-lite audit field `pk_crrt_clonidine_CL_L_min`.
- Added `scenarios/picu_clonidine_withdrawal_weaning_v1_15.yaml`.
- Added `tools/pkpd_clonidine_audit_v1_15.py`.
- Added `tests/test_v115_clonidine_pkpd.py`.
- Added `docs/PKPD_CLONIDINE_v1.15.md`.

## Changed

- `PainStressSedationModule` now treats clonidine as centrally owned by `PharmacologyModule` when `pk_extension_revision >= 115`.
- `pk_supported_drug_count` is now 13.
- `pk_extension_revision` is now 115.

## Limitations

- The clonidine model is educational and qualitative only.
- Bradycardia/hypotension outputs are risk signals, not predicted event probabilities.

# v1.12-alpha — Vancomycin PK/PD Scaffold

## Added

- Vancomycin one-compartment educational PK model.
- Renal-function-dependent clearance modifier using simulated GFR / baseline GFR.
- AKI/shock penalty on vancomycin clearance.
- CRRT-lite extracorporeal vancomycin clearance field.
- Qualitative concentration/MIC target-attainment proxy.
- Qualitative vancomycin contribution to `antibiotic_coverage`.
- New scenario: `picu_vancomycin_aki_crrt_v1_12.yaml`.
- New audit tool: `pkpd_vancomycin_audit_v1_12.py`.
- New regression tests for vancomycin PK/PD.

## Changed

- `pk_supported_drug_count` increased from 9 to 10.
- Scenario loader now accepts `vancomycin_mg_kg_h` and `set_vancomycin` perturbations.
- `run_simulation.py` prints vancomycin fields in final summaries.

## Safety

- Educational scaffold only.
- Not for clinical dosing, therapeutic drug monitoring, Bayesian AUC estimation, or prescribing decisions.

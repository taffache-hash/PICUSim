# CHANGELOG v1.22.3-alpha — EPALS debrief scaffold

## Added

- `data/epals_debrief_spec_v1.22.3.yaml` with debrief report sections, variables and educational thresholds.
- `tools/epals_debrief_scaffold_v1_22_3.py` to generate EPALS scenario debrief reports from metadata and optional simulation runs.
- `docs/EPALS_DEBRIEF_SCAFFOLD_v1.22.3.md`.
- `tests/test_v1223_epals_debrief_scaffold.py`.

## Scope

This release does not modify the simulation engine. It adds a reporting/debriefing layer for the existing EPALS 5H/5T scenario pack.

## Safety

The debrief artifacts are for education and model review only. They are not clinical protocols and must not be used for patient care.

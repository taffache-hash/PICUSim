# CHANGELOG v1.21-alpha — Sobol full runner

## Added

- `data/sobol_full_specs_v1.21.yaml` with smoke, exploratory, report and paper presets.
- `tools/sobol_full_runner_v1_21.py` with dry-run planning, evaluation-count guardrails and v1.21 outputs.
- `docs/SOBOL_FULL_RUNNER_v1.21.md`.
- `tests/test_v121_sobol_full_runner.py`.

## Changed

- Extended shared summary keys in `tools/simtools.py` so sensitivity runners can capture adaptive V/Q, antibiotic and selected PK/PD outputs.
- Updated public alpha check and release metadata to v1.21-alpha.

## Limitation

This is a model-development uncertainty-analysis scaffold, not clinical validation.

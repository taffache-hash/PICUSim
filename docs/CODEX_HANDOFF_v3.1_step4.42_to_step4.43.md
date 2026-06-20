# Codex handoff — PCCSim v3.1 Step 4.42 to Step 4.43

Current package VERSION: `3.1-step4.42-organ-perfusion-model`.

Completed in Step 4.42:

- Added `modules/perfusion/organ_perfusion.py`.
- Added `modules/perfusion/__init__.py`.
- Updated `core/bus.py` with organ-perfusion state fields.
- Added documentation `docs/ORGAN_PERFUSION_MODEL_v3.1_step4.42.md`.
- Added contract tests `tests/test_v442_organ_perfusion_contract.py`.
- Updated `CHANGELOG.md` and roadmap.

Targeted tests passed:

```bash
pytest -q tests/test_v442_organ_perfusion_contract.py \
  tests/test_v439_shock_engine_contract.py \
  tests/test_v440_epals_decision_engine_contract.py \
  tests/test_v441_intubation_physiology_contract.py
```

Result: `12 passed`.

## Next Codex instruction

```text
Continue from PCCSim v3.1 package VERSION 3.1-step4.42-organ-perfusion-model.
Use docs/PCCSIM_V3_1_PHARMACOLOGY_AND_UI_ROADMAP.md as the source of truth.
Implement Step 4.43 only: Advanced vasoactive engine.
Scope: receptor-weighted response and bounded interaction handling for norepinephrine, epinephrine, dopamine, dobutamine, milrinone and vasopressin; include hysteresis/tachyphylaxis/audit signals where appropriate.
Keep scope narrow, add targeted contract tests, update VERSION, CHANGELOG.md and the roadmap.
Do not refactor unrelated code and preserve the educational/non-clinical disclaimer.
```

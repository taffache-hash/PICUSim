# Codex handoff — v3.1 Step 4.44 to Step 5.0

Current status: Step 4.44 completed.

## Completed in Step 4.44

- Added `core/scenario_engine_v2.py`.
- Added `data/scenario_engine_v2_step4.44.yaml`.
- Added eight EPALS-oriented v2 scenarios.
- Added `shock:` and `neuro:` initialization hooks to `ScenarioLoader`.
- Added targeted tests: `tests/test_v444_scenario_engine_v2_contract.py`.
- Updated roadmap and changelog.

## Validation already run

```bash
pytest -q tests/test_v444_scenario_engine_v2_contract.py
```

Result: `3 passed`.

## Next step

Implement Step 5.0 only: Validation pack.

### Scope

Build a reproducibility/plausibility validation pack over the existing scenario stack.

Required outputs:

- a validation runner for selected scenario files;
- a YAML or JSON validation spec defining expected educational ranges;
- a Markdown report writer with pass/warn/fail rows;
- targeted tests for the validation runner;
- no UI redesign;
- no clinical claims;
- keep all labels as educational/research alpha only.

### Suggested files

- `validation/scenario_validation_pack.py`
- `data/validation_pack_step5.0.yaml`
- `docs/VALIDATION_PACK_v3.1_step5.0.md`
- `tests/test_v500_validation_pack_contract.py`

### Exact Codex prompt

Implement Step 5.0 — Validation pack. Use the existing Step 4.44 scenario-engine v2 manifest as input. Add a lightweight validation runner that loads selected scenarios, builds their initial bus/timeline, checks predefined plausibility ranges and writes a compact Markdown report. Add targeted tests. Do not redesign UI. Do not add clinical decision support. Preserve educational/research-alpha disclaimers.

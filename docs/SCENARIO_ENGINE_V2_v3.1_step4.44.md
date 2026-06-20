# Scenario Engine v2 — v3.1 Step 4.44

Educational/research alpha only. Not for clinical use. Not a medical device.

## Purpose

Step 4.44 adds a scenario-engine v2 catalog for structured EPALS-oriented training scenarios. The change does not claim clinical decision support. It standardizes scenario metadata so Codex/UI/instructor layers can discover, validate and present scenario packs consistently.

## Added scenario pack

Manifest: `data/scenario_engine_v2_step4.44.yaml`

Scenarios:

1. `epals_v2_septic_shock_warm`
2. `epals_v2_anaphylactic_shock`
3. `epals_v2_tamponade_obstructive_shock`
4. `epals_v2_hyperkalemia_aki_instability`
5. `epals_v2_status_epilepticus_hypoxia`
6. `epals_v2_tbi_icp_crisis`
7. `epals_v2_dka_dehydration_shock`
8. `epals_v2_bronchiolitis_respiratory_failure`

## Engine contract

`core/scenario_engine_v2.py` provides:

- `SCENARIO_ENGINE_V2_REVISION = 444`
- `ScenarioV2Entry`
- `ScenarioEngineV2Catalog.from_yaml(...)`
- `validate_scenario_config(...)`
- `summary()` with scenario count, valid count, invalid count and validation details.

Validation checks are intentionally lightweight:

- required top-level fields: `name`, `patient`, `simulation_time_s`;
- required patient fields: `age_y`, `weight_kg`;
- positive simulation duration;
- at least four output fields;
- manifest expected actions and key outputs present.

## ScenarioLoader hooks

`core/scenario.py` now accepts scenario-level `shock:` and `neuro:` blocks:

- `shock.type`, `shock.severity`, `shock.stage`;
- shock phenotype indices including vasoplegia, hypovolemia, low-output, obstruction/tamponade;
- `neuro.ICP_mmHg`, `neuro.CPP_mmHg`, `neuro.cerebral_edema_index`, selected osmotherapy/drainage hooks.

These are scenario initialization hooks only. Existing physiology modules remain owners of dynamic state updates.

## Tests

Targeted contract test:

```bash
pytest -q tests/test_v444_scenario_engine_v2_contract.py
```

Expected result in this package: `3 passed`.

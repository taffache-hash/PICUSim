# Codex handoff — v3.1 Step 4.46 to Step 4.47

Current state: Step 4.46 completed.

Implemented in Step 4.46:
- `core/failure_to_rescue.py`;
- failure-to-rescue metadata with golden window, reversibility threshold and point-of-no-return;
- optional late deterioration perturbation generation;
- `ScenarioLoader.failure_to_rescue_info`;
- Streamlit timing display update;
- changelog and roadmap update;
- `tests/test_v446_failure_to_rescue_clock_contract.py`.

Validation run:

```bash
pytest -q tests/test_v445_scenario_timing_trigger_contract.py tests/test_v446_failure_to_rescue_clock_contract.py
# 6 passed
```

Next step: Step 4.47 — Adaptive deterioration engine.

Goal:
Make scenario trajectory respond to learner actions:
- delayed appropriate actions worsen the patient;
- wrong actions worsen phenotype-specific physiology;
- correct early actions dampen or cancel failure-to-rescue escalation;
- debrief should record action timing versus golden window.

Constraints:
- keep educational/research alpha disclaimer;
- do not claim clinical calibration;
- preserve existing Step 4.39-4.46 tests;
- add targeted Step 4.47 tests only.

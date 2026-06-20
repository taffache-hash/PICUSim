# Step 4.46 — Failure-to-rescue clock

Educational timing deviation added after Step 4.45.

## Purpose

Every stable-start scenario now can expose a visible failure-to-rescue clock:

- critical event trigger time;
- golden / critical intervention window;
- reversibility threshold;
- point-of-no-return marker;
- optional deterministic deterioration after the window closes.

This layer is a teaching scaffold. It is not calibrated for clinical prediction and must not be used for patient care.

## Default windows

Phenotype examples:

- septic shock: 8 min golden window after trigger;
- anaphylaxis: 3 min;
- tamponade: 5 min;
- tension pneumothorax: 4 min;
- bronchiolitis respiratory failure: 10 min.

The values are explicit, scenario-level educational assumptions and can be overridden in `failure_to_rescue` YAML metadata.

## UI behavior

The Streamlit interface displays:

- nominal scenario duration at 1x real time;
- critical event trigger time;
- failure-to-rescue golden window;
- reversibility threshold;
- point-of-no-return time.

## Files touched

- `core/failure_to_rescue.py`
- `core/scenario.py`
- `core/scenario_timing.py`
- `apps/streamlit_app.py`
- `tests/test_v446_failure_to_rescue_clock_contract.py`
- `CHANGELOG.md`
- `docs/PCCSIM_V3_1_PHARMACOLOGY_AND_UI_ROADMAP.md`

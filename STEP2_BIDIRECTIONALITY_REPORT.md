# v3.1 Step 2 — UI/backend bidirectionality

Scope: backend-to-UI control round-trip only. No mathematical physiology changes, no vasoactive model changes, no new drug controls added.

## Changes

- Added `CONTROL_KEYS` and `controls_state()` in `api/state_profiles.py`.
- Added a nested `controls` object to `bedside` and `bedside_fast` state payloads.
- Added `profile=controls` to `/session/{session_id}/state` for explicit control-state inspection.
- Added UI sync maps in `ui/app.js`:
  - `RANGE_CONTROL_BINDINGS` for FiO2, PEEP and RR.
  - `DRUG_CONTROL_BINDINGS` for currently visible drug fields.
- Added `syncControlsFromState(st)` to update sliders and numeric drug inputs from backend state.
- Added an active-edit guard: the UI does not overwrite a control while the user is focused on it or immediately after input.

## Controls mirrored back to UI

Ventilation:

- `FiO2`
- `PEEP`
- `RR`
- `Paw`

Currently routed/visible or already accepted drug controls:

- `adrenaline_mcg_kg_min`
- `norad_mcg_kg_min`
- `dopamine_mcg_kg_min`
- `fentanyl_mcg_kg_h`
- `morphine_mcg_kg_h`
- `midazolam_mcg_kg_h`
- `propofol_mg_kg_h`
- `rocuronium_mg_kg_h`
- `insulin_UI_h`
- `vancomycin_mg_kg_h`
- `piperacillin_mg_kg_h`

## Tests run

```bash
node --check ui/app.js
python -m py_compile api/state_profiles.py api/server.py api/session.py
pytest -q tests/test_v302_ui_backend_bidirectional.py tests/test_v301_ui_live_controls.py tests/test_v210_web_monitor.py tests/test_v260_ui_polish_tablet.py
pytest -q tests/test_v200_api_server.py tests/test_v220_emergency_training_mode.py tests/test_v230_instructor_mode.py
```

Result:

- 12/12 passed for Step 2 + UI monitor tests.
- 9/9 passed for API/training/instructor smoke tests.

## Not changed in this step

- No correction of cardiovascular mathematics.
- No correction of `drug_MAP_mod` sign.
- No addition of missing drugs to the visible UI.
- No arterial waveform refactor.
- No Dockerfile changes.

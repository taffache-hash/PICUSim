# Step 4.16 - Audio UI cues + session button state

## Goal
Make simulator control buttons visibly communicate pressed/not pressed state, especially the session controls, and extend the monitor audio system with lightweight UI feedback cues.

## Changes
- Added shared button state helpers for `button-active`, `button-pending`, `button-confirmed`, and `button-error`.
- `Start` now stays visually active while the simulation is running.
- `Pause` now stays visually active when a loaded session is paused/not running.
- `Load`, `Step 5 s`, and `Reset` show pending/confirmed/error feedback.
- Existing monitor audio now includes optional UI cues when Audio is ON.
- Audio badge now indicates `SAT+ECG+UI`.
- Added `tests/test_v334_audio_session_button_state_contract.py`.

## Verification
- `node --check ui/app.js` passed.
- `python -m py_compile tests/test_v334_audio_session_button_state_contract.py` passed.
- Manual execution of the v334 contract assertions passed.
- `pytest` was attempted but is not installed in the available Python runtime.

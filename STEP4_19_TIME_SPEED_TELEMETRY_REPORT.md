# Step 4.19 - Simulated time / wall-clock / speed telemetry

## Goal
Complete roadmap Step 4.0E with a clear UI indicator for simulated time, real elapsed wall-clock time, and effective speed multiplier.

## Changes
- Added `timeTelemetry` beside the session metadata.
- Displays `sim`, `wall`, and effective `speed` in compact mm:ss/h:mm:ss format.
- Tracks wall-clock time across Start/Pause and resets on Load/Reset/Load saved.
- Updates continuously during animation frames and on bedside state updates.
- Keeps existing speed input as the control; this step only exposes clearer telemetry.
- Added `tests/test_v337_time_telemetry_contract.py`.

## Verification
- `node --check ui/app.js` passed.
- Manual v337 contract assertions passed.
- API smoke test passed: load, start at speed 2, pause, step.
- Full pytest was not run because pytest is not installed in the available Python runtime.
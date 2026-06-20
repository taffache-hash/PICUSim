# Step 4.18 - Always-visible rotating labs strip

## Goal
Complete the roadmap item Step 4.1B with a compact, always-visible bedside labs strip without changing physiology or backend schemas.

## Changes
- Added `labsStrip` under the bedside monitor header/scenario info area.
- Shows four compact lab/secondary parameters at a time.
- Rotates through roadmap parameters every 8 real seconds.
- Parameters include lactate, glucose, K, Na, Hb, creatinine, bilirubin, GCS proxy, RASS proxy, ICP, CVP, DO2, and urine output.
- Uses cached bedside/full state and requests `/state?profile=full` at most every 8 seconds while a session is active.
- Added responsive CSS for desktop/tablet/mobile.
- Added `tests/test_v336_labs_strip_contract.py`.

## Verification
- `node --check ui/app.js` passed.
- Manual v335+v336 contract assertions passed.
- API full-profile check on `picu_sedation_pkpd` returned populated strip values including lactate, Hb, DO2, CVP, and urine rate.
- Full pytest was not run because pytest is not installed in the available Python runtime.
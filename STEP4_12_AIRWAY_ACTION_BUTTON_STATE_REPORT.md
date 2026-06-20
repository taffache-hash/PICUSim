# STEP 4.12 - Airway action button state

## Goal
Make airway action buttons visibly retain their selected/active state after actions such as Intubate, Bag-mask rescue, Failed attempt, and Extubation.

## Changes
- Added `airwayActiveEvents()` and `updateAirwayActionButtons()` in `ui/app.js`.
- Airway buttons now use `aria-pressed`, `action-active`, and `pending` states.
- Button state is derived from live bedside state, not only from the last click.
- Reconnected bolus controls when the drug panel opens and bound the clear bolus status button.
- Added `tests/test_v331_airway_action_button_state_contract.py`.

## Expected UI behavior
- `Intubate` stays active when the patient is intubated.
- `Bag-mask` stays active while bag-mask/manual ventilation is active.
- `Accidental extubation` stays active after an extubation state.
- `Failed attempt` stays active as a historical signal after at least one failed attempt.
- A clicked airway button shows a pending state until the backend response updates the patient state.

## Verification
- `node --check ui/app.js` passed.
- `python -m py_compile tests/test_v331_airway_action_button_state_contract.py` passed.
- Manual execution of the new contract assertions passed.
- Full pytest was not run because pytest is not installed in the available Python runtimes.

# STEP 4.13 - Dedicated Emogas panel

## Goal
Expose arterial blood gas values in a clearly named Emogas tab instead of requiring the user to search inside Monitor esteso.

## Changes
- Added an `Emogas` card in the control dock.
- Added an `Emogas` tab inside the Apparatus window.
- Added a dedicated `emogasPanel` with pH, PaO2, PaCO2, EtCO2, SaO2, HCO3, BE, lactate, Hb, Na, K, and glucose.
- Added `Aggiorna emogas`, wired to the full state snapshot refresh.
- Emogas updates from bedside state while the tab is open and from full snapshot when refreshed.
- Added `tests/test_v332_emogas_panel_contract.py`.

## Verification
- `node --check ui/app.js` passed.
- `python -m py_compile tests/test_v332_emogas_panel_contract.py` passed.
- Manual execution of the Emogas contract assertions passed.
- Full pytest was not run because pytest is not installed in the available Python runtimes.

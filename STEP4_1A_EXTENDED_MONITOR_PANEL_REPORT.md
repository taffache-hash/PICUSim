# Step 4.1A — Extended monitor panel

Scope: add a request-only extended monitor surface inside the existing apparatus overlay.

## Implemented

- Added `Monitor esteso` dock card and apparatus tab.
- Added five grouped blocks:
  - Hemodynamics / perfusion
  - Respiratory
  - Metabolic / labs
  - Neurologic / sedation
  - Renal / fluids
- Uses the existing `/session/{session_id}/state?profile=full` endpoint only while the panel is open, with a 2.5 s polling interval.
- Falls back to the bedside websocket state if full-state refresh fails.
- Keeps the main bedside monitor uncluttered for single-screen use.
- Adds a manual Refresh button.
- Displays missing variables as `--` instead of failing.

## Non-goals

- No engine/model changes.
- No Docker changes.
- No always-visible labs strip.
- No sparkline trend implementation.
- No visual alarm threshold implementation.
- No searchable raw-Bus debug table yet.

## Notes

ScvO2 is displayed as an explicit value if present (`ScvO2` or `SvO2`), otherwise it is derived client-side from SaO2, VO2, CO and Hb. A later engine-level Step 4.0C can add ScvO2 to the Bus as a first-class model variable.

## Tests

Added `tests/test_v317_extended_monitor_panel_contract.py`. Targeted validation passed with 86 tests.

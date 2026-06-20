# Step 1 — UI live-control reactivity fix

Scope: UI only. No mathematical engine, drug model, hemodynamic model, scenario, API router, or Docker change.

## Problem
Ventilator and drug controls updated the local label on input, but most backend actions were sent only on `change`. This made sliders and numeric drug controls feel delayed, especially when the user expected immediate monitor response.

## Change
`ui/app.js` now adds live debounced control binding:

- `oninput`: updates the visible control value and schedules a backend action after 120 ms.
- `onchange`: flushes the final value immediately.
- Live updates are silent in the event log to avoid flooding the log.
- Final release/change is logged once.

Affected controls:

- FiO2
- PEEP
- RR
- all current drug numeric inputs in the Drugs panel

## Not changed in this step

- No new drugs added.
- No hemodynamic mathematical correction.
- No bidirectional control synchronization from backend state to UI controls.
- No arterial waveform / MAP / SAP / DAP logic changed.
- No Docker change.

## Tests run

```bash
node --check ui/app.js
pytest -q tests/test_v210_web_monitor.py tests/test_v260_ui_polish_tablet.py tests/test_v301_ui_live_controls.py
```

Result:

```text
9 passed
```

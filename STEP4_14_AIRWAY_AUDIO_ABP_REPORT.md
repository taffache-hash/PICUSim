# Step 4.14 — Airway quick-action fix + monitor audio + pressure-coupled ABP

## Fixes

1. Quick airway intubation no longer sends the invalid generic severity `moderate`.
   - UI buttons now carry event-specific `data-severity` values.
   - Backend resolves legacy aliases, so older UI calls remain safe.

2. Bedside audio monitor added.
   - Off by default because browsers require a user gesture.
   - Toggle: `Audio OFF/ON`.
   - Pulse oximeter tone follows HR and changes pitch with SpO2.
   - ECG QRS click follows HR.

3. ABP waveform strengthened.
   - Vertical position follows MAP.
   - Visible amplitude expands/contracts with pulse pressure.

## Files changed

- core/airway_events.py
- ui/index.html
- ui/app.js
- ui/canvas_waveforms.js
- ui/styles.css
- tests/test_v333_airway_audio_abp_contract.py
- VERSION
- CHANGELOG.md

# Step 4.4 — Visual threshold alarms

Scope: UI-only bedside alarm highlighting. No audio, no backend changes, no physiology changes.

Implemented:
- warning/critical CSS states for HR, SpO2, MAP, PaCO2/EtCO2, Paw, FiO2
- configurable JavaScript threshold table `VITAL_ALARM_RULES`
- `updateVisualAlarms(st)` called from `updateBedside`

Purpose: make dangerous bedside values visually salient for training without adding noise or a new alarm engine.

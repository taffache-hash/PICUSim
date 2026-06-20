# Emergency training mode v2.2

v2.2 integrates EPALS and airway-decision training workflows into the lightweight web monitor.

## New API endpoints

- `GET /training/scenarios` returns emergency scenario metadata grouped as airway decision, EPALS 5H, and EPALS 5T.
- `GET /session/{session_id}/debrief` computes live debrief metrics from the current API session history.

## UI additions

The `/monitor` page now includes:

- emergency scenario selector;
- one-click load for emergency scenarios;
- scenario focus and debrief prompts;
- debrief panel with SpO2 nadir, time below SpO2 thresholds, PaCO2 peak, MAP minimum, failed airway attempts, rescue ventilation timing and intubation timing;
- triggered decision flags and threshold events.

## Safety note

Educational/research alpha only. Not for clinical use. Not a medical device.

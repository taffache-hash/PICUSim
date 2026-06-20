# PDT Session Report — airway_rsi_hypoxic_child_v1_24

Educational/research alpha only. Not for clinical use. Not a medical device.

## Session
- Schema: `pdt-session-save-v2.5`
- Version: `3.1-step4.50-full-prevalidation-audit`
- Session ID: `9657c2e2-553d-4056-8f95-bcb790029353`
- Scenario path: `scenarios/airway_rsi_hypoxic_child_v1_24.yaml`
- Time: 10.0 / 420.0 s
- dt: 1.0 s

## Debrief metrics
- SpO2_nadir: 0.82
- time_below_SpO2_90_s: 10.0
- time_below_SpO2_80_s: 0.0
- PaCO2_peak: 68.3
- MAP_min: 60.8
- failed_intubation_count: 1
- intubation_attempt_count: 1
- first_rescue_ventilation_time_s: -1.0
- intubation_success_time_s: -1.0
- time_to_reoxygenation_after_intubation_s: -1.0

## Triggered decision flags
- None

## Instructor notes
- t=10.0 s [observation pinned]: Learner delayed rescue ventilation.

## Event log
- t=0.0 s: action:airway_event
- t=10.0 s: instructor:observation

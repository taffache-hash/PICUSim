# Emergency debrief engine v1.26

`v1.26-alpha` adds an instructor-facing debrief engine for airway decision and emergency scenarios.

The tool runs selected scenarios, reads the generated time series, and computes educational metrics:

- SpO2 nadir and time of nadir
- time below SpO2 90%, 80%, and 70%
- PaCO2 peak and hypercapnia burden
- MAP/HR nadir markers
- first failed intubation attempt
- first rescue ventilation time
- intubation success time
- extubation time
- time to reoxygenation after intubation
- repeated-attempt and delayed-rescue flags

## Usage

```bash
python tools/emergency_debrief_engine_v1_26.py --dt 10 --fail-on-review
```

Run a subset:

```bash
python tools/emergency_debrief_engine_v1_26.py --dt 10 --scenarios airway_failed_intubation_cannot_oxygenate_v1_25
```

Include EPALS scenario packs as well:

```bash
python tools/emergency_debrief_engine_v1_26.py --dt 10 --include-epals
```

## Outputs

Generated under `outputs/emergency_debrief_v1.26/`:

- `emergency_debrief_summary_v126.json`
- `emergency_debrief_scenario_metrics_v126.csv`
- `emergency_debrief_timing_v126.csv`
- `emergency_debrief_threshold_events_v126.csv`
- `emergency_debrief_decision_flags_v126.csv`
- `emergency_debrief_index_v126.md`
- `scenario_reports/*.md`

## Limitations

This is a debriefing scaffold, not a grading system. Metrics are educational markers only. Timing is limited by the simulation snapshot interval. Airway interventions are simplified event proxies and are not procedural guidance.

Not for clinical use. Not a medical device. Not a validated patient-specific digital twin.

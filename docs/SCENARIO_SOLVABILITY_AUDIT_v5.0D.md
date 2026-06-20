# Scenario Solvability Audit — v5.0D

Status: completed  
Scope: curated EPALS scenario-engine v2 pack before downstream publication-grade validation.

This is not clinical validation and not medical decision support. It is a structural/playability gate.

## Purpose

Step 5.0D checks that each curated scenario can function as an educational simulation rather than as a static display. Each scenario should be:

- playable: manifest and scenario file exist, minimum time and patient metadata are present;
- recoverable: there is at least one plausible intervention/reversal marker;
- fail-able: the starting physiology contains a measurable failure burden;
- non-deterministic enough: multiple action steps and outputs allow different trajectories;
- debriable: expected actions, outputs and debrief questions are available.

## Files added

- `data/scenario_solvability_audit_v5.0D.yaml`
- `tools/scenario_solvability_audit_v5_0D.py`
- `tests/test_v500d_scenario_solvability_audit.py`
- `outputs/scenario_solvability_v5.0D/scenario_solvability_audit_v50D.csv`
- `outputs/scenario_solvability_v5.0D/scenario_solvability_summary_v50D.json`
- `outputs/scenario_solvability_v5.0D/scenario_solvability_report_v50D.md`

## Current audit result

- Scenarios audited: 8
- Solvable: 8
- Playable: 8
- Recoverable: 8
- Fail-able: 8
- Non-deterministic/playable: 8
- Critical findings: 0
- Review findings: 0
- Pass audit: true

## Test command

```bash
pytest -q tests/test_v500d_scenario_solvability_audit.py \
  tests/test_v500a_literature_benchmark_engine.py \
  tests/test_v500b_monte_carlo_runner.py \
  tests/test_v500c_plausibility_guardrails.py
```

Expected compact handoff result: 11 passed.

## Next step

Proceed to Step 5.0E — UI human factors audit v2.

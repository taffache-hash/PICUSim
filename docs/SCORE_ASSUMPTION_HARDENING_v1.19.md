# Score Assumption Registry Hardening — v1.19

This release hardens the qualitative score/proxy/modifier registry used by the public PDT package.

It does **not** clinically validate the model. It improves transparency by making heuristic variables explicit, range-auditable and ready for expert review.

## What changed

- Added `data/score_assumption_registry_v1.19.yaml`.
- Added missing registry entries introduced by the public v1.08–v1.18 extensions.
- Added numeric hard/expected ranges for score-like variables where software sanity checking is meaningful.
- Added reviewer guidance fields:
  - review priority;
  - parameterizable-in-future flag;
  - qualitative review question.
- Added `tools/score_assumption_audit_v1_19.py`.
- Added default scenario subset in `data/score_assumption_audit_scenarios_v1.19.yaml`.

## Output

The audit writes:

```text
outputs/score_assumption_audit_v1.19/
  score_assumption_registry_v119.csv
  score_assumption_completeness_v119.json
  score_assumption_range_audit_v119.csv
  score_assumption_scenario_summary_v119.csv
  score_assumption_audit_report_v119.md
  score_assumption_audit_summary_v119.json
```

## Interpretation

- `PASS`: value remains inside the configured expected and hard software range.
- `REVIEW`: value is inside the hard software range but outside the broad expected range, or requires reviewer inspection.
- `FAIL`: value is outside the hard software range and likely indicates a software regression or missing clamp.
- `NOT_PRESENT`: the variable is not emitted by that scenario; this is not a failure.

## Important limitation

The registry ranges are not bedside normal values and not therapeutic targets. They are software sanity bounds for internal educational scores.

# Contributing

This project is an exploratory alpha physiology simulation framework for education, scenario design, and in-silico model development. It is not for clinical use and must not be presented as a validated clinical digital twin.

## Contribution priorities

Preferred contributions for the alpha phase:

1. scenario YAML files with clear educational objectives and limitations;
2. documentation improvements;
3. tests that strengthen numerical stability, unit consistency, or plausibility envelopes;
4. external-review checklists and benchmark metadata;
5. user-facing notebooks or teaching material.

Avoid adding patient-specific decision logic, treatment recommendations, or claims of clinical validity.

## Scenario contribution checklist

Every new scenario should include:

- `name`, `description`, `patient`, `respiratory`, `cardiovascular`, `outputs`, and `simulation_time_s`;
- a clear educational purpose;
- explicit limitations;
- at least one smoke run with `python run_simulation.py --scenario scenarios/<file>.yaml --dt 1 --no-plot`;
- no hidden claims of bedside validity.

## Code contribution checklist

Before submitting code:

```bash
python tools/v1_alpha_check.py --fail-on-error
pytest tests/test_dependency_audit.py tests/test_v1_alpha_candidate.py
```

For physiological changes, add a focused regression test and document the assumptions.

## Safety language

Use this framing consistently:

> exploratory simulation framework; educational and research alpha; not for clinical use; not a medical device; not a validated patient-specific digital twin.


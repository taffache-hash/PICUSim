# v1.21-alpha — Sobol full runner

`tools/sobol_full_runner_v1_21.py` is a configurable Sobol/Saltelli-Jansen runner for model-development uncertainty analysis.

It extends the lightweight v1.07 Sobol scaffold by adding named presets, dry-run planning, evaluation-count guardrails and v1.21 output manifests.

## Use

Dry-run planning only:

```bash
python tools/sobol_full_runner_v1_21.py --preset exploratory --dry-run
```

Small smoke execution:

```bash
python tools/sobol_full_runner_v1_21.py --preset smoke --scenarios ards_mild --fail-on-error
```

Heavier offline run:

```bash
python tools/sobol_full_runner_v1_21.py --preset report --allow-large-run
```

## Presets

- `smoke`: very small regression/pipeline check.
- `exploratory`: development-scale ranking.
- `report`: stronger internal-report analysis.
- `paper`: heavy offline analysis that still requires external review before any scientific claim.

## Outputs

The tool writes:

- `sobol_full_plan_v121.csv`
- `sobol_full_indices_v121.csv`
- `sobol_full_evaluations_v121.csv`
- `sobol_full_summary_v121.json`
- `sobol_full_report_v121.md`

## Interpretation

`S1` estimates the direct variance contribution of a parameter. `ST` estimates total contribution, including non-linear and interaction effects. Parameter ranges are stress-test ranges, not calibrated priors.

This is not clinical validation, not a medical-device verification process and not for patient-care decisions.

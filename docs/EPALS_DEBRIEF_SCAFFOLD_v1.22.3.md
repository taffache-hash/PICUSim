# EPALS debrief scaffold v1.22.3

## Purpose

v1.22.3 adds an instructor-facing debrief generator for the EPALS 5H/5T scenario pack. It converts scenario metadata and optional simulation time-series into reproducible debrief artifacts.

This is an educational reporting layer only. It is not clinical validation, not a resuscitation protocol and not a medical device feature.

## New files

- `data/epals_debrief_spec_v1.22.3.yaml`
- `tools/epals_debrief_scaffold_v1_22_3.py`
- `tests/test_v1223_epals_debrief_scaffold.py`

## Main command

```bash
python tools/epals_debrief_scaffold_v1_22_3.py --dt 10 --fail-on-review
```

Fast metadata-only mode:

```bash
python tools/epals_debrief_scaffold_v1_22_3.py --no-run
```

Single-scenario mode:

```bash
python tools/epals_debrief_scaffold_v1_22_3.py --scenarios epals_hypoxia_airway_obstruction --dt 10
```

## Outputs

Default output directory:

```text
outputs/epals_debrief_v1.22.3/
```

Generated files:

- `epals_debrief_summary_v1223.json`
- `epals_debrief_scenario_summary_v1223.csv`
- `epals_debrief_metric_markers_v1223.csv`
- `epals_debrief_threshold_events_v1223.csv`
- `epals_debrief_questions_v1223.csv`
- `epals_debrief_index_v1223.md`
- `scenario_reports/<scenario>_debrief.md`

## Debrief report content

Each scenario report includes:

1. reversible cause and H/T group;
2. clinical frame;
3. key physiologic markers;
4. threshold events;
5. intervention proxies from YAML perturbations;
6. expected physiologic response;
7. debrief questions;
8. explicit safety note.

## Interpretation

The report is designed for model review and educational scenario design. It summarizes whether a scenario behaves in the expected qualitative direction, but it does not grade a learner and must not be used for clinical decision-making.

## Limitations

- Intervention events are scenario perturbations, not real clinical protocols.
- Thresholds are educational markers, not clinical treatment thresholds.
- Some EPALS causes remain proxy models until later engine releases add airway interface, intubation/extubation and more detailed obstructive-shock mechanics.

# PDT v1.22 — EPALS Reversible-Cause Scenario Roadmap

This release adds a structured educational taxonomy for paediatric emergency reversible causes and maps them to PDT modules, variables, planned scenario IDs, intervention concepts and debriefing questions.

It does **not** change the simulation engine and does **not** add the 5H/5T scenario YAML files yet. Those are intentionally split into v1.22.1 and v1.22.2 to avoid mixing curriculum design with physiology changes.

Clinical status: educational/research alpha only. Not for clinical use, not a medical device, and not a validated patient-specific digital twin.

## Files added

```text
data/epals_reversible_causes_v1.22.yaml
data/epals_scenario_curriculum_v1.22.yaml
tools/epals_scenario_audit_v1_22.py
tests/test_v122_epals_taxonomy.py
```

## Taxonomy

The teaching scaffold uses five H entries and five T entries:

```text
H: hypoxia
H: hypovolaemia
H: hydrogen ion / acidosis
H: hypo-/hyperkalaemia and metabolic disorder
H: hypothermia

T: tension pneumothorax
T: cardiac tamponade
T: toxins / intoxication
T: pulmonary thrombosis
T: cardiac thrombosis / paediatric low-output analogue
```

The paediatric cardiac-T scenario is intentionally framed as cardiac thrombosis or myocarditis/low-output physiology, because this is more realistic for PICU teaching than an adult-style coronary thrombosis scenario.

## Planned implementation sequence

```text
v1.22.1  5H scenario YAML pack
v1.22.2  5T scenario YAML pack
v1.22.3  EPALS debrief scaffold
v1.23    airway interface model and unassisted breathing path
```

## Audit

Run:

```bash
python tools/epals_scenario_audit_v1_22.py --fail-on-review
```

Outputs:

```text
outputs/epals_taxonomy_v1.22/epals_taxonomy_summary_v122.json
outputs/epals_taxonomy_v1.22/epals_cause_matrix_v122.csv
outputs/epals_taxonomy_v1.22/epals_taxonomy_report_v122.md
```

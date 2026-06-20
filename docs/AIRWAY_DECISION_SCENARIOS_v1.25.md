# v1.25-alpha — Airway decision scenario pack

This release adds six executable educational airway-decision scenarios on top of the v1.24 airway-event system. The scenarios are designed for debriefing and regression testing, not procedural guidance.

## Scenarios

1. `airway_failed_intubation_cannot_oxygenate_v1_25.yaml` — repeated failed attempts, laryngospasm, difficult rescue ventilation, delayed secured airway.
2. `airway_extubation_failure_bronchiolitis_v1_25.yaml` — planned extubation to HFNC followed by recurrent obstruction and re-intubation.
3. `airway_laryngospasm_post_extubation_v1_25.yaml` — severe post-extubation upper-airway obstruction with rescue ventilation and intubation.
4. `airway_aspiration_during_rsi_v1_25.yaml` — aspiration during RSI, rescue oxygenation and airway protection.
5. `airway_opioid_sedation_apnea_v1_25.yaml` — sedative/opioid-related hypoventilation, bag-mask rescue and controlled intubation.
6. `airway_niv_failure_to_intubation_v1_25.yaml` — NIV failure in obstructive hypercapnic respiratory failure requiring intubation.

## Design constraints

- Uses only public v1.24 airway events.
- Keeps scenario logic in YAML.
- No clinical decision support, no procedural recommendations, no patient-specific prediction.
- Intended outputs: trajectory review, debrief markers, smoke testing, educational scenario authoring.

## Audit

Run:

```bash
python tools/airway_decision_scenario_audit_v1_25.py --dt 10 --fail-on-review
```

The audit checks scenario loading, simulation completion, event activation, expected airway-transition markers, and final secured-airway state where applicable.

# EPALS 5H scenario pack — v1.22.1-alpha

This release adds the first executable EPALS-style reversible-cause scenarios. It is deliberately YAML-first: no respiratory, ventilator, cardiovascular or airway-interface engine changes are made in this release.

## Scenarios

1. `epals_hypoxia_airway_obstruction.yaml` — hypoxia with airway obstruction physiology.
2. `epals_hypovolemia_hemorrhagic_shock.yaml` — hemorrhagic hypovolaemic shock.
3. `epals_acidosis_septic_shock.yaml` — metabolic acidosis driven by septic hypoperfusion.
4. `epals_hyperkalemia_aki.yaml` — AKI-associated hyperkalaemia/metabolic disorder.
5. `epals_hypothermia_rewarming.yaml` — accidental hypothermia and active rewarming.

## Design principles

Each scenario contains a clinical narrative, reversible-cause metadata, expected physiological response, debriefing questions and explicit limitations. Interventions are simplified physiology proxies, not clinical treatment protocols.

## What this release does not do

- It does not add a non-intubated/unassisted airway model.
- It does not add HFNC/NIV/ETT resistance modelling.
- It does not simulate real resuscitation algorithms or drug doses.
- It is not for clinical use.

The airway-interface and intubation work remains scheduled for v1.23+.

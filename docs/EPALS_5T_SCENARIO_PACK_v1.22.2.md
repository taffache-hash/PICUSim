# EPALS 5T scenario pack — v1.22.2-alpha

This release adds the executable T-cause EPALS-style scenario pack. It is deliberately scenario-first and does not change the respiratory, ventilator, cardiovascular or airway-interface engine.

## Scenarios

1. `epals_tension_pneumothorax.yaml` — obstructive shock plus ventilation failure from tension pneumothorax physiology.
2. `epals_cardiac_tamponade.yaml` — obstructive shock pattern with high venous pressure and low cardiac output.
3. `epals_toxicologic_opioid_benzodiazepine.yaml` — toxin-like opioid/benzodiazepine respiratory depression.
4. `epals_pulmonary_thrombosis_pe.yaml` — pulmonary vascular obstruction, RV afterload and dead-space physiology.
5. `epals_cardiac_thrombosis_myocarditis_low_output.yaml` — pediatric low-output analogue for the cardiac thrombosis T category.

## Design notes

- These scenarios are educational physiology traces, not treatment algorithms.
- Some T categories require future dedicated physiology modules for higher fidelity. In v1.22.2, tamponade, pulmonary thrombosis and cardiac low-output states are represented through existing bus variables and module couplings.
- Airway-interface and intubation/extubation work remains scheduled for v1.23+.

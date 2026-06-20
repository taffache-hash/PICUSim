# v1.23.2 — NIV / CPAP / BiPAP base

This release adds a conservative non-invasive ventilation layer for educational airway scenarios.

Implemented interfaces:

- `NIV_CPAP`: non-invasive mask CPAP, not intubated, ventilator connected, leak-adjusted delivered PEEP.
- `NIV_BIPAP`: non-invasive bilevel support, not intubated, ventilator connected, leak-adjusted EPAP and pressure support.

New/important Bus fields:

- `NIV_mode`
- `NIV_CPAP_cmH2O`
- `NIV_IPAP_cmH2O`
- `NIV_EPAP_cmH2O`
- `NIV_pressure_support_cmH2O`
- `NIV_FiO2_set`
- `NIV_leak_fraction`
- `NIV_delivered_PEEP_cmH2O`
- `NIV_delivered_PS_cmH2O`
- `NIV_delivered_PIP_cmH2O`
- `NIV_deadspace_washout`
- `NIV_failure_risk`

The model is intentionally qualitative. It is not a clinical NIV calculator and does not model exact mask mechanics, leak-compensation algorithms, patient-ventilator asynchrony, gastric insufflation or skin injury.

Two scenarios are included:

- `airway_niv_cpap_bronchiolitis_v1_23_2.yaml`
- `airway_niv_bipap_hypercapnia_v1_23_2.yaml`

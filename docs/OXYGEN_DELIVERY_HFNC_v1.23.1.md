# v1.23.1 — Oxygen delivery / HFNC base

This release extends the airway-interface layer with non-invasive oxygen delivery.

Implemented interfaces:

- `LOW_FLOW_OXYGEN`: extubated spontaneous breathing with non-pressurised oxygen.
- `SIMPLE_MASK`: higher qualitative delivery efficiency than low-flow oxygen.
- `HFNC`: high-flow nasal cannula with effective FiO2, a small distending-pressure proxy and dead-space washout.

The model remains educational. It does not compute exact inspired FiO2 from cannula geometry, patient inspiratory demand, device brand, mouth opening, humidification or circuit physics.

Key bus fields:

```text
oxygen_interface
oxygen_flow_L_min
oxygen_FiO2_set
FiO2_delivered
FiO2_delivery_efficiency
HFNC_flow_L_min
HFNC_FiO2_set
HFNC_distending_pressure_cmH2O
HFNC_deadspace_washout
HFNC_failure_risk
mouth_leak_fraction
oxygen_delivery_revision
```

Two scenarios are included:

```text
scenarios/airway_low_flow_oxygen_v1_23_1.yaml
scenarios/airway_hfnc_bronchiolitis_v1_23_1.yaml
```

Safety note: outputs are not for clinical oxygen prescription or escalation decisions.

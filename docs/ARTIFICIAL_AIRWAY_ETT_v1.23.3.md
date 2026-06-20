# Artificial airway / ETT-tracheostomy base — v1.23.3

This release adds an educational artificial-airway scaffold for intubated or tracheostomised patients.
It does not implement intubation/extubation events yet; it only makes a connected tube visible to the physiology.

## Added concepts

- explicit ETT/tracheostomy interface metadata;
- tube internal diameter and length;
- qualitative tube resistance using a bounded ID^-4 relationship;
- tube/apparatus dead-space proxy;
- cuff leak proxy;
- tube obstruction proxy;
- qualitative artificial-airway failure risk.

## New Bus fields

`tube_internal_diameter_mm`, `tube_length_cm`, `tube_resistance_cmH2O_L_s`,
`tube_resistance_factor`, `tube_dead_space_mL`, `tube_VdVt_add`,
`tube_obstruction_score`, `cuff_leak_fraction`, `cuff_pressure_cmH2O`,
`ETT_position_score`, `ETT_pressure_delivery_efficiency`,
`ETT_FiO2_delivery_efficiency`, `ETT_failure_risk`, `artificial_airway_revision`.

## Limitations

This is not a clinical tube-size calculator and not a measured pressure-drop model. It is a transparent educational proxy designed to support later intubation, failed-airway and extubation scenarios.

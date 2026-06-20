# Step 5.1D — Sensitivity maps

Purpose: map internal parameter-to-outcome behavior and identify dominant/fragile variables before publication freeze.

- Scenarios: 5
- Parameters: 6
- Outcomes: 4
- Map rows: 840
- Dominant findings: 44
- Fragility flags: 40

## Top sensitivity drivers
- septic_shock / lactate_peak: airway_resistance_factor (positive, normalized=0.81781)
- tamponade / lactate_peak: preload_factor (negative, normalized=0.81361)
- dka_shock / lactate_peak: airway_resistance_factor (positive, normalized=0.76714)
- anaphylaxis / lactate_peak: preload_factor (negative, normalized=0.75925)
- septic_shock / lactate_peak: preload_factor (negative, normalized=0.73013)
- tamponade / lactate_peak: airway_resistance_factor (positive, normalized=0.66432)
- anaphylaxis / lactate_peak: airway_resistance_factor (positive, normalized=0.63543)
- tamponade / lactate_peak: contractility_factor (negative, normalized=0.5427)
- anaphylaxis / lactate_peak: contractility_factor (negative, normalized=0.5106)
- septic_shock / lactate_peak: contractility_factor (negative, normalized=0.47101)

## Interpretation boundary
These maps describe internal simulator behavior. They are intended for reproducibility, model inspection, and reviewer transparency, not for bedside prediction.

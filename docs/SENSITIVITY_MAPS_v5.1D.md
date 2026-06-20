# Step 5.1D — Sensitivity maps

This step adds internal sensitivity mapping before publication freeze.

## Outputs

- `outputs/sensitivity_maps_v5.1D/sensitivity_map_long_v51D.csv`
- `outputs/sensitivity_maps_v5.1D/sensitivity_ranking_v51D.csv`
- `outputs/sensitivity_maps_v5.1D/sensitivity_fragility_flags_v51D.csv`
- `outputs/sensitivity_maps_v5.1D/sensitivity_summary_v51D.json`
- `outputs/sensitivity_maps_v5.1D/sensitivity_report_v51D.md`

## Scope

The maps test internal parameter-to-outcome behavior across representative EPALS-style scenarios. They are for model inspection and reproducibility, not for clinical prediction.

## Parameters

- preload factor
- SVR factor
- contractility factor
- alveolar oxygen reserve
- airway resistance factor
- lactate clearance factor

## Outcomes

- SpO2 nadir
- MAP nadir
- lactate peak
- rescue margin

# Step 4.10 - Respiratory Response Test

Functional API checks after Steps 4.8-4.10 found and fixed one bidirectionality issue.

## Finding

`set_rr` wrote to `RR`, but respiratory/chemoreflex updates could overwrite that field. In ventilated scenarios the commanded respiratory rate therefore drifted back toward the scenario/internal value.

## Fix

- Added `ventilator_RR_set` to `BusState`.
- `set_rr` now writes both `RR` and `ventilator_RR_set`.
- `VentilatorModule` prefers `ventilator_RR_set` when it is positive.
- `controls_state()` reports `RR` from `ventilator_RR_set` when present, preserving UI round-trip behavior.

## Observed Response After Fix

Scenario: `ventilator_modes_demo`

- Baseline: `RR_total` about 20, `PaCO2` about 33, `EtCO2` about 28.
- `set_rr = 35`: `RR_total` about 35, `PaCO2` about 21, `EtCO2` about 15.
- `set_rr = 12`: `RR_total` about 12, `PaCO2` about 40, `EtCO2` about 30.

PEEP/Paw response remained bidirectional and visible in `waveform_fast`.

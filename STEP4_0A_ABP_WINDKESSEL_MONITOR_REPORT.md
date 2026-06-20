# PCCSim v3.1 — Step 4.0A ABP/SBP-DBP monitor coupling

## Scope

This step intentionally skipped antibiotics and moved to the monitor/UI roadmap.

Implemented only:

- expose real bedside `SBP`/`DBP` values from model arterial pressure outputs;
- use those values in API bedside/waveform profiles;
- draw the ABP waveform from `SBP`/`DBP` rather than a cosmetic MAP-derived amplitude;
- display a small `SBP/DBP` pair under the MAP vital.

Not implemented here:

- real EtCO2;
- labs strip;
- sparkline trends;
- alarm thresholds;
- scenario brief card;
- simulation speed indicator;
- complete drugs or calculated-parameters windows.

## Rationale

Before this step, the waveform profile and canvas could fall back to:

- `SBP = MAP + 20`
- `DBP = MAP - 15`

and the ABP curve used a fixed cosmetic amplitude derived from MAP. This could produce an educationally confusing mismatch: for example a low MAP could still look visually like a relatively preserved arterial waveform.

## Changes

### Bus schema

Added:

- `SBP`
- `DBP`
- `arterial_pulse_pressure`
- `arterial_pressure_source`

`SAP`/`DAP` are kept for backward compatibility.

### CirculationModule

`CirculationModule` now writes:

- `SAP`
- `DAP`
- `SBP`
- `DBP`
- `arterial_pulse_pressure`
- `arterial_pressure_source = circulation_windkessel_envelope`

The current implementation remains an educational pressure envelope derived from the circulation state, stroke volume, compliance and arterial load. It is not a fully invasive beat-to-beat arterial line model.

### API profiles

`bedside`, `bedside_fast`, `waveform`, and `waveform_fast` now prefer model arterial values:

1. `SBP`/`DBP` if present;
2. `SAP`/`DAP` aliases if present;
3. MAP fallback only if neither exists.

### UI waveform

`ui/canvas_waveforms.js` now draws ABP from:

- `SBP`/`DBP`, or
- `SAP`/`DAP` aliases.

The previous MAP-centered cosmetic baseline/amplitude has been removed.

### Bedside monitor

The MAP tile now displays a small `SBP/DBP` pair below the MAP value.

## Tests

Added:

- `tests/test_v315_abp_windkessel_monitor_contract.py`

Checks:

- Circulation exposes `SBP`/`DBP` and pulse pressure.
- Waveform profiles use model pressure values, not `MAP + 20` and `MAP - 15`.
- Bedside profiles expose the ABP pair for UI rendering.
- API waveform profile returns `SBP`/`DBP`.
- Canvas code consumes `SBP`/`DBP` and no longer uses cosmetic MAP baseline logic.

Executed targeted regression group:

- Step 4.0A ABP tests
- Step 3.9 insulin tests
- Step 3.8 furosemide tests
- Step 3.7 steroids tests
- Step 3.6 respiratory drugs/iNO tests
- Step 3.5 rocuronium tests
- Step 3.4D alpha-2 tests
- Step 3.4C ketamine tests
- Step 3.4B GABA sedatives tests
- Step 3.4A opioid tests
- Step 3.3 vasoactive tests
- Step 3.2 drug MAP direction tests
- Step 3.1 drug controls tests
- Step 3.0 UI bidirectionality/reactivity tests
- API/web monitor/training/instructor tests

Result: 76 passed.

## Next recommended step

Step 4.0B — real EtCO2 physiology, replacing the current `PaCO2 - 5` proxy with a value coupled to alveolar ventilation, dead space/VQ burden and perfusion/CO.

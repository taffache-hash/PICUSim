# Step 4.0B — Real EtCO2 monitor coupling

## Scope

This step replaces the fixed EtCO2 waveform/profile proxy with a model-coupled end-tidal CO2 estimate.

## Previous behavior

The waveform and API profiles derived capnography from:

```text
EtCO2_proxy = PaCO2 - 5
```

This made EtCO2 insensitive to V/Q dead space, shunt/dispersion, low cardiac output and effective alveolar ventilation beyond the already computed PaCO2.

## New behavior

`GasExchangeModule` now writes:

```text
EtCO2
EtCO2_proxy
etco2_pa_gradient
etco2_perfusion_factor
etco2_deadspace_factor
etco2_source
```

The legacy `EtCO2_proxy` key is retained as an alias of `EtCO2` for compatibility.

## Physiologic coupling

EtCO2 now follows PaCO2 but widens the Pa-EtCO2 gradient when:

- effective dead space increases;
- V/Q dispersion increases;
- shunt burden increases;
- cardiac output/pulmonary blood-flow delivery is low;
- effective alveolar ventilation is severely low.

This is an educational/semi-mechanistic capnography contract, not a clinical patient-specific model.

## UI/API changes

- `bedside`, `bedside_fast`, `waveform`, `waveform_fast` and `debug` profiles expose real EtCO2.
- The bedside PaCO2 tile now shows EtCO2 beneath PaCO2.
- Canvas waveform rendering consumes `EtCO2` first and falls back to `EtCO2_proxy` only for legacy payloads.

## Tests

Added:

```text
tests/test_v316_etco2_model_coupling_contract.py
```

The tests verify:

- high dead-space widens the Pa-EtCO2 gradient at fixed PaCO2;
- low cardiac output lowers EtCO2 at fixed PaCO2;
- GasExchangeModule writes EtCO2 and alias fields to the Bus;
- waveform profiles do not recompute fixed PaCO2-5;
- API waveform payload includes real EtCO2;
- UI consumes `EtCO2` before legacy `EtCO2_proxy`.

## Non-goals

This step does not implement:

- labs strip;
- sparkline trends;
- threshold alarms;
- scenario info card;
- all-drugs window;
- calculated hidden-parameter window;
- Docker changes.

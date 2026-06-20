# PCCSim v3.1 — Step 4.42 Organ Perfusion Model

Status: implemented.

## Scope

Step 4.42 adds a bounded educational organ-perfusion layer coupling MAP, CVP, CO, oxygenation and shock burden to kidney/liver perfusion proxies.

This is a simulation scaffold only. It is not a clinical decision tool and does not provide diagnostic, dosing or management recommendations.

## Implemented concepts

- Pediatric MAP low-threshold anchor by age group.
- Organ perfusion pressure proxy: `MAP - CVP`.
- Renal perfusion index and renal hypoperfusion index.
- Hepatic perfusion index and hepatic hypoperfusion index.
- Urine-output trajectory in `mL/kg/h` and `mL/h`.
- Slow creatinine surrogate trajectory and creatinine ratio.
- Lactate-clearance modifier routed through hepatic/organ perfusion.
- GFR modifier from perfusion for downstream modules.
- Instructor-facing warnings for renal/hepatic hypoperfusion.

## Main outputs

- `organ_perfusion_revision = 442`
- `organ_perfusion_pressure_mmHg`
- `pediatric_MAP_low_threshold_mmHg`
- `renal_perfusion_index`
- `hepatic_perfusion_index`
- `renal_hypoperfusion_index`
- `hepatic_hypoperfusion_index`
- `organ_hypoperfusion_burden`
- `urine_output_mL_kg_h`
- `urine_rate_mL_h`
- `creatinine_mg_dL`
- `creatinine_ratio`
- `organ_lactate_clearance_mod`
- `hepatic_lactate_clearance_mod`
- `GFR_mod_from_perfusion`
- `renal_warning`
- `hepatic_warning`

## Contract tests

Implemented in:

- `tests/test_v442_organ_perfusion_contract.py`

Targeted verification:

```bash
pytest -q tests/test_v442_organ_perfusion_contract.py \
  tests/test_v439_shock_engine_contract.py \
  tests/test_v440_epals_decision_engine_contract.py \
  tests/test_v441_intubation_physiology_contract.py
```

Observed result in this package: `12 passed`.

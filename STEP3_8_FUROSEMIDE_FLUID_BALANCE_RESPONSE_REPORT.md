# v3.1 Step 3.8 — Furosemide / fluid-balance response contract

## Scope

This step revises only the renal loop-diuretic pathway:

- furosemide bolus-equivalent counter (`furosemide_mg_kg`)
- furosemide infusion (`furosemide_mg_kg_h`)
- qualitative PK/PD signal
- AKI/renal-delivery audit signal
- final urine-rate and fluid-balance ledger

No ventilator, monitor-waveform, Docker, antibiotic, insulin or general UI-panel logic was changed.

## Problem fixed

The previous implementation could make furosemide act through overlapping pathways:

1. raw cumulative bolus counter in `FluidBalanceModule`
2. PK/PD concentration-effect signal in `PharmacologyModule`
3. `diuretic_response_index` from `AKICRRTModule`

That meant the same dose could be counted more than once. It also risked a persistent diuretic effect from the raw cumulative counter even after PK exposure should have decayed.

## New contract

Ownership is now explicit:

- `PharmacologyModule` owns concentration/effect-site exposure.
- `AKICRRTModule` exposes a renal-adjusted audit response (`diuretic_response_index`).
- `FluidBalanceModule` is the only owner of final `urine_rate_mL_h`, cumulative urine, and final `fluid_balance`.

`FluidBalanceModule` uses `max(diuretic_response_index, local_pk_response)`, not a sum, to avoid double-counting.

## Added audit outputs

- `furosemide_diuresis_signal`
- `furosemide_tubular_delivery_factor`
- `furosemide_effective_diuretic_signal`
- `furosemide_urine_gain`
- `furosemide_additional_urine_mL_h`
- `diuretic_hypovolemia_risk`

## Expected behavior

- Raw bolus counter alone does not drive urine output.
- PK/PD furosemide exposure increases urine output.
- Higher dose gives higher qualitative response.
- AKI/severe hypoperfusion blunts furosemide effect.
- FluidBalance remains the single ledger owner for fluid balance.

## Tests

Added:

- `tests/test_v313_furosemide_fluid_balance_contract.py`

Targeted group result:

- pharmacology/renal contract group: 52 passed
- API/smoke/furosemide legacy group: 19 passed
- total targeted tests run for this step: 71 passed

## Not changed in this step

- UI windows for hidden calculated parameters
- monitor arterial waveform
- insulin
- antibiotics
- Docker packaging

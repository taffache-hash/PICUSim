# Step 3.7 — Steroid response contract

## Scope

This step revises only corticosteroid behaviour:

- hydrocortisone
- dexamethasone

No Docker, UI layout, monitor waveform, antibiotics, insulin, diuretics, or ventilator changes were made.

## Problem found

Steroids already had a delayed PK/PD module, but some downstream modules were also reading raw commanded steroid doses directly:

- `AdvancedSepsisModule` used `hydrocortisone_mg_kg_h` to blunt cytokines and vasoplegia.
- `EndocrineStressAxisModule` used raw hydrocortisone/dexamethasone dose to create exogenous glucocorticoid activity.
- `steroid_SVR_mod` existed but was not consumed by `CirculationModule`, making part of hydrocortisone's vasopressor-sensitizing effect orphaned.

This allowed steroids to behave partly like immediate drugs, which is clinically and pedagogically wrong for this simulator.

## Contract implemented

Steroids now follow this contract:

```text
hydrocortisone / dexamethasone command
→ PK concentration
→ delayed PD effect
→ audit signals
→ downstream sepsis/endocrine/circulation effects
```

Raw commands no longer directly suppress sepsis or activate the endocrine axis.

## New audit signals

Added to `BusState` and emitted by `SteroidsModule`:

```text
hydrocortisone_adrenal_support_signal
hydrocortisone_vasopressor_sensitization_signal
hydrocortisone_antiinflammatory_signal
dexamethasone_antiinflammatory_signal
dexamethasone_ICP_edema_signal
steroid_glucose_signal
steroid_delayed_effect_signal
```

All are delayed/filtered PD signals in the 0–1 range.

## Downstream routing

### AdvancedSepsisModule

Now uses delayed steroid signals for:

- cytokine blunting
- vasoplegia reduction / hydrocortisone vasopressor sensitization

It no longer uses raw hydrocortisone dose as an immediate sepsis modifier.

### EndocrineStressAxisModule

Now uses delayed steroid signals for exogenous glucocorticoid activity.

It no longer uses raw hydrocortisone/dexamethasone command dose as an immediate endocrine activation term.

### CirculationModule

Now consumes `steroid_SVR_mod`, so hydrocortisone's slow SVR/vasopressor-sensitizing effect is no longer orphaned.

## Expected behaviour

### Hydrocortisone

```text
dose ↑
→ C_hydrocort_mcg_mL ↑
→ delayed hydrocortisone_adrenal_support_signal ↑
→ delayed steroid_SVR_mod ↑
→ delayed vasopressor sensitization / MAP support
→ delayed anti-inflammatory effect
→ glucose effect possible over time
```

No immediate adrenaline-like MAP jump should occur.

### Dexamethasone

```text
dose ↑
→ C_dexa_ng_mL ↑
→ delayed anti-inflammatory signal ↑
→ delayed steroid_SIRS_mod ↓
→ delayed steroid_ICP_mod ↓
```

No immediate hemodynamic rescue effect should occur.

## Tests

Added:

```text
tests/test_v312_steroid_response_contract.py
```

The tests verify:

1. hydrocortisone has delayed, not immediate, vasopressor-sensitizing effect;
2. dexamethasone has delayed anti-inflammatory and ICP/edema effects;
3. sepsis reads delayed steroid signals, not raw hydrocortisone dose;
4. endocrine axis reads delayed steroid signals, not raw hydrocortisone/dexamethasone dose;
5. `steroid_SVR_mod` is consumed by CirculationModule.

## Validation run

Targeted validation:

```text
63 passed
```

Groups run:

- steroid response contract
- respiratory drugs / iNO
- rocuronium NMB
- alpha-2 agonists
- ketamine
- GABA sedatives
- opioids
- vasoactives
- drug_MAP_mod direction
- UI/router/controls
- API/web monitor
- training/instructor mode

The full slow suite was not run.

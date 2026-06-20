# PCCSim v3.1 — Step 3.9 insulin/glucose/potassium response contract

## Scope

This step revises insulin only.  It does not change antibiotics, monitor waveforms, Docker packaging, or the future full-drug/calculated-parameter UI windows.

## Clinical/educational contract

Insulin is treated as a delayed metabolic intervention:

- the command is `insulin_UI_h`;
- `PharmacologyModule` converts the command into a delayed concentration/effect-site signal;
- `GlucoseModule` is the sole writer of final `glucose_mmol_L`;
- `AcidBaseElectrolyteModule` is the sole writer of final `K_mmol_L`;
- endocrine and nutrition modules read delayed insulin action signals, not the raw pump command.

This is an educational scaffold and not a clinical insulin dosing model.

## Main fixes

### 1. Removed raw immediate insulin bypass

A raw `insulin_UI_h` command no longer directly lowers glucose when `PharmacologyModule` has not generated an effect-site signal.

### 2. Centralized PK/PD insulin signals

Added or revised:

- `C_insulin_mU_L`
- `insulin_action_signal`
- `insulin_glucose_clearance_signal`
- `insulin_effective_clearance_mmol_L_h`
- `insulin_potassium_shift_signal`
- `insulin_effective_potassium_shift_mmol_L_h`
- `insulin_hypoglycemia_risk`
- `insulin_glucose_safety_factor`
- `insulin_potassium_safety_factor`
- `insulin_effect_revision = 319`

### 3. Glucose safety taper

The glucose-lowering effect is progressively tapered when glucose approaches hypoglycemic values.  Hypoglycemia risk rises when insulin effect is present and glucose is low.

### 4. Potassium safety taper

The potassium intracellular-shift effect is expressed as an effect-site shift rate and is tapered near hypokalemia.  Final potassium remains owned by `AcidBaseElectrolyteModule`.

### 5. Downstream modules no longer use raw insulin acutely

`EndocrineStressAxisModule` and `Nutrition/CatabolismModule` now read delayed insulin action signals for stress-hyperglycemia/refeeding logic rather than directly reacting to the raw pump command.

## Files changed

- `core/bus.py`
- `modules/pharmacology/pk_pd.py`
- `modules/nutrition/glucose.py`
- `modules/acidbase/electrolytes.py`
- `modules/endocrine/stress_axis.py`
- `modules/nutrition/catabolism.py`
- `api/state_profiles.py`
- `tests/test_v314_insulin_glucose_potassium_contract.py`
- `VERSION`
- `CHANGELOG.md`
- `docs/PCCSIM_V3_1_PHARMACOLOGY_AND_UI_ROADMAP.md`

## Tests

Targeted validation groups executed:

- Step 3.9 insulin/glucose/potassium contract
- Legacy v1.16 insulin PK/PD tests
- Step 3.8 furosemide/fluid balance
- Step 3.7 steroids
- Step 3.6 respiratory drugs/iNO
- Step 3.5 rocuronium/NMB
- Step 3.4D alpha-2 agonists
- Step 3.4C ketamine
- Step 3.4B GABA sedatives
- Step 3.4A opioids
- Step 3.3 vasoactives
- Step 3.2 drug_MAP_mod direction
- Step 3.1 drug control surface
- Step 2 UI/backend bidirectionality
- Step 1 live controls
- API/web monitor/training/instructor smoke tests

Result: 76 targeted tests passed.

UI syntax check: `node --check ui/app.js` passed.

The complete slow suite was not run in this step.

## Remaining work

- Step 3.10: antibiotics — vancomycin and piperacillin-tazobactam.
- Step 4.0: all-drugs control window.
- Step 4.1: calculated-parameters window for hidden Bus/audit values.
- Step 4.2: per-drug audit panel.
- Step 4.3: hemodynamic monitor/arterial waveform cleanup.

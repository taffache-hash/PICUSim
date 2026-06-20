# v1.16-alpha — Insulin / Glucose PD scaffold

This release adds insulin as a central PharmacologyModule drug and connects it to the existing glucose and potassium physiology.

## Scope

Educational, qualitative model only. It is not a dosing model and must not be used for clinical insulin titration.

## Inputs

- `insulin_UI_h`: insulin infusion in U/h
- `glucose_mmol_L`: current glucose state
- `GIR_mg_kg_min`: glucose infusion rate

## Outputs

- `C_insulin_mU_L`
- `insulin_glucose_clearance_signal`
- `insulin_potassium_shift_signal`
- `insulin_hypoglycemia_risk`
- `insulin_effective_clearance_mmol_L_h`
- `insulin_effect_revision = 116`

## Coupling

- `GlucoseModule` uses the PK/PD signal when available and falls back to the older direct-infusion effect otherwise.
- `AcidBaseElectrolyteModule` uses the insulin potassium shift signal when available.

## Limitations

No endogenous insulin secretion, subcutaneous absorption, pancreas model, counter-regulatory glucagon model, nutrition-specific insulin protocols, or clinical dosing targets are included.

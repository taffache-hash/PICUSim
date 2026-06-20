# PK/PD Furosemide Scaffold — v1.13-alpha

This update adds furosemide as an educational renal-pharmacology layer.

## Model structure

- One-compartment concentration model.
- Allometric volume and clearance scaling.
- Renal-function-dependent clearance and qualitative effect.
- Bolus-equivalent input through `furosemide_mg_kg`.
- Continuous infusion input through `furosemide_mg_kg_h`.
- CRRT-lite audit clearance using the same public effluent-rate framework used for other drugs.

## Main outputs

- `C_furosemide_mg_L`
- `furosemide_effect_signal`
- `furosemide_renal_clearance_factor`
- `diuretic_response_index`
- `urine_output_mL_kg_h`
- `fluid_overload_percent`
- `pk_crrt_furosemide_CL_L_min`

## Educational use

The purpose is to show how the same dose exposure can produce a different diuretic response depending on renal perfusion, AKI severity and CRRT status.

## Not for clinical use

This is not a therapeutic drug monitoring model and not a prescribing aid. Local protocols, TDM where applicable, renal consultation and clinical judgment remain mandatory.

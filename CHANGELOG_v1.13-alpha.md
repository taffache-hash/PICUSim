# v1.13-alpha — Furosemide PK/PD scaffold

This public-clean release extends the pharmacology roadmap with an educational furosemide model.

## Added

- `C_furosemide_mg_L` concentration output.
- `furosemide_mg_kg_h` continuous infusion input.
- Existing `furosemide_mg_kg` cumulative counter is also interpreted as bolus-equivalent exposure for PK.
- `furosemide_effect_signal` qualitative PD output.
- `furosemide_renal_clearance_factor` audit output.
- `pk_crrt_furosemide_CL_L_min` CRRT-lite audit output.
- Scenario `picu_furosemide_fluid_overload_v1_13.yaml`.
- Audit tool `tools/pkpd_furosemide_audit_v1_13.py`.
- Regression tests `tests/test_v113_furosemide_pkpd.py`.

## Limitations

The model is educational and qualitative. It does not provide dosing advice and does not model tubular secretion saturation, albumin binding, ototoxicity, nephrocalcinosis or detailed electrolyte depletion.

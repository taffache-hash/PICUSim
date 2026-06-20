# PK/PD Morphine Scaffold — v1.14-alpha

This public educational layer adds morphine to the centralized `PharmacologyModule`.

## Scope

The implementation is intentionally qualitative:

- one-compartment parent-drug PK;
- pediatric allometric volume and clearance scaling;
- analgesia signal;
- respiratory-depression signal;
- renal-impairment risk proxy for active glucuronide metabolite accumulation;
- CRRT-lite audit field.

It is not a clinical dosing model, not a therapeutic drug monitoring model and not a medical device.

## Outputs

- `C_morphine_ng_mL`
- `morphine_analgesia_signal`
- `morphine_resp_depression_signal`
- `morphine_renal_accumulation_risk`
- `M6G_accumulation_proxy`
- `pk_crrt_morphine_CL_L_min`

## Ownership

From v1.14 onward, morphine plasma concentration is owned by `PharmacologyModule` when available.
`PainStressSedationModule` keeps a local fallback for standalone use but does not overwrite the centralized concentration when `pk_extension_revision >= 114`.

## Known limitations

- M3G/M6G are not modeled as true measured compartments.
- Renal impairment changes are qualitative.
- Genetic transporter/enzyme covariates are not implemented.
- No patient-specific dosing advice is implied.

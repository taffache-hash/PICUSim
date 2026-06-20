# PK/PD Clonidine Scaffold — v1.15-alpha

This release adds clonidine to the centralized `PharmacologyModule` as a public educational PK/PD scaffold.

## Scope

Clonidine is represented as a slow one-compartment alpha-2 agonist model with qualitative outputs for:

- plasma concentration (`C_clonidine_ng_mL`),
- sedation signal,
- sympatholysis signal,
- bradycardia-risk signal,
- hypotension-risk signal,
- withdrawal-modulation signal,
- CRRT-lite extracorporeal clearance field.

## Important limitation

This is not a clinical dosing model. It does not predict patient-specific hemodynamic adverse events and must not be used for prescribing or dose adjustment.

## Coupling

`PainStressSedationModule` now reads centralized clonidine PK when `pk_extension_revision >= 115`. A local fallback remains only for standalone module use.

## Scenario

`scenarios/picu_clonidine_withdrawal_weaning_v1_15.yaml` demonstrates sedative weaning with clonidine introduction and qualitative withdrawal-risk modulation.

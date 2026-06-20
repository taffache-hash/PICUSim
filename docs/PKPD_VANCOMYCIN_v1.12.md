# PK/PD Vancomycin Scaffold — v1.12-alpha

This release starts the new pharmacology-expansion roadmap by adding a public educational vancomycin model to the existing allometric PK/PD layer.

## Scope

Vancomycin is represented as a one-compartment total plasma concentration model with:

- allometric volume scaling;
- allometric baseline clearance scaling;
- dynamic renal-function modifier based on simulated GFR / baseline GFR;
- AKI-stage and shock-lactate penalties;
- CRRT-lite extracorporeal clearance through the existing effluent-rate/sieving proxy;
- qualitative concentration/MIC target-attainment proxy;
- qualitative contribution to `antibiotic_coverage` for the infection module.

## New Bus fields

```text
vancomycin_mg_kg_h
C_vancomycin_mg_L
vancomycin_target_attainment
vancomycin_coverage_mod
vancomycin_renal_clearance_factor
pk_crrt_vancomycin_CL_L_min
```

## New scenario

```text
scenarios/picu_vancomycin_aki_crrt_v1_12.yaml
```

The scenario uses a compressed educational loading phase followed by a maintenance-equivalent infusion and then starts CRRT. This is not a prescribing scheme.

## New audit tool

```bash
python tools/pkpd_vancomycin_audit_v1_12.py --fail-on-review
```

The audit compares normal renal function, AKI, AKI+CRRT, infant and adolescent cases. It verifies that AKI increases exposure, CRRT adds extracorporeal clearance, and target-attainment remains bounded.

## Limitations

This is not a therapeutic drug monitoring model. It does not implement:

- intermittent peak/trough sampling;
- Bayesian AUC estimation;
- unbound concentration;
- nephrotoxicity feedback;
- dynamic MIC uncertainty;
- filter adsorption, membrane type, filter age or CRRT downtime;
- validated dosing recommendations.

Use only for educational simulation and software testing.

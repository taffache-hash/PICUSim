# Shock Engine — v3.1 Step 4.39

Educational shock phenotype scaffold for the Pediatric Critical Care Simulation Framework.

## Scope

Step 4.39 adds a bounded `ShockModule` that translates scenario-level shock drivers into modifier fields consumed by existing physiology modules:

- `shock_SVR_mod` for systemic vascular tone;
- `shock_preload_mod` for venous return/preload;
- `shock_contractility_mod` for myocardial depression;
- `shock_HR_add` and `shock_sympathetic_tone` for compensation;
- `shock_lactate_prod_mod` and `shock_lactate_clearance_mod` for lactate kinetics;
- phenotype indices for vasoplegia, hypovolemia, low output and obstruction.

Supported educational phenotypes are distributive, hypovolemic, cardiogenic, obstructive and mixed shock.

## Non-goals

- No treatment algorithm or dose recommendation.
- No bedside decision support.
- No replacement of existing sepsis, baroreflex, circulation, heart or metabolism ownership rules.
- No validated clinical prediction model.

## Integration contract

`ShockModule` writes modifiers only. Final variables remain owned by existing modules:

- `CirculationModule`: MAP/SVR/CVP/venous-return effects.
- `BaroreflexModule`: final displayed HR.
- `HeartModule`: SV/CO with contractility modifier.
- `MetabolismModule`: final lactate after production/clearance modifiers.

The module is intentionally bounded to avoid runaway MAP/CO/lactate behavior during long educational scenarios.

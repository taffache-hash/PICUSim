# EPALS-like Decision Engine — v3.1 Step 4.40

Educational/non-clinical pattern-recognition layer for the PCCSim v3.1 roadmap.

## Purpose

The module reads current Bus physiology and intervention markers and writes instructor-facing prompts around:

- ABCDE priority bucket;
- arrest/shock/airway-breathing/metabolic pattern recognition;
- contextual flags for debriefing;
- incoherence warnings when the simulated state and action markers diverge.

It is intentionally not a clinical decision support tool and does not provide drug doses.

## Main file

- `modules/decision/epals.py`

## Bus outputs

- `decision_engine_revision = 440`
- `decision_priority`
- `decision_pattern`
- `decision_pattern_confidence`
- `decision_recommendation_primary`
- `decision_recommendation_secondary`
- `decision_warning`
- `decision_warning_level`
- `decision_abcde_step`
- `decision_escalation_needed`
- `decision_context_flags`
- `decision_last_update_s`

## Recognized pattern branches

Priority order:

1. Cardiac arrest.
2. Airway/breathing emergency.
3. Circulation/shock.
4. Hyperkalemia risk.
5. Hypoglycemia.
6. Hypercarbic ventilatory failure.
7. Routine monitoring.

## Contract tests

- `tests/test_v440_epals_decision_engine_contract.py`

Covered checks:

- hypoxemia with disconnected ventilator triggers A/B priority and high warning;
- distributive shock with infection marker and no antibiotic flag triggers circulation priority and warning;
- cardiac arrest without CPR marker triggers critical warning.

# PCCSim v3.1 — Step 4.48 Recovery Engine

Purpose: make correct rescue actions visibly recover physiology after the critical-event trigger.

Implemented behavior:

- scenarios can declare `recovery_engine.enabled: true`;
- recovery is anchored to the first corrective action after the critical-event trigger;
- first response, partial response and near-baseline times are exposed in metadata;
- recovery perturbations can reduce shock indices and improve oxygenation/perfusion/lactate surrogates;
- multiplier perturbations such as `lactate_multiplier`, `SaO2_multiplier`, `PaCO2_multiplier` are audited and immediately applied to the base variable.

The layer is educational only. It is intended to show that early correct treatment improves recovery probability and speed; it is not a clinical response model.

## Phenotype presets

- septic shock
- anaphylaxis
- tamponade/obstructive shock
- DKA/dehydration shock
- bronchiolitis/respiratory failure
- generic fallback

## Timing logic

Recovery does not start at scenario start. It starts after a correct action performed after the critical event. This keeps the Step 4.45 timing concept intact: stable child → critical trigger → timed rescue window → recovery if treatment is appropriate.

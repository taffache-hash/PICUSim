# v3.2.0 public polish Step 7 — RC2 external-review fixes

Status: local `3.2.0-public-rc2` release-candidate; GitHub/Zenodo upload not performed in this step.

This step addresses the independent RC1 review that focused on full-suite behavior, public-demo physiology, and fragile historical test contracts.

## Confirmed and fixed findings

### 1. DKA oxygen/Fick death spiral

The RC1 `epals_v2_dka_dehydration_shock` scenario could collapse to extreme simulated desaturation shortly after scenario start. The root cause was an educational-scenario mismatch: a DKA/Kussmaul physiology scenario was still being run through a ventilator-pressure-control pathway, producing inadequate effective ventilation and a Fick-like oxygen-delivery collapse.

RC2 changes:

- configured DKA as spontaneous/unassisted room-air physiology;
- added scenario-level chemoreflex parameters for Kussmaul-style respiratory drive;
- allowed `run_simulation.py` to read scenario-specific chemoreflex parameters;
- added an RC2 regression test preventing recurrence of the oxygen death spiral.

Observed RC2 pattern: SaO2 remains >=95%, PaCO2 remains low/compensatory, pH remains acidemic, and K starts pathologic.

### 2. Tension pneumothorax teaching pattern

The RC1 tension pneumothorax scenario did not show a sufficiently visible pre-intervention deterioration phase before decompression. RC2 adds explicit deterioration proxies before the decompression event and fixes airway-obstruction/shunt command persistence so timeline perturbations are not immediately overwritten by the airway module.

RC2 changes:

- added early obstructive-shock deterioration perturbations to `epals_tension_pneumothorax.yaml`;
- preserved external `airway_shunt_add` commands in `AirwayObstructionModule`;
- retained recovery perturbations after decompression;
- added an RC2 regression test requiring deterioration followed by recovery.

Observed RC2 pattern: SaO2 and MAP deteriorate before decompression and recover afterward.

## Findings not reproduced as integrated engine bugs

### Hyperkalemia baseline

The integrated RC2 scenario path starts `epals_hyperkalemia_aki` at K >=6.5 mmol/L and then improves. The earlier suspected K overwrite was already addressed by robust electrolyte baseline initialization. RC2 adds a direct integrated regression test so this cannot regress silently.

### Norepinephrine/MAP visibility in sepsis

The integrated short septic-acidosis scenario shows visible norepinephrine exposure and a MAP rise after norepinephrine. RC2 adds a regression test requiring a short-horizon MAP increase after norepinephrine.

## Historical/audit test policy updates

The independent review identified historical tests that treated REVIEW-class audit rows as hard failures. RC2 updates those tests so they remain informative but do not fail the public release when there are zero hard FAIL rows:

- `test_v119_score_assumption_hardening.py` now treats the legacy v1.19 score-assumption registry as a partial audit layer under v3.2, not as a complete registry for all later score-like fields.
- `test_v1221_epals_5h_scenarios.py` and `test_v1222_epals_5t_scenarios.py` now require zero FAIL rows and allow at most one REVIEW row.
- `state_profiles.py` keeps the explicit legacy `Pmean` alias formula visible for source-level HF4 tests, while still preferring `Paw_mean` when available.

## Regression files added or updated

- `tests/test_v320_public_rc2_external_review_regressions.py`
- `tests/test_v320_public_rc2_manifest_package.py`
- `tests/test_v119_score_assumption_hardening.py`
- `tests/test_v1221_epals_5h_scenarios.py`
- `tests/test_v1222_epals_5t_scenarios.py`

## Boundary

These changes improve release-facing educational plausibility and test hygiene. They are not clinical validation and do not change the non-clinical safety status of PICUSim.

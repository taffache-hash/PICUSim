# PICUSim v3.2.0 public-polish — Step 1 report

Status: local sandbox work-in-progress. README.md and CITATION.cff intentionally preserved from the GitHub/Zenodo publication baseline in this step.

## Scope

This step targets the most visible reviewer-facing issues identified in v3.1-step5.9:

1. Healthy child gas-exchange over-instability after room-air weaning.
2. Static bicarbonate/base-excess behavior in septic/metabolic scenarios.
3. Missing/unclear shock metadata in clinical shock scenarios.
4. New clinically sane tests for golden public scenarios.

## Code changes

### Gas exchange

Files changed:

- `modules/respiratory/gas_exchange.py`
- `run_simulation.py`

Changes:

- Lowered normal-lung baseline shunt and dead-space assumptions.
- Reduced mild derecruitment contribution to shunt/dead space.
- Replaced the previous `1 - SaO2` shunt initializer with a safer formula based on deviation below 0.97 only.
- Preserved the original v1.20 adaptive V/Q revision string while adding a v3.2 public-polish marker.

### Acid-base

File changed:

- `modules/acidbase/electrolytes.py`

Changes:

- Added a faster acute metabolic HCO3 trend for lactate/microcirculatory-failure/leak states.
- Increased lactate and sepsis acidification gains for educational visibility.
- Kept slow renal compensation for near-normal states.

### Shock metadata

Files changed/added:

- `core/scenario.py`
- `modules/cardiovascular/shock_labels.py`
- `modules/cardiovascular/__init__.py`
- `run_simulation.py`

Changes:

- Added scenario-level shock metadata inference for sepsis, pneumothorax, high-PEEP/obstructive, hemorrhagic/hypovolemic and mixed low-perfusion patterns.
- Added `ShockLabelModule`, a lightweight label-only module that updates `shock_type`, `shock_stage`, and `shock_severity` without writing hemodynamic modifiers.
- Deliberately did not activate the pre-existing full `ShockModule` in public scenarios, because it over-penalized MAP/CO when added late to legacy scenarios.

### Tests

File added:

- `tests/test_v320_public_polish_contracts.py`

New contracts:

- Healthy child remains clinically sane after room-air wean.
- Tension pneumothorax preserves recovery pattern and obstructive-shock label.
- Excessive PEEP reduces CO/MAP and flags obstructive shock.
- Septic shock has distributive-shock label and visible metabolic component.

## Golden scenario sweep after Step 1

| Scenario | Final SaO2 % | Min SaO2 % | PaCO2 | pH | HCO3 | BE | MAP final/min | CO final/min | Shock label |
|---|---:|---:|---:|---:|---:|---:|---|---|---|
| healthy_child_20kg | 94.0 | 93.9 | 43.6 | 7.35 | 24.0 | -0.7 | 70.4 / 67.8 | 4.58 / 4.21 | none / none |
| neonatal_rds_3kg | 96.5 | 88.0 | 62.3 | 7.20 | 24.0 | -3.0 | 43.8 / 41.7 | 0.75 / 0.75 | none / none |
| septic_shock | 86.9 | 80.7 | 96.2 | 6.97 | 21.8 | -8.6 | 39.3 / 25.0 | 6.25 / 4.90 | distributive / critical |
| septic_shock_refractory | 82.5 | 76.6 | 101.3 | 6.91 | 20.2 | -11.0 | 31.8 / 25.0 | 5.00 / 3.14 | distributive / critical |
| counterfactual_excessive_PEEP_ARDS | 91.4 | 90.0 | 61.3 | 7.21 | 24.0 | -2.9 | 25.0 / 25.0 | 2.88 / 2.05 | obstructive / critical |
| epals_hyperkalemia_aki | 99.4 | 96.5 | 36.3 | 7.33 | 18.9 | -6.2 | 50.3 / 48.4 | 7.50 / 6.87 | none / none |
| epals_tension_pneumothorax | 99.7 | 92.0 | 41.0 | 7.38 | 24.0 | -0.3 | 47.1 / 25.0 | 4.00 / 1.44 | obstructive / decompensated |
| near_fatal_status_asthmaticus | 96.6 | 92.0 | 104.3 | 6.97 | 24.0 | -6.3 | 67.2 / 61.9 | 7.50 / 6.37 | none / none |
| infant_bronchiolitis | 92.4 | 85.1 | 105.0 | 6.97 | 24.0 | -6.3 | 65.0 / 56.2 | 2.00 / 1.75 | none / none |

## Test results

Targeted regression suite:

- `tests/test_v320_public_polish_contracts.py`
- `tests/test_public_smoke.py`
- `tests/test_v120_vq_adaptive_dispersion.py`
- `tests/test_v316_etco2_model_coupling_contract.py`
- `tests/test_v439_shock_engine_contract.py`
- `tests/test_v440_epals_decision_engine_contract.py`
- `tests/test_v500c_plausibility_guardrails.py`
- `tests/test_v200_api_server.py`
- `tests/test_v210_web_monitor.py`
- `tests/test_v301_ui_live_controls.py`
- `tests/test_v302_ui_backend_bidirectional.py`
- `tests/test_v332_emogas_panel_contract.py`
- `tests/test_v333_emogas_full_autorefresh_contract.py`
- `tests/test_v335_ui_human_pass_contract.py`
- `tests/test_v451_monitor_layout_compression_contract.py`

Result: 42 passed.

A full repository-wide pytest excluding release-archive tests was started but exceeded the sandbox execution window before completion. No additional failure was observed before timeout.

## Remaining issues for next steps

1. PaCO2 still visibly hits 105 in bronchiolitis and remains >100 in near-fatal asthma/refractory sepsis.
2. HR still often reaches high ceilings in severe scenarios.
3. Neonatal RDS now oxygenates slightly generously after optimization; acceptable for a treated/stabilized teaching scenario but should be rechecked.
4. README.md and CITATION.cff are not yet updated for v3.2.0, by design.
5. Public release-archive tests still need a dedicated fix/split between repository-only and public-package tests.

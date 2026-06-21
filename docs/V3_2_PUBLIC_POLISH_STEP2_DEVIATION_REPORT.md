# PICUSim v3.2.0-public-polish — Step 2 deviation report

Date: 2026-06-20

Scope: targeted deviation from the v3.2 roadmap to examine additional review findings reported after the Step 1 local package.

README.md and CITATION.cff were intentionally left unchanged in this step.

## Review findings examined

1. Possible `K_mmol_L` reset in hyperkalaemia scenarios.
2. Norepinephrine visibility in short septic-shock simulations.
3. `set_antibiotic_effect` being ineffective/overwritten in integrated sepsis scenarios.
4. Paw numeric oscillation in sampled CLI/API output.

## Changes made

### 1. AcidBaseElectrolyteModule baseline preservation

File changed:

- `modules/acidbase/electrolytes.py`

The integrated scenario path already started `epals_hyperkalemia_aki` at K=6.8 mmol/L in Step 1, so the bug was not reproduced in the full scenario runner. However, the module-level fragility was real: when an isolated module was initialized against a default bus, explicit `K_baseline`, `Na_baseline`, `Cl_baseline`, and `HCO3_baseline` could be overwritten by default bus values.

Fix: `initialize()` now prefers explicit module baseline parameters for Na/K/Cl/HCO3.

Added contract:

- `test_v320_acidbase_initialize_preserves_param_baselines_when_bus_has_defaults`

### 2. Direct antimicrobial-effect perturbation preservation

File changed:

- `modules/infection/antimicrobial_basic.py`

In `epals_acidosis_septic_shock`, the timeline uses `set_antibiotic_effect`. The infection module previously recomputed `antibiotic_effect` from coverage/source-control and could overwrite this direct instructor-level proxy on the next step.

Fix: the model-derived antimicrobial effect is still computed, but a direct bus/timeline `antibiotic_effect` is preserved as a floor.

Added contract:

- `test_v320_direct_antibiotic_effect_perturbation_is_not_overwritten`

### 3. Short-horizon norepinephrine visibility in sepsis

File changed:

- `modules/sepsis/advanced_sepsis.py`

Norepinephrine response was already visible after Step 1 in the tested integrated scenarios, but the vasoplegia/cytokine term still tended to keep worsening over short EPALS time windows.

Fixes:

- Increased bounded catecholamine attenuation of vasoplegia from a weak 0.12 term to a still-bounded 0.28 term.
- Added a mild antibiotic/source-control cytokine-target blunt. This does not rapidly cure infection, but it prevents treatment from being completely invisible over 5-10 minute educational simulations.

Added contract:

- `test_v320_norepinephrine_visibly_raises_map_in_short_septic_shock_scenario`

### 4. Stable Paw numeric display alias

Files changed:

- `core/bus.py`
- `modules/ventilator/ventilator.py`
- `api/state_profiles.py`

The instantaneous `Paw` waveform is not wrong; it naturally alternates between inspiratory and expiratory phases depending on sampling. For numeric monitor/CLI display, however, this can look like instability.

Fix: keep `Paw` and `Paw_current` as instantaneous mechanics variables, but add:

- `Paw_mean`
- `Paw_display`

The API bedside profiles now display `Paw_display` while full/waveform views can still access instantaneous waveform pressure.

Added contract:

- `test_v320_numeric_paw_display_uses_stable_mean_alias_not_instantaneous_waveform_only`

## Spot-check values after Step 2

### `epals_hyperkalemia_aki`

- Initial K: 6.8 mmol/L
- Final K: ~5.13 mmol/L
- HCO3: ~17 → ~18.9 mmol/L

Interpretation: starts hyperkalaemic and improves after temporizing/CRRT proxy interventions.

### `epals_acidosis_septic_shock`

Approximate integrated values with dt=1s spot-check:

- MAP before norepinephrine window: ~25 mmHg
- MAP after norepinephrine: ~44-46 mmHg
- `antibiotic_effect` after direct perturbation: 0.35
- `source_control` after perturbation: 0.35
- `Paw`: instantaneous value preserved
- `Paw_display`: stable cycle-level mean alias (~12.25 cmH2O in the tested PCV scenario)

Interpretation: norepinephrine now produces a visible short-horizon MAP response, while antibiotics/source control stabilize the trajectory without unrealistic immediate cure.

## Tests run

Targeted deviation + v3.2 public polish contracts:

```text
9 passed
```

Expanded public/API/UI/physiology subset:

```text
28 passed
16 passed
```

Total targeted checks executed in this step:

```text
44 passed, 0 failed
```

Suites included:

- `tests/test_public_smoke.py`
- `tests/test_v320_public_polish_contracts.py`
- `tests/test_v320_public_polish_deviation_contracts.py`
- `tests/test_v443_advanced_vasoactive_engine_contract.py`
- `tests/test_v305_vasoactive_response_contract.py`
- `tests/test_v440_epals_decision_engine_contract.py`
- `tests/test_v500c_plausibility_guardrails.py`
- `tests/test_v332_emogas_panel_contract.py`
- `tests/test_v335_ui_human_pass_contract.py`
- `tests/test_v200_api_server.py`
- `tests/test_v210_web_monitor.py`
- `tests/test_v301_ui_live_controls.py`
- `tests/test_v302_ui_backend_bidirectional.py`
- `tests/test_v303_drug_control_surface.py`
- `tests/test_v451_monitor_layout_compression_contract.py`

## Files changed in Step 2

- `core/bus.py`
- `modules/acidbase/electrolytes.py`
- `modules/infection/antimicrobial_basic.py`
- `modules/sepsis/advanced_sepsis.py`
- `modules/ventilator/ventilator.py`
- `api/state_profiles.py`
- `tests/test_v320_public_polish_deviation_contracts.py`
- `docs/V3_2_PUBLIC_POLISH_STEP2_DEVIATION_REPORT.md`

## Files intentionally unchanged

- `README.md`
- `CITATION.cff`

SHA256 after this step:

```text
README.md   bab1bdccbf84d87558c35cc6505dfbf43ed9f00356bb9a11bab3b2101146937b
CITATION.cff b16dd39207ac46388d897abcab50c0d42696ed2253e2fa65b37603dc2c4fc5d9
```

## Remaining issues

1. HR ceiling remains visually prominent in severe sepsis scenarios.
2. Some obstructive/bronchiolitis/asthma scenarios still reach high PaCO2 caps.
3. Public release archive tests still need repo-only/public-package separation.
4. UI basic mode remains pending.


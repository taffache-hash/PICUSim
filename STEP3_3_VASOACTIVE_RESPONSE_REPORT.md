# Step 3.3 — Vasoactive Response Cleanup

## Scope

This step is intentionally limited to the main vasoactive/inodilator controls:

- noradrenaline
- adrenaline
- dopamine
- vasopressin
- milrinone

No new drugs, Docker changes, waveform-rendering changes or ventilator corrections are included in this step.

## Main problem addressed

Before this step, catecholamine effects were spread across overlapping pathways:

1. direct dose effects inside `CirculationModule`,
2. concentration-based PK/PD effects inside `PharmacologyModule`,
3. disease-specific support terms inside `AdvancedSepsisModule`,
4. heart rate effects that changed cardiac output without changing the displayed bedside HR.

This could make the monitor response appear non-linear or non-intuitive, especially after adrenaline/noradrenaline commands.

## Changes made

### 1. Primary vasoactive vascular tone isolated in `CirculationModule`

`modules/cardiovascular/circulation.py` now uses a clearer saturable response contract:

- noradrenaline: primary alpha-1 SVR/MAP support,
- vasopressin: vasoplegia/SVR support,
- adrenaline: mixed alpha/beta with smaller direct SVR effect,
- dopamine: little direct SVR at low/moderate dose; alpha tone only at higher dose,
- milrinone: inodilator pattern, lower SVR with modest direct CO support.

The module now also writes:

- `vasoactive_SVR_mod`
- `vasoactive_CO_mod`

These are audit variables for verifying the vasoactive pathway.

### 2. Catecholamine MAP double-counting removed from `PharmacologyModule`

`modules/pharmacology/pk_pd.py` no longer adds adrenaline/dopamine directly to `drug_MAP_mod`.

`drug_MAP_mod` remains for non-vasoactive MAP modifiers such as ketamine, propofol and midazolam.

Catecholamine concentration still contributes to:

- `drug_HR_mod`
- `drug_inotropy_mod`

### 3. `HeartModule` now consumes `drug_inotropy_mod`

`modules/cardiovascular/heart.py` now applies `drug_inotropy_mod` to LV/RV elastance. This makes inotropy affect stroke volume/cardiac output through the heart rather than through an extra circulation-level CO multiplier.

### 4. Displayed HR and cardiac output alignment improved

`BaroreflexModule` now reads `drug_HR_mod`, so pharmacologic chronotropy changes the displayed bedside HR instead of only affecting cardiac output internally.

`HeartModule` no longer multiplies HR by `drug_HR_mod` again. This avoids double-counting and keeps displayed HR and CO more aligned.

## Regression tests added

New test file:

```text
tests/test_v305_vasoactive_response_contract.py
```

The tests verify:

- noradrenaline, adrenaline and vasopressin raise MAP monotonically in an isolated circulation test;
- dopamine has minimal alpha/SVR tone at low dose and stronger tone at high dose;
- milrinone behaves as an inodilator, not as a primary vasopressor;
- `drug_inotropy_mod` increases heart SV/CO/EF through `HeartModule`;
- catecholamine MAP effects are no longer double-counted inside `drug_MAP_mod`.

## Tests run

```text
python -m py_compile modules/cardiovascular/circulation.py modules/cardiovascular/heart.py modules/cardiovascular/baroreflex.py modules/pharmacology/pk_pd.py core/bus.py
pytest test_v305_vasoactive_response_contract.py
pytest test_v304_drug_map_mod_direction.py
pytest test_v303_drug_control_surface.py
pytest test_v302_ui_backend_bidirectional.py
pytest test_v301_ui_live_controls.py
pytest test_v210_web_monitor.py
pytest test_v260_ui_polish_tablet.py
pytest test_v200_api_server.py
pytest test_v220_emergency_training_mode.py
pytest test_v230_instructor_mode.py
```

Result:

```text
31 passed
```

## Known remaining limitations

- The septic shock scenario can still show HR/CO saturation because the scenario starts with very high compensatory tachycardia and high CO.
- The arterial waveform is still cosmetic and remains scheduled for a later monitor-specific step.
- This is still a qualitative educational model, not a clinical dosing or pharmacodynamic model.

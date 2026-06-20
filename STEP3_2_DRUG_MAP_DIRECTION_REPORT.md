# v3.1 Step 3.2 — drug_MAP_mod direction fix

## Scope

This step is deliberately narrow. It fixes the cardiovascular sign/direction bug identified during the audit.

Changed file:

- `modules/cardiovascular/circulation.py`

Added test:

- `tests/test_v304_drug_map_mod_direction.py`

## Bug

Before this step, the systemic Windkessel model used:

```python
R_sys_eff = R_sys / MAP_drug_mod
```

That made `drug_MAP_mod > 1` reduce effective systemic resistance and therefore lower steady-state MAP. This was opposite to the documented intent.

## Fix

The model now uses:

```python
R_sys_eff = R_sys * MAP_drug_mod
```

This makes the direction physiologically and semantically consistent:

- `drug_MAP_mod > 1` increases effective systemic resistance and MAP.
- `drug_MAP_mod < 1` decreases effective systemic resistance and MAP.

## Isolated response test

With stable CO and non-drug modifiers, the regression test verifies monotonic response:

| drug_MAP_mod | Expected direction |
|---:|---|
| 0.8 | lower MAP |
| 1.0 | baseline MAP |
| 1.2 | higher MAP |
| 1.5 | much higher MAP |

## Explicitly not changed

- No UI changes.
- No Docker changes.
- No additional drug controls.
- No arterial waveform rewrite.
- No recalibration of adrenaline/noradrenaline dose-response curves.
- No removal of duplicate vasoactive pathways.

## Next step candidate

Step 3.3 should address the remaining hemodynamic interpretability issue: duplicated/overlapping vasoactive pathways between direct CirculationModule effects and PK/PD effect-site modifiers.

# PICUSim v3.2.0-public polish — Step 3 FiO2 control fix

## Scope

This step addresses the observed UI/API behavior where changing FiO2 appeared to snap back to 21% or to the previous value.

README.md and CITATION.cff were not modified in this step.

## Root cause

The simulator used `FiO2` ambiguously as both:

1. the commanded oxygen set-point, and
2. the delivered/effective FiO2 after oxygen interface efficiency and leak.

This was mostly invisible in intubated ventilator scenarios, because commanded and delivered FiO2 are often identical. It became visible in HFNC, low-flow oxygen, and NIV scenarios:

- `set_fio2` changed only `FiO2`;
- AirwayInterfaceModule used interface-specific set-points such as `HFNC_FiO2_set`, `oxygen_FiO2_set`, or `NIV_FiO2_set`;
- those set-points remained at the previous value, commonly 0.21;
- the next simulation step recalculated delivered FiO2 and overwrote `FiO2`, making the UI look as if FiO2 always returned to room air.

A second UI issue contributed to confusion: the bedside card was labeled as FiO2 set-point but displayed `FiO2_delivered` first, which can remain stale until the next engine step or can be lower than the set-point on non-invasive oxygen interfaces.

## Changes made

### 1. API action router

File changed:

- `api/action_router.py`

`set_fio2` / `set_FiO2` now uses a dedicated handler.

It now:

- accepts both fraction input (`0.8`) and percent input (`80`);
- normalizes and clips to 0.21–1.0;
- always updates the commanded `FiO2`;
- also updates the correct interface-specific set-point:
  - `HFNC_FiO2_set` for HFNC;
  - `NIV_FiO2_set` for NIV;
  - `oxygen_FiO2_set` for low-flow/simple oxygen;
  - ventilator FiO2 for ETT/tracheostomy/ventilator scenarios;
- updates `FiO2_delivered` immediately in ventilator scenarios so the UI response is instant.

### 2. AirwayInterfaceModule

File changed:

- `modules/respiratory/airway_interface.py`

The module now preserves the distinction:

- `FiO2` = commanded set-point;
- `FiO2_delivered` = effective delivered FiO2 after interface efficiency/leak.

It no longer overwrites commanded `FiO2` with delivered FiO2 in spontaneous, HFNC, NIV, or artificial-airway paths.

### 3. UI bedside display

File changed:

- `ui/app.js`

The main FiO2 card is labeled as a set-point, so it now displays:

1. `st.controls.FiO2`, if available;
2. otherwise `st.FiO2`;
3. only then `st.FiO2_delivered` as fallback.

This prevents the visible FiO2 card from snapping to a stale delivered value after a user changes the slider.

## New tests

File added:

- `tests/test_v320_fio2_control_persistence.py`

The tests cover:

- ventilator/ETT FiO2 persistence;
- percent input normalization (`80` -> `0.80`);
- HFNC set-point persistence;
- low-flow oxygen set-point persistence;
- NIV set-point persistence.

## Verification

Targeted v3.2 public-polish tests:

```text
14 passed
0 failed
```

Included:

- `tests/test_v320_public_polish_contracts.py`
- `tests/test_v320_public_polish_deviation_contracts.py`
- `tests/test_v320_fio2_control_persistence.py`

UI/API round-trip subset:

```text
7 passed
0 failed
```

Included:

- `tests/test_v302_ui_backend_bidirectional.py`
- `tests/test_v200_api_server.py::test_api_action_router_set_fio2_and_airway_event`
- `tests/test_v301_ui_live_controls.py`

Manual probes:

- `healthy_child_20kg`: set FiO2 to 0.80 -> remains 0.80 after step.
- `ards_mild`: set FiO2 to 0.80 -> remains 0.80 after step.
- `airway_hfnc_bronchiolitis_v1_23_1`: set FiO2 to 0.80 -> `HFNC_FiO2_set` remains 0.80 and delivered FiO2 rises appropriately.
- `airway_unassisted_spontaneous_breathing_v1_23`: set FiO2 to 0.80 -> `oxygen_FiO2_set` remains 0.80 and delivered FiO2 remains above room air.
- `airway_niv_cpap_bronchiolitis_v1_23_2`: set FiO2 to 0.80 -> `NIV_FiO2_set` remains 0.80 and delivered FiO2 rises appropriately.

## Remaining note

`FiO2_delivered` may correctly be lower than `FiO2` in low-flow oxygen, HFNC, or NIV because the model includes interface efficiency and leak. The UI should therefore treat `FiO2` as the user command and `FiO2_delivered` as the physiologic/effective value.

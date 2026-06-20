# v1.23-alpha — Airway interface model base

This release introduces the first airway-interface abstraction. The goal is to represent a child who is not intubated and not actively supported by a ventilator.

## Added

- `modules/respiratory/airway_interface.py`
- `NONE` / `UNASSISTED` ventilator modes.
- Bus fields for `airway_interface`, `intubated`, `ventilator_connected`, `unassisted_breathing_active`, and pressure-delivery metadata.
- Scenario `airway_unassisted_spontaneous_breathing_v1_23.yaml`.
- Audit tool `tools/airway_interface_audit_v1_23.py`.
- Tests `tests/test_v123_airway_interface.py`.

## Scope

This is the base layer only. HFNC, NIV, tube resistance, intubation attempts, extubation events, aspiration and laryngospasm are intentionally left for later releases.

## Safety

Educational use only. Not a medical device. Not for clinical decision support.


## Numerical note

The chemoreflex spontaneous respiratory-rate response is anchored to the baseline scenario RR to avoid cumulative RR drift in spontaneous/NONE modes.

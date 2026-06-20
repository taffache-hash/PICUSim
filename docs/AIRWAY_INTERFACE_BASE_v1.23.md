# v1.23-alpha — Airway interface model base

This release introduces an explicit airway-interface layer. Its first purpose is to support an educational child who is **not intubated** and has **no active ventilator pressure**.

## Implemented in v1.23

- `airway_interface = UNASSISTED`
- `vent_mode = NONE`
- `intubated = False`
- `ventilator_connected = False`
- `Paw = 0 cmH2O` and `PEEP = 0 cmH2O`
- Respiratory mechanics remain driven by `Pmus` from the chemoreflex pathway.

## Not yet implemented

- HFNC flow effects
- NIV / mask leak
- Endotracheal tube resistance
- Failed intubation
- Accidental or planned extubation
- Aspiration and laryngospasm

These are deliberately deferred to later releases.

## Educational interpretation

`NONE/UNASSISTED` should be read as spontaneous breathing without a ventilator. It is not a high-fidelity airway model and is not suitable for clinical decision support.


## Numerical note

The chemoreflex spontaneous respiratory-rate response is anchored to the baseline scenario RR to avoid cumulative RR drift in spontaneous/NONE modes.

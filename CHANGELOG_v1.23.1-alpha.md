# v1.23.1-alpha — Oxygen delivery / HFNC base

- Added non-invasive oxygen-delivery fields to the physiological bus.
- Extended `AirwayInterfaceModule` with low-flow oxygen, simple mask and HFNC educational behavior.
- Connected gas exchange to `FiO2_delivered` and HFNC dead-space washout.
- Updated `VentilatorModule` so `mode=NONE` preserves HFNC/low-flow interface metadata rather than forcing all cases to `UNASSISTED`.
- Added low-flow oxygen and HFNC bronchiolitis scenarios.
- Added audit tool, documentation and tests.

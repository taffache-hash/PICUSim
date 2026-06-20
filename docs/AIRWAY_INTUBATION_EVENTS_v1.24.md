# v1.24-alpha — Airway intubation/extubation event system

This release adds an educational airway event layer above the v1.23 airway-interface model.

Implemented events:

- `perform_intubation`
- `failed_intubation_attempt`
- `start_bag_mask_ventilation`
- `accidental_extubation`
- `planned_extubation`
- `laryngospasm`
- `aspiration_event`
- `airway_obstruction_event`

The events are bounded state-change proxies. They are designed for simulation teaching and debriefing only. They are not procedural guidance and are not a clinical airway-management algorithm.

New scenarios:

- `airway_rsi_hypoxic_child_v1_24.yaml`
- `airway_accidental_extubation_picu_v1_24.yaml`

New audit:

```bash
python tools/airway_event_audit_v1_24.py --dt 10 --fail-on-review
```

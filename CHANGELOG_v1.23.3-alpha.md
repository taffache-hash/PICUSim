# CHANGELOG v1.23.3-alpha

## Added
- Artificial-airway ETT/tracheostomy educational scaffold.
- Tube resistance, dead-space, cuff leak, obstruction and failure-risk Bus fields.
- Two ETT scenarios and audit tool.

## Changed
- Gas exchange now includes `tube_VdVt_add` as an apparatus dead-space proxy.
- Scenario loader reads artificial-airway fields under `airway_interface`.

## Limitations
- No intubation/extubation event system yet.
- No CFD or clinical tube-size recommendation.

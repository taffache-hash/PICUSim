# PDT v1.20 — Adaptive V/Q Dispersion

This release extends the public three-zone gas-exchange scaffold with pathology-adaptive V/Q dispersion.

The model remains educational and qualitative. It is not externally validated and is not intended for clinical decision support.

## What changed

The gas-exchange module now exposes explicit driver weights:

- `vq_ards_weight`: derecruitment / low-V/Q / shunt driver
- `vq_obstruction_weight`: obstructive dead-space / high-V/Q driver
- `vq_shock_weight`: sepsis-shock perfusion heterogeneity driver
- `vq_neonatal_weight`: neonatal/RDS-like immaturity and derecruitment driver
- `vq_pathology_driver`: dominant qualitative driver (`none`, `ards`, `obstruction`, `shock`, `neonatal`, `mixed`)
- `vq_adaptive_sigma`: final log-normal V/Q dispersion after pathology adaptation
- `vq_adaptive_revision`: schema marker, set to `120`

## Intended directionality

- ARDS-like derecruitment increases shunt and sigma.
- Asthma/bronchiolitis-like obstruction increases dead space and high-V/Q burden.
- Sepsis/shock increases perfusion heterogeneity.
- Neonatal RDS increases shunt and dispersion in the neonatal profile.

## Audit

Run:

```bash
python tools/vq_adaptive_dispersion_audit_v1_20.py --fail-on-review
```

The audit checks healthy, ARDS, asthma, bronchiolitis, neonatal RDS and septic shock scenarios.

# v1.20-alpha — Adaptive V/Q Dispersion

## Added

- Pathology-adaptive V/Q dispersion in `modules/respiratory/gas_exchange.py`.
- New Bus fields: `vq_adaptive_sigma`, `vq_ards_weight`, `vq_obstruction_weight`, `vq_shock_weight`, `vq_neonatal_weight`, `vq_pathology_driver`, `vq_adaptive_revision`.
- New audit tool: `tools/vq_adaptive_dispersion_audit_v1_20.py`.
- New documentation: `docs/VQ_ADAPTIVE_DISPERSION_v1.20.md`.
- New tests: `tests/test_v120_vq_adaptive_dispersion.py`.

## Notes

This is a qualitative educational refinement. It is not external clinical validation.

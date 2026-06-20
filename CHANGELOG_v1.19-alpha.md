# CHANGELOG v1.19-alpha — Score assumption registry hardening

## Added

- `data/score_assumption_registry_v1.19.yaml` with hardened score/proxy/modifier metadata.
- `data/score_assumption_audit_scenarios_v1.19.yaml` default audit subset.
- `tools/score_assumption_audit_v1_19.py` for registry completeness and range-audit reporting.
- `docs/SCORE_ASSUMPTION_HARDENING_v1.19.md`.
- `tests/test_v119_score_assumption_hardening.py`.

## Changed

- Updated public alpha check to require the v1.19 score registry, audit tool, documentation and tests.
- Updated score registry audit default to v1.19.
- Updated version metadata to 1.19-alpha.

## Limitations

- This is not external validation.
- Numeric ranges are software sanity ranges for internal qualitative variables, not clinical targets.

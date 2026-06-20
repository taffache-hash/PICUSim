# PDT v3.1 Step 4.13 — HF-1/HF-2/HF-3 Hotfix Report

Release: `3.1-step4.13-emogas-panel-hf1-hf2-hf3-trend10min-visible`

## Scope

This hotfix intentionally avoids physiology-engine changes and new feature work. It targets pre-release blockers identified in the Step 4.13 review.

## Fixes

### HF-1 — Unicode/BOM cleanup

- Removed UTF-8 BOM from text/code files.
- Repaired mojibake Unicode labels in UI and code comments, including CO₂/EtCO₂/PaCO₂ and ×10⁹/L labels.
- Re-saved text sources as UTF-8 without BOM.

### HF-2 — score_assumption_audit v1.19 robustness

- Changed `core/bus.py` parsing in `tools/score_assumption_audit_v1_19.py` to use `utf-8-sig`.
- Added missing Step 4 audit variables to `data/score_assumption_registry_v1.19.yaml`, because after BOM removal the v119 audit exposed 31 newly introduced Bus variables that were not registered.

### HF-3 — VERSION consistency

- Updated `VERSION` to `3.1-step4.13-emogas-panel-hf1-hf2-hf3-trend10min-visible`.
- `api/server.py` already reads the version from `VERSION`, so no hardcoded API version change was needed.

## Validation performed

Syntax checks:

- `python -m py_compile core/bus.py api/state_profiles.py api/action_router.py modules/ventilator/ventilator.py tools/score_assumption_audit_v1_19.py api/server.py`
- `node --check ui/app.js`
- `node --check ui/canvas_waveforms.js`

Targeted pytest checks:

- `tests/test_v316_etco2_model_coupling_contract.py`
- `tests/test_v320_popup_charts_requested_contract.py`
- `tests/test_v119_score_assumption_hardening.py`
- `tests/test_v332_emogas_panel_contract.py`

Result: `14 passed`.

A broader pytest run was attempted but exceeded the execution time limit in this environment, so this release should still be re-tested locally/Docker with the full suite before considering it final.

## Not included

- Benchmark matrix v118 was not corrected in this hotfix.
- Step 4.14+ UI/clinical additions were not implemented yet.
- No Dockerfile or physiology model changes were made.

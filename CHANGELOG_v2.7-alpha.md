# v2.7-alpha — Scenario authoring assistant

Added a template-based scenario authoring assistant for the local API and web console.

## Added

- `data/scenario_authoring_templates_v2.7.yaml`
- `api/scenario_authoring.py`
- `tools/scenario_authoring_audit_v2_7.py`
- `docs/SCENARIO_AUTHORING_ASSISTANT_v2.7.md`
- `tests/test_v270_scenario_authoring_assistant.py`
- Author panel in `ui/index.html`
- Authoring client logic in `ui/app.js`

## API

- `GET /authoring/templates`
- `POST /authoring/draft`
- `POST /authoring/validate`
- `POST /authoring/save`
- `GET /authoring/created`

## Notes

The authoring assistant creates educational YAML scenario drafts from curated templates. It validates drafts with the existing scenario loader before saving. It does not generate clinical protocols and is not for clinical use.

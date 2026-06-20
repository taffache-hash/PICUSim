# Release audit — v3.0-alpha

## Scope

General source, packaging and documentation review before Docker-oriented distribution.

## Checks performed in this environment

- Source tree inspection.
- Version consistency check across main distribution files.
- Python syntax compilation with `python -m compileall -q .`.
- Targeted public/API/UI/authoring regression tests.
- FastAPI health and monitor endpoint smoke check through `TestClient`.
- Removal of generated Python bytecode and pytest cache artifacts from the final bundle.

## Test results

```text
python -m pytest -q tests/test_public_smoke.py tests/test_v200_api_server.py tests/test_v260_ui_polish_tablet.py tests/test_v270_scenario_authoring_assistant.py
11 passed
```

Endpoint smoke check:

```text
GET /health  -> 200, status ok, api_version 3.0-alpha
GET /monitor -> 200, text/html
```

## Issues corrected

- Inconsistent v2.7/v2.8 distribution metadata in README and Docker documentation.
- Legacy v1.0 wording in `LICENSE_PENDING.md`.
- Hard-coded API version strings in `api/server.py`.
- Hard-coded console launcher display version.
- Generated local cache artifacts included in the source bundle.
- Missing v3.0 release notes, installation guide and distribution checklist.

## Not fully verifiable here

Docker Engine is not available in this execution environment, so an actual `docker compose up --build` run was not performed here. The Dockerfile and Compose file were reviewed and the same application entry point was tested through Python/FastAPI.

## Residual risks

- This is still alpha research/education software.
- No clinical validation has been performed.
- Some legacy feature names and historical files retain their original version numbers by design.
- A final redistribution/open-source license is still pending.

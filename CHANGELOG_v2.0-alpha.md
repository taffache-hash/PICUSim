# CHANGELOG v2.0-alpha

## Added

- Clean local FastAPI backend for PDT training UI integration.
- In-memory session manager with scenario loading, stepping, start/pause, compact history, and actions.
- Compact state profiles: `bedside`, `waveform`, `debug`, `full`.
- WebSocket streams for bedside and waveform scalar states.
- Action router for selected ventilator, oxygen, drug, airway-event, and Bus-variable actions.
- `start_pdt_api.py` one-command API launcher.
- API documentation in `docs/API_SERVER_v2.0.md`.
- API tests in `tests/test_v200_api_server.py`.

## Changed

- Project version bumped to `2.0-alpha`.
- Added FastAPI and Uvicorn to runtime requirements.
- pyproject package discovery now includes `api*`.

## Notes

This release does not add the new browser frontend yet. It prepares the backend contract for the future lightweight Web Training Console.

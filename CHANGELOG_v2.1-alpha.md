# v2.1-alpha — Web Monitor MVP

This release adds a lightweight local web monitor for the PDT Clinical Training Console.

## Added

- `ui/index.html` — browser monitor shell.
- `ui/styles.css` — responsive dark bedside monitor layout.
- `ui/canvas_waveforms.js` — Canvas ECG, pleth, ABP, and respiratory waveform renderer.
- `ui/app.js` — scenario loading, session control, WebSocket subscription, airway actions, drug actions, and timeline logging.
- `/` and `/monitor` routes to serve the UI.
- `/session/{id}/reset` and `/session/{id}/events` API endpoints.
- `docs/WEB_MONITOR_v2.1.md`.
- `tests/test_v210_web_monitor.py`.

## Design

The UI deliberately avoids PyQt, Streamlit, desktop subprocess orchestration, and full-Bus streaming. The browser draws waveforms locally using compact scalar anchors from the API.

## Safety

Educational use only. Not for clinical use. Not a medical device. Not a validated patient-specific digital twin.

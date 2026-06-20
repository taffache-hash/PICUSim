# v2.0-alpha — PDT Clinical Training API

This release introduces a clean local API layer for the Pediatric Critical Care Physiology Simulation Framework.

The design goal is to replace heavy desktop GUI coupling with a small backend that can be used by any frontend: browser UI, instructor console, notebooks, tests, or a future desktop wrapper.

## Start

```bash
python start_pdt_api.py --host 127.0.0.1 --port 8000
```

or:

```bash
uvicorn api.server:app --host 127.0.0.1 --port 8000
```

Interactive API docs are available at:

```text
http://127.0.0.1:8000/docs
```

## Core endpoints

```text
GET  /health
GET  /scenarios
GET  /sessions
POST /session/load
POST /session/{id}/start
POST /session/{id}/pause
POST /session/{id}/step
GET  /session/{id}/state?profile=bedside|waveform|debug|full
POST /session/{id}/action
GET  /session/{id}/history
DEL  /session/{id}
WS   /ws/session/{id}/bedside
WS   /ws/session/{id}/waveform
```

## State profiles

The API intentionally does not stream the full physiological Bus at high frequency.

Profiles:

- `bedside`: compact monitor-like state for numeric bedside display.
- `waveform`: scalar anchors for browser-side ECG/pleth/ABP/airway waveform synthesis.
- `debug`: selected physiology/debug variables.
- `full`: full Bus dictionary, intended for development only.

## Actions

Supported action classes:

- set ventilator/oxygen fields: FiO2, PEEP, RR, Paw.
- set selected drugs: noradrenaline, adrenaline, dopamine, fentanyl, morphine, midazolam, propofol, rocuronium, insulin, vancomycin, piperacillin.
- apply known airway events from the v1.24 event library.
- set a known Bus variable for controlled development use.

Example:

```bash
curl -X POST http://127.0.0.1:8000/session/load \
  -H 'Content-Type: application/json' \
  -d '{"scenario":"airway_rsi_hypoxic_child_v1_24", "dt":0.2}'
```

```bash
curl -X POST http://127.0.0.1:8000/session/<id>/action \
  -H 'Content-Type: application/json' \
  -d '{"action":"set_fio2", "payload":{"value":1.0}}'
```

## Design notes

The API holds sessions in memory. This is deliberate for the educational local-server MVP. It avoids database overhead and keeps the UI integration simple.

The frontend should render waveforms in the browser using Canvas/requestAnimationFrame. The backend streams low-bandwidth scalar anchors, not large waveform arrays.

## Limitations

- Not for clinical use.
- In-memory sessions are not persistent.
- No authentication; intended for local use.
- The websocket stream is compact and lossy by design.
- This release is backend-only; the new browser UI starts in v2.1.

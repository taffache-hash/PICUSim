# Web Monitor MVP — v2.1-alpha

The v2.1 web monitor is a lightweight browser-based interface served by the local FastAPI backend.

## Start

```bash
python start_pdt_api.py --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000/monitor
```

## Architecture

```text
PDT core simulation
→ FastAPI session backend
→ compact bedside/waveform profiles
→ browser JavaScript UI
→ Canvas waveform rendering
```

The monitor does not stream the full physiological Bus at high frequency. It subscribes to:

```text
/ws/session/{id}/bedside   5 Hz
/ws/session/{id}/waveform 20 Hz
```

## UI panels

- Scenario selector.
- Start / pause / step / reset.
- Bedside vitals.
- ECG, pleth, ABP, and respiratory waveform canvases.
- Airway / ventilation controls.
- Drug controls.
- Local event timeline.

## API additions

```text
GET  /
GET  /monitor
GET  /ui/*
POST /session/{id}/reset
GET  /session/{id}/events
```

## Limitations

This is an MVP. It is intentionally simple and local-first. It does not yet include full instructor mode, integrated debrief reports, authentication, multiplayer sessions, or packaged desktop deployment.

## Safety

Educational use only. Not for clinical use. Not a medical device. Not a validated patient-specific digital twin.

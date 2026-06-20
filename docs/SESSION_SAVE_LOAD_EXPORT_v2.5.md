# PDT v2.5-alpha — Session save/load and report export

Educational/research alpha only. Not for clinical use. Not a medical device.

v2.5 adds a portable JSON session-save format and Markdown report export for the local web training console.

## What is saved

The JSON bundle includes:

- session metadata: scenario, dt, current time, duration, history settings;
- final bedside state;
- compact bedside history and training history;
- event log and action replay log;
- instructor notes and learner-diagnosis visibility;
- emergency debrief metrics and decision flags;
- instructor report summary;
- safety disclaimer.

The save file deliberately does **not** use Python pickle. Restored sessions are rebuilt from the original scenario YAML and the saved action log.

## API endpoints

```text
GET  /session/{session_id}/export?format=json|md
POST /session/{session_id}/save
POST /session/load_saved
```

`/save` writes files under:

```text
outputs/session_exports_v2.5/
```

`/load_saved` accepts either a relative JSON file path or a full JSON bundle.

## GUI

The web console now includes:

- Save session;
- Export JSON;
- Export MD;
- Load saved JSON path.

## Limitations

Replay is deterministic for scenario perturbations and API/instructor actions recorded in the action log. It is not intended as legal-grade audit logging or clinical patient-record storage.

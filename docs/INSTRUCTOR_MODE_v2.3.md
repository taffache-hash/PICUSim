# v2.3-alpha — Instructor mode

This release adds an instructor layer to the lightweight web monitor. It is intended for local educational simulation only and is not for clinical use.

## Features

- Instructor action presets for airway, oxygenation, ventilation, and vasoactive support.
- Instructor notes and bookmarks attached to the current simulation time.
- Learner-diagnosis visibility toggle for scenario concealment during training.
- Instructor report endpoint combining event log, notes, final bedside state, and emergency debrief metrics.
- UI panel integrated into `/monitor`.

## API

```text
GET  /instructor/presets
GET  /session/{session_id}/instructor
POST /session/{session_id}/instructor/note
POST /session/{session_id}/instructor/visibility
GET  /session/{session_id}/instructor/report?format=json|md
```

## Safety boundary

Instructor mode exposes only predefined action presets and existing API actions. It does not expose arbitrary code execution. Advanced `set_variable` remains available through the API action router for development use, not for learners.

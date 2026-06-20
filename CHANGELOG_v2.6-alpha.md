# v2.6-alpha — UI polish and tablet-friendly apparatus layout

## Added

- Clean bedside-monitor-first layout.
- Right-side control dock with high-level apparatus buttons.
- Modal apparatus window system for Session, Airway, Drugs, Training, Instructor, Debrief and Timeline.
- Learner/instructor view toggle.
- Compact mini-timeline in the control dock.
- Tablet-friendly and small-screen responsive breakpoints.
- Larger touch targets for emergency training use.
- Documentation: `docs/WEB_UI_POLISH_v2.6.md`.
- Tests: `tests/test_v260_ui_polish_tablet.py`.

## Changed

- Removed the crowded all-panels-on-screen layout from the main monitor view.
- Kept the monitor and vital signs visually dominant.
- Moved secondary actions into pop-up apparatus panels.
- Preserved the existing API, session save/load, debrief and instructor functions.

## Not changed

- No physiological-model changes.
- No scenario changes.
- No PK/PD changes.

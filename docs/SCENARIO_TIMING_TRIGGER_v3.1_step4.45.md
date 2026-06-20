# Scenario Timing and Critical-Event Trigger — v3.1 Step 4.45

Purpose: make scenario time explicit and pedagogically usable.

## Contract

Every scenario can now expose:

- nominal real-time duration at 1x speed;
- virtual simulation duration;
- critical-event trigger time;
- stable-start mode, where the child begins from a healthy/stable baseline;
- shifted critical timeline, so deterioration starts only after trigger.

## UI behavior

The Streamlit interface now displays the nominal real-time duration before running the scenario and provides:

- `Start from stable child` checkbox;
- `Critical event trigger [real seconds at 1x]` slider;
- `Run / trigger critical event` button.

Acceleration changes wall-clock execution speed, not the educational clinical timeline displayed to the learner.

## Safety note

This does not make the timing clinically predictive. It makes timing visible, reproducible and easier to teach.

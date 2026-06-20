# Step 4.3 — Control pending/confirmed feedback

Scope: UI-only.

## Implemented

- Pending status appears immediately when a live control is changed.
- Confirmed status appears when the backend value returns through the controls profile and matches the requested value.
- Error status appears when an action call fails.
- Applies to ventilator controls and drug numeric inputs.

## Rationale

The user should know that the command was sent and later confirmed by the backend, instead of waiting passively for the monitor to change.

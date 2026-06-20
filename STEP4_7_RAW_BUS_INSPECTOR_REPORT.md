# Step 4.7 - Raw Bus Inspector

Added a snapshot-only raw Bus inspector inside the extended monitor panel.

## Behavior

- Uses the existing `/session/{id}/state?profile=full` snapshot.
- No new route, WebSocket, or polling loop.
- The inspector is hidden until `Raw Bus` is pressed.
- A local text filter searches variable names and rendered values.
- The table refreshes only when a new full snapshot is requested or the filter changes.

## Files

- `ui/index.html`
- `ui/app.js`
- `ui/styles.css`
- `tests/test_v325_raw_bus_inspector_contract.py`

## Verification

Targeted contract:

```bash
pytest tests/test_v325_raw_bus_inspector_contract.py
```

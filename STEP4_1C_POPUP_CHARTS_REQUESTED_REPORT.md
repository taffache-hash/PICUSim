# Step 4.1C — Requested popup charts

Scope: UI-only. No backend route, no new WebSocket, no physiology changes.

## Implemented

- Added a popup chart modal opened from Monitor esteso.
- Added chart selector and redraw button.
- Bedside variables use the existing 4 Hz lightweight trend buffer.
- Extended variables use the manual snapshot buffer populated by pressing Aggiorna snapshot.

## First chart set

- MAP
- SpO2
- PaCO2 / EtCO2
- HR
- Paw
- Lactate
- Urine output
- Fluid balance
- DO2 / VO2
- Glucose

## Rationale

The user can inspect trajectories on demand without converting the interface into a heavy continuous multi-parameter dashboard.

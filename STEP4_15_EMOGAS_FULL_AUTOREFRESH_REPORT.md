# Step 4.15 - Emogas full profile autorefresh

## Problem
The Emogas panel was rendered from the 4 Hz bedside-fast WebSocket when the tab was open. That stream contains PaCO2, EtCO2 and SaO2, but not the complete blood gas/lab set. Result: pH, PaO2, HCO3, BE, lactate, Hb, Na, K and glucose could remain `--` unless the user manually refreshed the full state.

## Fix
- Added full-profile polling while Emogas is open.
- Reuses `/session/{session_id}/state?profile=full`.
- Refresh interval: 2.5 seconds only while Emogas or Monitor esteso is open.
- Bedside WebSocket still updates the panel, but labels it as waiting/full-profile + bedside update depending on cached full data.
- No engine changes.

## Expected UI result
Opening Emogas should populate all 12 values within a few seconds:

- pH
- PaO2
- PaCO2
- EtCO2
- SaO2
- HCO3
- BE
- lactate
- Hb
- Na
- K
- glucose

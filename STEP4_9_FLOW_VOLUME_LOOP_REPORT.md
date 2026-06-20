# Step 4.9 - Flow-Volume Loop

Added an on-request flow-volume loop.

- Extends `waveform_fast` with `Vt`, `Flow_current_mL_s`, and derived `flow_L_s`.
- Builds a short client-side waveform buffer from the existing waveform WebSocket.
- Integrates signed flow into an approximate loop volume for display.
- Shows a data-needed message if waveform samples are insufficient.

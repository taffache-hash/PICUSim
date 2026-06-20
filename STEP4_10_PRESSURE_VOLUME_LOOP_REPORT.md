# Step 4.10 - Pressure-Volume Loop

Added an on-request pressure-volume loop.

- Reuses the same waveform buffer as Step 4.9.
- Plots `Paw` against the derived loop volume.
- No new backend endpoint or polling loop.
- The loop is intended as a bedside teaching display, not a calibrated pulmonary mechanics measurement.

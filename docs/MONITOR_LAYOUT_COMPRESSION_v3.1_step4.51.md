# Step 4.51 — Monitor layout compression

Purpose: make the bedside screen more useful during scenario execution by prioritising large numeric values over decorative waveforms.

Changes:

- Vital signs are now rendered as a vertical side column next to the waveform stack.
- HR, SpO₂, MAP/ABP, PaCO₂/EtCO₂, Paw and FiO₂ remain always visible with larger numeric typography.
- Waveforms are compressed and kept as supportive visual context rather than the dominant monitor element.
- Mini trend canvases are preserved beside each numeric tile, but reduced to a compact strip.
- Existing DOM ids are preserved for UI compatibility and regression tests.

Design rationale:

- During scenario use, the educational value comes mainly from numerical deterioration, response latency and rescue trajectory.
- Curves remain helpful for ambience and pattern recognition, but should not consume the majority of vertical space.
- The new layout improves readability when many panels are open and when the control dock is visible.

Validation:

- Static UI contract confirms the compact split layout exists.
- Existing vital ids and trend canvas ids are preserved.
- Existing UI id-target audit remains valid.

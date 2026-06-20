# Step 4.8 - Capnography Popup

Added a requested capnography plot in the existing popup chart surface.

- Uses the live waveform buffer.
- Couples the capnogram height to model `EtCO2` / `EtCO2_proxy`.
- Does not add polling, WebSocket routes, or backend streaming.
- The shape is educational/semi-synthetic; the value is anchored to the respiratory gas-exchange model.

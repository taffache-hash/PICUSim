
# Console performance hardening — v2.4-alpha

v2.4 stabilizes the web-console architecture before adding more clinical UI features.

## Additions

- One-command launcher: `python start_pdt_console.py`.
- Fast API profiles: `bedside_fast`, `waveform_fast`, and `training`.
- WebSocket rate limits: bedside defaults to 4 Hz, waveform defaults to 24 Hz.
- Bounded history: `max_history_points`, `history_window_s`, and `history_decimation_s`.
- Performance audit: `python tools/gui_performance_audit_v2_4.py`.

## Intent

The GUI should stream compact monitor data and request debug/full state only on demand.
This release does not change the physiology engine.

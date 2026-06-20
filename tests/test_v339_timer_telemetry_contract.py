from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v339_timer_telemetry_uses_backend_time_and_commanded_speed():
    js = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")

    assert "function readSessionSpeed()" in js
    assert "function syncSessionTiming(st={}, envelope={})" in js
    assert "SESSION_UI_STATE.simTimeS = t" in js
    assert "SESSION_UI_STATE.speed = speed" in js

    # Bedside websocket/API updates must advance the telemetry pill's sim timer.
    assert "function updateBedside(st, envelope={})" in js
    assert "syncSessionTiming(st, envelope);" in js

    # The displayed speed should be the commanded run speed, not sim/wall since
    # sim time is absolute and makes the pill show x0.0 or huge transient values.
    assert "sim / wallS" not in js
    assert "const speed = SESSION_UI_STATE.running ? Number(SESSION_UI_STATE.speed || readSessionSpeed()) : 0;" in js

    # Start and manual step responses should sync timing immediately.
    assert "syncSessionTiming(data.state || {}, data);" in js
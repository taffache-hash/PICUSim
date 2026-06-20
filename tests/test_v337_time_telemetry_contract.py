from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v337_time_telemetry_contract_present():
    html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "ui" / "styles.css").read_text(encoding="utf-8")

    assert 'id="timeTelemetry"' in html
    assert 'sim --' in html and 'wall --' in html and 'speed' in html
    assert 'simTimeS' in js and 'wallStartMs' in js and 'wallAccumMs' in js
    assert 'function formatDuration' in js
    assert 'function currentWallElapsedMs' in js
    assert 'function updateTimeTelemetry' in js
    assert 'function startWallClock' in js
    assert 'function pauseWallClock' in js
    assert 'function resetWallClock' in js
    assert "function readSessionSpeed()" in js
    assert "SESSION_UI_STATE.speed = readSessionSpeed()" in js
    assert 'startWallClock();' in js
    assert 'pauseWallClock();' in js
    assert 'resetWallClock();' in js
    assert 'updateTimeTelemetry(now);' in js
    assert '.time-telemetry' in css
    assert '.time-telemetry.running' in css

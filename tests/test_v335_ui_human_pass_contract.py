from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v335_session_state_pill_and_audio_start_cue_present():
    html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "ui" / "styles.css").read_text(encoding="utf-8")

    assert '`n' not in html
    assert 'id="sessionRunState"' in html
    assert 'class="session-state-pill idle"' in html
    assert 'function setSessionRunState' in js
    assert "setSessionRunState('pending')" in js
    assert "setSessionRunState('error')" in js
    assert "if (AUDIO_MONITOR.enabled) playUiCue('confirm')" in js
    assert "SESSION_UI_STATE.running = true" in js
    assert "SESSION_UI_STATE.running = false" in js
    assert '.session-state-pill' in css
    assert '.session-state-pill.running' in css
    assert '.session-state-pill.paused' in css

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v334_session_buttons_have_stateful_feedback_and_audio_cues():
    html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "ui" / "styles.css").read_text(encoding="utf-8")

    for button_id in ["loadBtn", "startBtn", "pauseBtn", "stepBtn", "resetBtn", "audioMonitorBtn"]:
        assert f'id="{button_id}"' in html

    assert "const SESSION_UI_STATE" in js
    assert "uiCues: true" in js
    assert "function playUiCue" in js
    assert "function setButtonVisualState" in js
    assert "function updateSessionButtonStates" in js
    assert "function runSessionButtonAction" in js
    assert "runSessionButtonAction('startBtn', startSession)" in js
    assert "runSessionButtonAction('pauseBtn', pauseSession)" in js
    assert "SESSION_UI_STATE.running = true" in js
    assert "SESSION_UI_STATE.running = false" in js
    assert "markButtonMomentary('stepBtn'" in js
    assert "markButtonMomentary('resetBtn'" in js
    assert "playUiCue('pending')" in js
    assert "playUiCue('confirm')" in js
    assert "playUiCue('error')" in js

    for selector in ["button.button-active", "button.button-pending", "button.button-confirmed", "button.button-error"]:
        assert selector in css
    assert "SAT+ECG+UI" in css

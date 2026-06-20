from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v343_monitor_action_feedback_bar_present():
    html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "ui" / "styles.css").read_text(encoding="utf-8")

    assert 'id="actionFeedbackBar"' in html
    assert 'aria-live="polite"' in html

    assert "function showActionFeedback" in js
    assert "showActionFeedback(label, detail, 'confirmed')" in js
    assert "showActionFeedback(btn?.textContent?.trim() || 'Session action', 'in corso', 'pending')" in js
    assert "showActionFeedback(btn?.textContent?.trim() || 'Session action', e.message, 'error')" in js

    assert ".action-feedback-bar" in css
    assert ".action-feedback-bar.pending" in css
    assert ".action-feedback-bar.confirmed" in css
    assert ".action-feedback-bar.error" in css

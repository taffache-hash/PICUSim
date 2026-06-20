from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_visual_alarm_contract_present():
    app = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "ui" / "styles.css").read_text(encoding="utf-8")
    assert "VITAL_ALARM_RULES" in app
    assert "function updateVisualAlarms" in app
    assert "updateVisualAlarms(st);" in app
    assert "alarm-warning" in css
    assert "alarm-critical" in css

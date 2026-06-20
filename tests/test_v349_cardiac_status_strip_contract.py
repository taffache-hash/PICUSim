from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v349_bedside_monitor_has_cardiac_status_strip():
    html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "ui" / "styles.css").read_text(encoding="utf-8")

    for element_id in [
        "cardiacStatusStrip",
        "cardiacRhythm",
        "cardiacPulse",
        "cardiacRhythmClass",
        "cardiacCprState",
    ]:
        assert f'id="{element_id}"' in html

    assert "function updateCardiacStatusStrip" in js
    assert "st.cardiac_rhythm" in js
    assert "st.has_pulse" in js
    assert "st.cardiac_arrest_active" in js
    assert "st.shockable_rhythm" in js
    assert "updateCardiacStatusStrip(st);" in js

    assert ".cardiac-status-strip" in css
    assert ".cardiac-status-strip.arrest" in css
    assert ".cardiac-status-strip.unstable" in css

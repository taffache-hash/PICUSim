from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v342_monitor_header_has_quick_access_buttons():
    html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "ui" / "styles.css").read_text(encoding="utf-8")

    assert 'id="quickEmogasBtn"' in html
    assert 'id="quickBolusBtn"' in html
    assert 'id="quickExtendedMonitorBtn"' in html

    assert "$('quickEmogasBtn').onclick = () => openApparatus('emogasPanel')" in js
    assert "$('quickBolusBtn').onclick = () => openApparatus('drugPanel', 'bolusPanel')" in js
    assert "$('quickExtendedMonitorBtn').onclick = () => openApparatus('extendedMonitorPanel')" in js

    assert ".monitor-header-actions" in css
    assert "flex-wrap: wrap" in css

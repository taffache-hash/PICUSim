from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v325_raw_bus_inspector_is_snapshot_only_and_filterable():
    html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "ui" / "styles.css").read_text(encoding="utf-8")

    assert 'id="rawBusToggleBtn"' in html
    assert 'id="rawBusInspector"' in html
    assert 'id="rawBusFilter"' in html
    assert 'id="rawBusTable"' in html
    assert "function renderRawBusInspector" in js
    assert "function toggleRawBusInspector" in js
    assert "rawBusFilter" in js
    assert "renderRawBusInspector(lastExtendedMonitorState)" in js
    assert "setInterval(() => renderRawBusInspector" not in js
    assert ".raw-bus-inspector" in css
    assert ".raw-bus-row" in css

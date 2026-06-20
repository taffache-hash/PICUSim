from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v336_always_visible_labs_strip_contract_present():
    html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "ui" / "styles.css").read_text(encoding="utf-8")

    assert 'id="labsStrip"' in html
    assert 'id="labsStripItems"' in html
    assert 'class="labs-strip"' in html
    assert 'const LABS_STRIP_ITEMS' in js
    for label in ['Lactate', 'Glucose', 'K+', 'Na+', 'Hb', 'Creatinine', 'Bilirubin', 'GCS', 'RASS', 'ICP', 'CVP', 'DO2', 'Urine']:
        assert label in js
    assert 'function renderLabsStrip' in js
    assert 'function rotateLabsStrip' in js
    assert 'function requestLabsStripSnapshotSoon' in js
    assert 'now - labsStripLastFullRequestMs) < 8000' in js
    assert 'nowMs - labsStripLastRotateMs >= 8000' in js
    assert 'renderLabsStrip(Object.assign({}, st, lastExtendedMonitorState)' in js
    assert 'requestLabsStripSnapshotSoon();' in js
    assert 'rotateLabsStrip(now);' in js
    assert '.labs-strip' in css
    assert '.labs-strip-items' in css
    assert '.labs-strip-item' in css

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v340_drug_panel_has_section_navigation():
    html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "ui" / "styles.css").read_text(encoding="utf-8")

    assert 'class="drug-mode-toolbar"' in html
    assert 'id="drugInfusionsPanel"' in html
    assert 'id="bolusPanel"' in html
    assert 'id="drugAuditPanel"' in html
    assert 'data-panel-scroll="drugInfusionsPanel"' in html
    assert 'data-panel-scroll="bolusPanel"' in html
    assert 'data-panel-scroll="drugAuditPanel"' in html

    assert "document.querySelectorAll('[data-panel-scroll]')" in js
    assert "target.scrollIntoView" in js
    assert "panel-focus-pulse" in js

    assert ".drug-mode-toolbar" in css
    assert ".drug-section-block" in css
    assert ".drug-audit-panel" in css and "scroll-margin-top" in css

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v332_emogas_panel_contract_present():
    html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "ui" / "styles.css").read_text(encoding="utf-8")

    assert 'data-open-panel="emogasPanel"' in html
    assert 'data-panel-tab="emogasPanel"' in html
    assert 'id="emogasPanel"' in html
    assert 'id="emogasRefreshBtn"' in html
    assert 'id="emogasGrid"' in html
    assert 'const EMOGAS_ITEMS' in js
    assert 'function renderEmogasPanel' in js
    assert 'function isEmogasOpen' in js
    assert "panelId === 'emogasPanel'" in js
    assert "$('emogasRefreshBtn').onclick" in js
    assert 'pH_a' in js and 'PaO2' in js and 'PaCO2' in js
    assert 'HCO3_mmol_L' in js and 'lactate' in js
    assert '.emogas-grid' in css
    assert '.emogas-param' in css

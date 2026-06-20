from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v330_bolus_drug_ui_contract_present():
    html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "ui" / "styles.css").read_text(encoding="utf-8")
    assert 'id="bolusDoseGrid"' in html
    assert 'data-scroll-target="bolusPanel"' in html
    assert 'id="bolusPanel"' in html
    assert 'Boli / rescue doses' in html
    assert 'const BOLUS_DRUG_DEFS' in js
    assert 'const activeBolusRecords' in js
    assert 'function administerBolus' in js
    assert 'function bolusWallDelayMs' in js
    assert 'SESSION_UI_STATE.speed' in js
    assert 'function updateBolusCardStates' in js
    assert 'renderBolusControls()' in js
    assert 'setTimeout(async () =>' in js
    assert 'bolus_furosemide' in js and 'nativeBolus: true' in js
    assert '.bolus-dose-grid' in css
    assert '.bolus-active-card' in css
    assert '.panel-focus-pulse' in css

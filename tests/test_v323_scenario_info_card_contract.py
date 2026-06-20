from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_scenario_info_card_contract_present():
    html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "ui" / "styles.css").read_text(encoding="utf-8")
    assert 'id="scenarioInfoBtn"' in html
    assert 'id="scenarioInfoCard"' in html
    assert "scenarioCatalogMap" in app
    assert "function updateScenarioInfoCard" in app
    assert "function toggleScenarioInfoCard" in app
    assert "scenario-info-card" in css

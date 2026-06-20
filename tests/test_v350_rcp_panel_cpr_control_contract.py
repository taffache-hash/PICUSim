from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.server import app


def test_v350_cpr_control_improves_map_and_etco2_during_arrest():
    client = TestClient(app)
    loaded = client.post("/session/load", json={"scenario": "healthy_child_20kg", "dt": 0.2})
    assert loaded.status_code == 200, loaded.text
    sid = loaded.json()["session_id"]

    vf = client.post(
        f"/session/{sid}/action",
        json={"action": "cardiac_rhythm_event", "payload": {"name": "induce_vf"}},
    )
    assert vf.status_code == 200, vf.text
    arrest_state = vf.json()["session"]["state"]
    assert arrest_state["cardiac_arrest_active"] is True
    assert arrest_state["MAP"] <= 10
    assert arrest_state["EtCO2"] <= 10

    cpr = client.post(
        f"/session/{sid}/action",
        json={
            "action": "cpr_control",
            "payload": {"active": True, "quality": 0.8, "compression_fraction": 0.9},
        },
    )
    assert cpr.status_code == 200, cpr.text
    st = cpr.json()["session"]["state"]
    assert st["CPR_active"] is True
    assert st["CPR_quality"] == 0.8
    assert st["compression_fraction"] == 0.9
    assert st["MAP"] > arrest_state["MAP"]
    assert st["EtCO2"] > arrest_state["EtCO2"]

    stopped = client.post(
        f"/session/{sid}/action",
        json={"action": "cpr_control", "payload": {"active": False}},
    )
    assert stopped.status_code == 200, stopped.text
    st = stopped.json()["session"]["state"]
    assert st["CPR_active"] is False
    assert st["compression_fraction"] == 0.0
    assert st["MAP"] <= 10


def test_v350_ui_has_minimal_rcp_operational_panel():
    html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "ui" / "styles.css").read_text(encoding="utf-8")

    assert 'data-open-panel="rcpPanel"' in html
    assert 'data-panel-tab="rcpPanel"' in html
    assert 'id="rcpPanel"' in html
    assert 'id="startCprBtn"' in html
    assert 'id="stopCprBtn"' in html
    assert 'id="cprQualityRange"' in html
    assert '/ui/app.js?v=3.1-step4.38' in html

    assert "function renderRcpPanel" in js
    assert "async function setCprActive" in js
    assert "const cprQuality = st.CPR_quality ?? st.cpr_quality ?? $('cprQualityRange')?.value;" in js
    assert "currentScenario = select.value;" in js
    assert "const scenarioRef = scenarioMeta?.file || scenarioMeta?.path || scenario;" in js
    assert "sendAction('cpr_control'" in js
    assert "$('startCprBtn').onclick = () => setCprActive(true).catch(reportUiError)" in js
    assert "$('stopCprBtn').onclick = () => setCprActive(false).catch(reportUiError)" in js
    assert "renderRcpPanel(st);" in js

    assert ".rcp-status-grid" in css
    assert ".rcp-badge.arrest" in css
    assert ".rcp-badge.cpr-active" in css

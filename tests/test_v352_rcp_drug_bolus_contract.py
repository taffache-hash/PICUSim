from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.server import app


def _load(client):
    loaded = client.post("/session/load", json={"scenario": "healthy_child_20kg", "dt": 0.2})
    assert loaded.status_code == 200, loaded.text
    return loaded.json()["session_id"]


def _action(client, sid, action, payload):
    r = client.post(f"/session/{sid}/action", json={"action": action, "payload": payload})
    assert r.status_code == 200, r.text
    return r.json()


def test_v352_epinephrine_bolus_is_tracked_in_cardiac_arrest():
    client = TestClient(app)
    sid = _load(client)
    _action(client, sid, "cardiac_rhythm_event", {"name": "induce_pea"})

    data = _action(client, sid, "rcp_drug_bolus", {"drug": "epinephrine"})
    assert data["result"]["appropriate"] is True
    assert data["result"]["result"] == "arrest_vasopressor"
    st = data["session"]["state"]
    assert st["epinephrine_bolus_count"] == 1
    assert st["last_rcp_drug"] == "epinephrine"
    assert st["last_rcp_drug_appropriate"] is True
    assert st["MAP"] >= 18


def test_v352_amiodarone_is_contextual_for_shockable_rhythm():
    client = TestClient(app)
    sid = _load(client)
    _action(client, sid, "cardiac_rhythm_event", {"name": "induce_vf"})

    data = _action(client, sid, "rcp_drug_bolus", {"drug": "amiodarone"})
    assert data["result"]["appropriate"] is True
    assert data["result"]["result"] == "shockable_antiarrhythmic"
    assert data["session"]["state"]["amiodarone_bolus_count"] == 1


def test_v352_atropine_is_contextual_for_unstable_bradycardia():
    client = TestClient(app)
    sid = _load(client)
    _action(client, sid, "cardiac_rhythm_event", {"name": "induce_bradycardia_unstable"})

    data = _action(client, sid, "rcp_drug_bolus", {"drug": "atropine"})
    assert data["result"]["appropriate"] is True
    assert data["result"]["result"] == "bradycardia_context"
    st = data["session"]["state"]
    assert st["atropine_bolus_count"] == 1
    assert st["HR"] >= 90


def test_v352_ui_exposes_rcp_drug_buttons_and_last_drug_status():
    html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "ui" / "styles.css").read_text(encoding="utf-8")

    assert 'id="rcpEpinephrineBtn"' in html
    assert 'id="rcpAmiodaroneBtn"' in html
    assert 'id="rcpAtropineBtn"' in html
    assert 'id="rcpLastDrug"' in html
    assert "async function giveRcpDrug" in js
    assert "sendAction('rcp_drug_bolus'" in js
    assert "$('rcpEpinephrineBtn').onclick = () => giveRcpDrug('epinephrine').catch(reportUiError)" in js
    assert "$('rcpAmiodaroneBtn').onclick = () => giveRcpDrug('amiodarone').catch(reportUiError)" in js
    assert "$('rcpAtropineBtn').onclick = () => giveRcpDrug('atropine').catch(reportUiError)" in js
    assert ".rcp-drug-controls" in css

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


def test_v354_rosc_creates_post_arrest_care_need_and_residual_risks():
    client = TestClient(app)
    sid = _load(client)
    _action(client, sid, "cardiac_rhythm_event", {"name": "induce_vf"})

    shocked = _action(client, sid, "defibrillation", {"energy_J": 40, "synchronized": False})
    st = shocked["session"]["state"]

    assert st["ROSC"] is True
    assert st["post_arrest_phase"] is True
    assert st["cardiac_rhythm"] == "sinus"
    assert st["post_rosc_care_status"] == "needed"
    assert st["post_rosc_oxygenation_optimized"] is False
    assert st["post_rosc_ventilation_optimized"] is False
    assert st["post_rosc_perfusion_support_active"] is False
    assert st["post_rosc_acidosis_burden"] >= 0.5
    assert st["post_rosc_myocardial_dysfunction_risk"] >= 0.35
    assert st["reperfusion_injury_risk"] >= 0.35
    assert st["lactate"] >= 3.0
    assert st["pH_a"] <= 7.30


def test_v354_post_rosc_care_action_marks_stabilization_and_improves_targets():
    client = TestClient(app)
    sid = _load(client)
    _action(client, sid, "cardiac_rhythm_event", {"name": "induce_vf"})
    shocked = _action(client, sid, "defibrillation", {"energy_J": 40, "synchronized": False})
    before = shocked["session"]["state"]

    cared = _action(client, sid, "post_rosc_care", {"fio2_target": 0.6, "map_target": 55, "paco2_target": 45})
    assert cared["result"]["appropriate"] is True
    assert cared["result"]["result"] == "post_rosc_stabilization_started"
    st = cared["session"]["state"]
    assert st["post_rosc_care_status"] == "active"
    assert st["post_rosc_oxygenation_optimized"] is True
    assert st["post_rosc_ventilation_optimized"] is True
    assert st["post_rosc_perfusion_support_active"] is True
    assert st["MAP"] >= 55
    assert st["SaO2"] >= 0.94
    assert st["post_rosc_acidosis_burden"] < before["post_rosc_acidosis_burden"]
    assert st["renal_hypoperfusion_index"] <= before["renal_hypoperfusion_index"]
    assert st["reperfusion_injury_risk"] >= 0.35


def test_v354_post_rosc_care_is_contextual_not_available_during_active_arrest():
    client = TestClient(app)
    sid = _load(client)
    _action(client, sid, "cardiac_rhythm_event", {"name": "induce_pea"})

    cared = _action(client, sid, "post_rosc_care", {})
    assert cared["result"]["appropriate"] is False
    assert cared["result"]["result"] == "not_post_rosc_context"


def test_v354_ui_exposes_post_rosc_status_and_care_control():
    html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "ui" / "styles.css").read_text(encoding="utf-8")

    assert 'id="rcpPostRosc"' in html
    assert 'id="rcpAcidosis"' in html
    assert 'id="rcpRenalRisk"' in html
    assert 'id="rcpReperfusionRisk"' in html
    assert 'id="postRoscCareBtn"' in html
    assert "async function applyPostRoscCare" in js
    assert "sendAction('post_rosc_care'" in js
    assert "$('postRoscCareBtn').onclick = () => applyPostRoscCare().catch(reportUiError)" in js
    assert ".post-rosc-controls" in css

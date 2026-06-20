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


def test_v351_defib_on_vf_is_appropriate_and_can_produce_rosc():
    client = TestClient(app)
    sid = _load(client)
    _action(client, sid, "cardiac_rhythm_event", {"name": "induce_vf"})

    shocked = _action(client, sid, "defibrillation", {"energy_J": 40, "synchronized": False})
    assert shocked["result"]["appropriate"] is True
    assert shocked["result"]["effective"] is True
    assert shocked["result"]["result"] == "rosc"
    st = shocked["session"]["state"]
    assert st["cardiac_rhythm"] == "sinus"
    assert st["ROSC"] is True
    assert st["last_shock_energy_J"] == 40
    assert st["last_shock_mode"] == "defibrillation"
    assert st["last_shock_effective"] is True
    assert st["defibrillation_attempt_count"] == 1


def test_v351_defib_on_pea_is_not_indicated_and_does_not_create_rosc():
    client = TestClient(app)
    sid = _load(client)
    _action(client, sid, "cardiac_rhythm_event", {"name": "induce_pea"})

    shocked = _action(client, sid, "defibrillation", {"energy_J": 40, "synchronized": False})
    assert shocked["result"]["appropriate"] is False
    assert shocked["result"]["effective"] is False
    assert shocked["result"]["result"] == "not_shockable"
    st = shocked["session"]["state"]
    assert st["cardiac_rhythm"] == "pea"
    assert st["cardiac_arrest_active"] is True
    assert st["ROSC"] is False
    assert st["last_shock_appropriate"] is False


def test_v351_sync_cardioversion_converts_pulsed_unstable_vt():
    client = TestClient(app)
    sid = _load(client)
    _action(client, sid, "cardiac_rhythm_event", {"name": "induce_vt_with_pulse"})

    shocked = _action(client, sid, "defibrillation", {"energy_J": 20, "synchronized": True})
    assert shocked["result"]["appropriate"] is True
    assert shocked["result"]["effective"] is True
    assert shocked["result"]["result"] == "converted"
    st = shocked["session"]["state"]
    assert st["cardiac_rhythm"] == "sinus"
    assert st["has_pulse"] is True
    assert st["synchronized_cardioversion_count"] == 1


def test_v351_ui_exposes_energy_defib_and_sync_cardioversion_controls():
    html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "ui" / "styles.css").read_text(encoding="utf-8")

    assert 'id="shockEnergyInput"' in html
    assert 'id="defibAsyncBtn"' in html
    assert 'id="cardioversionSyncBtn"' in html
    assert 'id="rcpLastShock"' in html
    assert "async function deliverShock" in js
    assert "sendAction('defibrillation'" in js
    assert "$('defibAsyncBtn').onclick = () => deliverShock(false).catch(reportUiError)" in js
    assert "$('cardioversionSyncBtn').onclick = () => deliverShock(true).catch(reportUiError)" in js
    assert ".rcp-shock-controls" in css

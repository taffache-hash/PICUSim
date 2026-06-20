from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.server import app


SCENARIO_FILE = "scenarios/unstable_bradycardia_with_pulse_child_v1_31.yaml"


def _load(client):
    loaded = client.post("/session/load", json={"scenario": SCENARIO_FILE, "dt": 1.0})
    assert loaded.status_code == 200, loaded.text
    return loaded.json()["session_id"]


def _step(client, sid, seconds):
    r = client.post(f"/session/{sid}/step", json={"seconds": seconds})
    assert r.status_code == 200, r.text
    return r.json()["state"]


def _action(client, sid, action, payload):
    r = client.post(f"/session/{sid}/action", json={"action": action, "payload": payload})
    assert r.status_code == 200, r.text
    return r.json()


def test_v357_scenario_declares_pulsed_unstable_bradycardia_timeline():
    cfg = yaml.safe_load((ROOT / SCENARIO_FILE).read_text(encoding="utf-8"))

    assert cfg["name"] == "unstable_bradycardia_with_pulse_child_v1_31"
    assert cfg["version"] == "v3.1-step4.37"
    assert cfg["patient"]["weight_kg"] == 20.0
    assert cfg["cardiac_events"][0]["name"] == "induce_bradycardia_unstable"
    assert cfg["cardiac_events"][0]["t"] == 50
    assert "use atropine in the bradycardia context" in cfg["decision_focus"]
    assert "atropine_bolus_count" in cfg["outputs"]


def test_v357_unstable_bradycardia_scenario_is_visible_in_catalog():
    client = TestClient(app)
    r = client.get("/scenarios")
    assert r.status_code == 200, r.text
    scenarios = r.json()["scenarios"]

    match = [s for s in scenarios if s.get("file") == SCENARIO_FILE or s.get("id") == "unstable_bradycardia_with_pulse_child_v1_31"]
    assert match, "unstable bradycardia with pulse scenario is missing from /scenarios"


def test_v357_scenario_progresses_to_pulsed_unstable_bradycardia_not_arrest():
    client = TestClient(app)
    sid = _load(client)

    st = _step(client, sid, 55)
    assert st["cardiac_rhythm"] == "bradycardia_unstable"
    assert st["rhythm_category"] == "pulsed"
    assert st["has_pulse"] is True
    assert st["cardiac_arrest_active"] is False
    assert st["shockable_rhythm"] is False
    assert st["cardiac_arrest_cause"] == "vagal or conduction instability"


def test_v357_pulsed_unstable_bradycardia_uses_atropine_not_shock_or_arrest_epinephrine():
    client = TestClient(app)
    sid = _load(client)
    _step(client, sid, 55)

    shock = _action(client, sid, "defibrillation", {"energy_J": 40, "synchronized": False})
    assert shock["result"]["appropriate"] is False
    assert shock["result"]["effective"] is False
    assert shock["result"]["result"] == "not_indicated"
    assert shock["session"]["state"]["cardiac_rhythm"] == "bradycardia_unstable"

    epi = _action(client, sid, "rcp_drug_bolus", {"drug": "epinephrine"})
    assert epi["result"]["appropriate"] is False
    assert epi["result"]["result"] == "not_arrest_context"
    assert epi["session"]["state"]["epinephrine_bolus_count"] == 1

    atropine = _action(client, sid, "rcp_drug_bolus", {"drug": "atropine"})
    assert atropine["result"]["appropriate"] is True
    assert atropine["result"]["result"] == "bradycardia_context"
    st = atropine["session"]["state"]
    assert st["atropine_bolus_count"] == 1
    assert st["last_rcp_drug"] == "atropine"
    assert st["last_rcp_drug_appropriate"] is True
    assert st["MAP"] >= 55
    assert st["cardiac_arrest_active"] is False
    assert st["ROSC"] is False

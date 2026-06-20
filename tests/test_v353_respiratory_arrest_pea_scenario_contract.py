from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.server import app


SCENARIO_FILE = "scenarios/respiratory_arrest_to_pea_child_v1_31.yaml"


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


def test_v353_scenario_declares_respiratory_arrest_to_pea_timeline():
    cfg = yaml.safe_load((ROOT / SCENARIO_FILE).read_text(encoding="utf-8"))

    assert cfg["name"] == "respiratory_arrest_to_pea_child_v1_31"
    assert cfg["version"] == "v3.1-step4.33"
    assert cfg["patient"]["weight_kg"] == 20.0
    assert cfg["respiratory"]["PaCO2"] >= 60.0
    assert any(p["action"] == "set_lactate" and p["t"] == 75 for p in cfg["perturbations"])
    assert any(p["action"] == "set_pH_a" and p["t"] == 75 for p in cfg["perturbations"])
    assert cfg["cardiac_events"][0]["name"] == "induce_bradycardia_unstable"
    assert cfg["cardiac_events"][0]["t"] == 75
    assert cfg["cardiac_events"][1]["name"] == "induce_pea"
    assert cfg["cardiac_events"][1]["t"] == 115


def test_v353_scenario_is_visible_in_catalog():
    client = TestClient(app)
    r = client.get("/scenarios")
    assert r.status_code == 200, r.text
    scenarios = r.json()["scenarios"]

    match = [s for s in scenarios if s.get("file") == SCENARIO_FILE or s.get("id") == "respiratory_arrest_to_pea_child_v1_31"]
    assert match, "respiratory arrest to PEA scenario is missing from /scenarios"


def test_v353_respiratory_arrest_progresses_to_unstable_bradycardia_then_pea():
    client = TestClient(app)
    sid = _load(client)

    brady = _step(client, sid, 80)
    assert brady["cardiac_rhythm"] == "bradycardia_unstable"
    assert brady["rhythm_category"] == "pulsed"
    assert brady["has_pulse"] is True
    assert brady["cardiac_arrest_active"] is False
    assert brady["shockable_rhythm"] is False
    assert brady["cardiac_arrest_cause"] == "hypoxia"

    pea = _step(client, sid, 45)
    assert pea["cardiac_rhythm"] == "pea"
    assert pea["rhythm_category"] == "nonshockable"
    assert pea["has_pulse"] is False
    assert pea["cardiac_arrest_active"] is True
    assert pea["shockable_rhythm"] is False
    assert pea["cardiac_arrest_cause"] == "hypoxic respiratory arrest"


def test_v353_pea_scenario_accepts_cpr_and_epinephrine_bolus_but_rejects_shock_logic():
    client = TestClient(app)
    sid = _load(client)
    _step(client, sid, 120)
    _step(client, sid, 5)

    cpr = _action(client, sid, "cpr_control", {"active": True, "quality": 0.8, "compression_fraction": 0.9})
    cpr_state = cpr["session"]["state"]
    assert cpr_state["CPR_active"] is True
    assert cpr_state["MAP"] > 10
    assert cpr_state["EtCO2"] > 8

    epi = _action(client, sid, "rcp_drug_bolus", {"drug": "epinephrine"})
    assert epi["result"]["appropriate"] is True
    assert epi["result"]["result"] == "arrest_vasopressor"
    assert epi["session"]["state"]["epinephrine_bolus_count"] == 1

    shock = _action(client, sid, "defibrillation", {"energy_J": 40, "synchronized": False})
    assert shock["result"]["appropriate"] is False
    assert shock["result"]["effective"] is False
    assert shock["result"]["result"] == "not_shockable"
    assert shock["session"]["state"]["cardiac_rhythm"] == "pea"

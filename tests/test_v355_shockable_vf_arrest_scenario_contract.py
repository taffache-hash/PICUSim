from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.server import app


SCENARIO_FILE = "scenarios/shockable_vf_arrest_child_v1_31.yaml"


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


def test_v355_scenario_declares_sudden_vf_shockable_arrest_timeline():
    cfg = yaml.safe_load((ROOT / SCENARIO_FILE).read_text(encoding="utf-8"))

    assert cfg["name"] == "shockable_vf_arrest_child_v1_31"
    assert cfg["version"] == "v3.1-step4.35"
    assert cfg["patient"]["weight_kg"] == 20.0
    assert cfg["cardiac_events"][0]["name"] == "induce_vf"
    assert cfg["cardiac_events"][0]["t"] == 60
    assert "defibrillate asynchronously with adequate energy" in cfg["decision_focus"]
    assert "post_rosc_care_status" in cfg["outputs"]


def test_v355_shockable_vf_scenario_is_visible_in_catalog():
    client = TestClient(app)
    r = client.get("/scenarios")
    assert r.status_code == 200, r.text
    scenarios = r.json()["scenarios"]

    match = [s for s in scenarios if s.get("file") == SCENARIO_FILE or s.get("id") == "shockable_vf_arrest_child_v1_31"]
    assert match, "shockable VF arrest scenario is missing from /scenarios"


def test_v355_scenario_progresses_to_shockable_vf_arrest():
    client = TestClient(app)
    sid = _load(client)

    st = _step(client, sid, 65)
    assert st["cardiac_rhythm"] == "vf"
    assert st["rhythm_category"] == "shockable"
    assert st["has_pulse"] is False
    assert st["cardiac_arrest_active"] is True
    assert st["shockable_rhythm"] is True
    assert st["cardiac_arrest_cause"] == "primary arrhythmia"


def test_v355_shockable_path_uses_cpr_amiodarone_defib_and_post_rosc_care():
    client = TestClient(app)
    sid = _load(client)
    _step(client, sid, 65)

    cpr = _action(client, sid, "cpr_control", {"active": True, "quality": 0.85, "compression_fraction": 0.9})
    assert cpr["session"]["state"]["CPR_active"] is True

    amio = _action(client, sid, "rcp_drug_bolus", {"drug": "amiodarone"})
    assert amio["result"]["appropriate"] is True
    assert amio["result"]["result"] == "shockable_antiarrhythmic"
    assert amio["session"]["state"]["amiodarone_bolus_count"] == 1

    low = _action(client, sid, "defibrillation", {"energy_J": 20, "synchronized": False})
    assert low["result"]["appropriate"] is True
    assert low["result"]["effective"] is False
    assert low["result"]["result"] == "energy_too_low"
    assert low["session"]["state"]["cardiac_rhythm"] == "vf"

    adequate = _action(client, sid, "defibrillation", {"energy_J": 40, "synchronized": False})
    assert adequate["result"]["appropriate"] is True
    assert adequate["result"]["effective"] is True
    assert adequate["result"]["result"] == "rosc"
    st = adequate["session"]["state"]
    assert st["cardiac_rhythm"] == "sinus"
    assert st["ROSC"] is True
    assert st["post_rosc_care_status"] == "needed"
    assert st["defibrillation_attempt_count"] == 2

    cared = _action(client, sid, "post_rosc_care", {"fio2_target": 0.6, "map_target": 55, "paco2_target": 45})
    assert cared["result"]["appropriate"] is True
    assert cared["session"]["state"]["post_rosc_care_status"] == "active"

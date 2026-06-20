from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.server import app


SCENARIO_FILE = "scenarios/unstable_vt_with_pulse_child_v1_31.yaml"


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


def test_v356_scenario_declares_pulsed_unstable_vt_timeline():
    cfg = yaml.safe_load((ROOT / SCENARIO_FILE).read_text(encoding="utf-8"))

    assert cfg["name"] == "unstable_vt_with_pulse_child_v1_31"
    assert cfg["version"] == "v3.1-step4.36"
    assert cfg["patient"]["weight_kg"] == 20.0
    assert cfg["cardiac_events"][0]["name"] == "induce_vt_with_pulse"
    assert cfg["cardiac_events"][0]["t"] == 45
    assert "choose synchronized cardioversion" in cfg["decision_focus"]
    assert "synchronized_cardioversion_count" in cfg["outputs"]


def test_v356_unstable_vt_scenario_is_visible_in_catalog():
    client = TestClient(app)
    r = client.get("/scenarios")
    assert r.status_code == 200, r.text
    scenarios = r.json()["scenarios"]

    match = [s for s in scenarios if s.get("file") == SCENARIO_FILE or s.get("id") == "unstable_vt_with_pulse_child_v1_31"]
    assert match, "unstable VT with pulse scenario is missing from /scenarios"


def test_v356_scenario_progresses_to_pulsed_unstable_vt_not_arrest():
    client = TestClient(app)
    sid = _load(client)

    st = _step(client, sid, 50)
    assert st["cardiac_rhythm"] == "vt_with_pulse"
    assert st["rhythm_category"] == "pulsed"
    assert st["has_pulse"] is True
    assert st["cardiac_arrest_active"] is False
    assert st["shockable_rhythm"] is False
    assert st["cardiac_arrest_cause"] == "unstable tachyarrhythmia"


def test_v356_pulsed_unstable_vt_requires_sync_cardioversion_not_async_defib():
    client = TestClient(app)
    sid = _load(client)
    _step(client, sid, 50)

    async_shock = _action(client, sid, "defibrillation", {"energy_J": 40, "synchronized": False})
    assert async_shock["result"]["appropriate"] is False
    assert async_shock["result"]["effective"] is False
    assert async_shock["result"]["result"] == "not_indicated"
    assert async_shock["session"]["state"]["cardiac_rhythm"] == "vt_with_pulse"

    low_sync = _action(client, sid, "defibrillation", {"energy_J": 5, "synchronized": True})
    assert low_sync["result"]["appropriate"] is True
    assert low_sync["result"]["effective"] is False
    assert low_sync["result"]["result"] == "energy_too_low"
    assert low_sync["session"]["state"]["cardiac_rhythm"] == "vt_with_pulse"

    converted = _action(client, sid, "defibrillation", {"energy_J": 20, "synchronized": True})
    assert converted["result"]["appropriate"] is True
    assert converted["result"]["effective"] is True
    assert converted["result"]["result"] == "converted"
    st = converted["session"]["state"]
    assert st["cardiac_rhythm"] == "sinus"
    assert st["has_pulse"] is True
    assert st["cardiac_arrest_active"] is False
    assert st["ROSC"] is False
    assert st["post_arrest_phase"] is False
    assert st["post_rosc_care_status"] == "none"
    assert st["synchronized_cardioversion_count"] == 2
    assert st["defibrillation_attempt_count"] == 1

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.server import app


VASOACTIVE_ACTIONS = {
    "set_norad": ("norad_mcg_kg_min", 0.12),
    "set_adrenaline": ("adrenaline_mcg_kg_min", 0.05),
    "set_dopamine": ("dopamine_mcg_kg_min", 8.0),
    "set_vasopressin": ("vasopressin_mU_kg_min", 0.04),
    "set_milrinone": ("milrinone_mcg_kg_min", 0.30),
}


def test_v358_septic_shock_accepts_continuous_vasoactive_infusions_and_roundtrips_controls():
    client = TestClient(app)
    loaded = client.post("/session/load", json={"scenario": "septic_shock", "dt": 0.2})
    assert loaded.status_code == 200, loaded.text
    sid = loaded.json()["session_id"]

    for action, (state_key, value) in VASOACTIVE_ACTIONS.items():
        r = client.post(f"/session/{sid}/action", json={"action": action, "payload": {"value": value}})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["result"]["status"] == "applied"
        assert data["result"]["key"] == state_key
        assert data["result"]["value"] == value
        assert data["session"]["state"]["controls"][state_key] == value


def test_v358_ui_confirms_live_drug_controls_from_immediate_action_response():
    js = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")

    assert "function syncControlsFromActionResponse" in js
    assert ".then(syncControlsFromActionResponse)" in js
    assert ".then(data => { syncControlsFromActionResponse(data); return data; })" in js
    assert "confirmControlIfMatched(controlKey, value)" in js
    for action in VASOACTIVE_ACTIONS:
        assert f"{action}: '{VASOACTIVE_ACTIONS[action][0]}'" in js

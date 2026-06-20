from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.server import app


def test_v347_airway_extubation_bag_mask_reintubation_sequence():
    client = TestClient(app)
    loaded = client.post("/session/load", json={"scenario": "healthy_child_20kg", "dt": 0.2})
    assert loaded.status_code == 200, loaded.text
    sid = loaded.json()["session_id"]

    extubated = client.post(
        f"/session/{sid}/action",
        json={
            "action": "airway_event",
            "payload": {"name": "accidental_extubation", "severity": "moderate"},
        },
    )
    assert extubated.status_code == 200, extubated.text
    st = extubated.json()["session"]["state"]
    assert st["intubated"] is False
    assert st["airway_rescue_state"] == "at_risk"

    rescued = client.post(
        f"/session/{sid}/action",
        json={
            "action": "airway_event",
            "payload": {"name": "start_bag_mask_ventilation", "severity": "adequate"},
        },
    )
    assert rescued.status_code == 200, rescued.text
    st = rescued.json()["session"]["state"]
    assert st["bag_mask_ventilation_active"] is True
    assert st["airway_rescue_state"] == "rescued_BVM"
    assert st["airway_event_type"] == "start_bag_mask_ventilation"

    intubated = client.post(
        f"/session/{sid}/action",
        json={
            "action": "airway_event",
            "payload": {"name": "perform_intubation", "severity": "emergency"},
        },
    )
    assert intubated.status_code == 200, intubated.text
    st = intubated.json()["session"]["state"]
    assert st["intubated"] is True
    assert st["airway_interface"] == "ETT"
    assert st["airway_rescue_state"] == "secured_ETT"
    assert st["airway_event_type"] == "perform_intubation"


def test_v347_ui_handles_stale_session_and_current_airway_state():
    js = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")

    assert "function isUnknownSessionError" in js
    assert "function handleUnknownSession" in js
    assert "Sessione non più attiva: ricarica lo scenario." in js
    assert "function reportUiError" in js
    assert ".catch(reportUiError)" in js
    assert "const unresolvedExtubation = !isIntubated && !bagMaskActive" in js

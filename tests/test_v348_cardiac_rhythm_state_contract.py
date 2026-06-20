from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.server import app
from core.bus import PhysiologicalBus
from core.cardiac_arrest_events import SHOCKABLE_RHYTHMS, rhythm_metadata


def test_v348_cardiac_rhythm_taxonomy_has_shockable_and_nonshockable_arrest():
    assert SHOCKABLE_RHYTHMS == {"vf", "pulseless_vt"}
    assert rhythm_metadata("vf") == {
        "cardiac_rhythm": "vf",
        "shockable_rhythm": True,
        "cardiac_arrest_active": True,
        "has_pulse": False,
        "rhythm_category": "shockable",
    }
    assert rhythm_metadata("pea")["rhythm_category"] == "nonshockable"
    assert rhythm_metadata("asystole")["shockable_rhythm"] is False
    assert rhythm_metadata("vt_with_pulse")["has_pulse"] is True


def test_v348_bus_exposes_cardiac_arrest_state_fields():
    bus = PhysiologicalBus()
    for field in [
        "cardiac_rhythm",
        "has_pulse",
        "cardiac_arrest_active",
        "shockable_rhythm",
        "ROSC",
        "CPR_active",
        "CPR_quality",
        "compression_fraction",
        "defibrillation_attempt_count",
        "epinephrine_bolus_count",
        "amiodarone_bolus_count",
        "atropine_bolus_count",
        "reperfusion_injury_risk",
        "renal_hypoperfusion_index",
    ]:
        assert hasattr(bus.state, field), field


def test_v348_api_can_induce_vf_pea_and_rosc_with_bedside_visibility():
    client = TestClient(app)
    loaded = client.post("/session/load", json={"scenario": "healthy_child_20kg", "dt": 0.2})
    assert loaded.status_code == 200, loaded.text
    sid = loaded.json()["session_id"]

    vf = client.post(
        f"/session/{sid}/action",
        json={"action": "cardiac_rhythm_event", "payload": {"name": "induce_vf"}},
    )
    assert vf.status_code == 200, vf.text
    st = vf.json()["session"]["state"]
    assert st["cardiac_rhythm"] == "vf"
    assert st["shockable_rhythm"] is True
    assert st["cardiac_arrest_active"] is True
    assert st["has_pulse"] is False
    assert st["MAP"] <= 10
    assert st["EtCO2"] <= 10

    pea = client.post(
        f"/session/{sid}/action",
        json={"action": "cardiac_rhythm_event", "payload": {"name": "induce_pea"}},
    )
    assert pea.status_code == 200, pea.text
    st = pea.json()["session"]["state"]
    assert st["cardiac_rhythm"] == "pea"
    assert st["shockable_rhythm"] is False
    assert st["cardiac_arrest_active"] is True
    assert st["has_pulse"] is False

    rosc = client.post(
        f"/session/{sid}/action",
        json={"action": "cardiac_rhythm_event", "payload": {"name": "rosc"}},
    )
    assert rosc.status_code == 200, rosc.text
    st = rosc.json()["session"]["state"]
    assert st["cardiac_rhythm"] == "sinus"
    assert st["ROSC"] is True
    assert st["post_arrest_phase"] is True
    assert st["has_pulse"] is True
    assert st["cardiac_arrest_active"] is False
    assert st["reperfusion_injury_risk"] >= 0.2


def test_v348_state_profiles_include_cardiac_arrest_fields():
    text = (ROOT / "api" / "state_profiles.py").read_text(encoding="utf-8")
    for key in [
        "cardiac_rhythm",
        "has_pulse",
        "cardiac_arrest_active",
        "shockable_rhythm",
        "CPR_active",
        "ROSC",
        "reperfusion_injury_risk",
        "renal_hypoperfusion_index",
    ]:
        assert key in text

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.server import app
from core.bus import BusState, PhysiologicalBus
from modules.renal.fluid_balance import FluidBalanceModule


def test_v56a_api_accepts_crystalloid_type_and_rate_and_roundtrips_controls():
    client = TestClient(app)
    loaded = client.post("/session/load", json={"scenario": "septic_shock", "dt": 0.2})
    assert loaded.status_code == 200, loaded.text
    sid = loaded.json()["session_id"]

    r = client.post(f"/session/{sid}/action", json={"action": "set_crystalloid_type", "payload": {"value": "sterofundin"}})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["result"]["key"] == "crystalloid_type"
    assert data["session"]["state"]["controls"]["crystalloid_type"] == "sterofundin"

    r = client.post(f"/session/{sid}/action", json={"action": "set_crystalloid_rate", "payload": {"value": 300}})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["result"]["key"] == "crystalloid_rate_mL_h"
    assert data["session"]["state"]["controls"]["crystalloid_rate_mL_h"] == 300

    stepped = client.post(f"/session/{sid}/step", json={"seconds": 20})
    assert stepped.status_code == 200, stepped.text
    st = stepped.json()["state"]
    assert st["crystalloid_type"] == "sterofundin"
    assert st["crystalloid_effective_mL_h"] == 300
    assert st["crystalloid_active"] is True
    assert st["cumulative_crystalloid_input_mL"] > 0
    assert 0.0 <= st["crystalloid_preload_response"] <= 1.0


def test_v56a_fluid_balance_routes_crystalloid_volume_and_glucosata_to_gir():
    bus = PhysiologicalBus(BusState())
    bus.update({
        "weight_kg": 20.0,
        "MAP": 45.0,
        "T_core": 37.0,
        "CVP": 4.0,
        "PEEP": 5.0,
        "fluid_balance": -300.0,
        "crystalloid_type": "glucosata",
        "crystalloid_rate_mL_h": 240.0,
        "shock_hypovolemia_index": 0.6,
        "endothelial_leak_index": 0.0,
        "norad_mcg_kg_min": 0.0,
        "ADH_water_retention_index": 0.0,
    })
    mod = FluidBalanceModule()
    mod.initialize(bus)
    before = float(bus.get("cumulative_fluid_input_mL"))
    mod.step(bus, 60.0)

    assert bus.get("crystalloid_type") == "dextrose_5"
    assert bus.get("crystalloid_active") is True
    assert abs(float(bus.get("crystalloid_effective_mL_h")) - 240.0) < 1e-6
    assert float(bus.get("cumulative_crystalloid_input_mL")) >= 3.9
    assert float(bus.get("cumulative_fluid_input_mL")) > before
    assert float(bus.get("GIR_mg_kg_min")) >= 10.0
    assert 0.0 <= float(bus.get("crystalloid_MAP_support_mmHg")) <= 10.0
    assert 0.0 <= float(bus.get("crystalloid_renal_perfusion_gain")) <= 1.0


def test_v56a_ui_exposes_main_page_and_panel_fluid_controls():
    html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "ui" / "styles.css").read_text(encoding="utf-8")

    assert 'id="fluidQuickPanel"' in html
    assert 'id="quickCrystalloidRate"' in html
    assert 'id="quickCrystalloidType"' in html
    assert 'id="fluidInfusionsPanel"' in html
    assert 'data-drug="set_crystalloid_rate"' in html
    assert 'data-crystalloid-type="1"' in html
    assert "set_crystalloid_rate: 'crystalloid_rate_mL_h'" in js
    assert "sendAction('set_crystalloid_type'" in js
    assert "renderFluidControls(st)" in js
    assert ".fluid-quick-panel" in css

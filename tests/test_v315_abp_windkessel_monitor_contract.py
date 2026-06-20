from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.server import app
from api.state_profiles import waveform_fast_state, bedside_state
from core.bus import BusState, PhysiologicalBus
from modules.cardiovascular.circulation import CirculationModule


def _step_circulation(bus: PhysiologicalBus, steps: int = 20, dt: float = 0.2):
    module = CirculationModule()
    module.initialize(bus)
    for _ in range(steps):
        module.step(bus, dt)
    return bus.state


def test_v315_circulation_exposes_sbp_dbp_from_model_outputs():
    bus = PhysiologicalBus()
    bus.update({"MAP": 65.0, "CO": 3.5, "SV": 32.0, "CVP": 5.0, "PAP_mean": 15.0, "PAWP": 8.0})
    st = _step_circulation(bus)

    assert st.SBP == st.SAP
    assert st.DBP == st.DAP
    assert st.SBP > st.DBP
    assert st.arterial_pulse_pressure == st.SBP - st.DBP
    assert st.arterial_pressure_source == "circulation_windkessel_envelope"


def test_v315_waveform_profile_uses_sap_dap_not_cosmetic_map_constants():
    state = BusState(MAP=50.0, SAP=62.0, DAP=42.0, SBP=62.0, DBP=42.0)
    wf = waveform_fast_state(state)
    assert wf["SBP"] == 62.0
    assert wf["DBP"] == 42.0
    assert wf["SBP"] != 70.0  # old MAP + 20 cosmetic fallback
    assert wf["DBP"] != 35.0  # old MAP - 15 cosmetic fallback


def test_v315_bedside_profile_includes_abp_pair_for_ui():
    state = BusState(MAP=55.0, SAP=68.0, DAP=48.0, SBP=68.0, DBP=48.0)
    bs = bedside_state(state)
    assert bs["SBP"] == 68.0
    assert bs["DBP"] == 48.0
    assert bs["arterial_pulse_pressure"] == 20.0


def test_v315_api_waveform_profile_returns_model_abp_values():
    client = TestClient(app)
    r = client.post('/session/load', json={'scenario': 'healthy_child_20kg', 'dt': 0.2})
    assert r.status_code == 200, r.text
    sid = r.json()['session_id']
    for _ in range(3):
        step = client.post(f'/session/{sid}/step', json={'seconds': 1})
        assert step.status_code == 200, step.text

    r = client.get(f'/session/{sid}/state?profile=waveform_fast')
    assert r.status_code == 200, r.text
    wf = r.json()['state']
    assert 'SBP' in wf and 'DBP' in wf
    assert wf['SBP'] > wf['DBP']
    assert wf['SBP'] != round(wf['MAP'] + 20.0, 0) or wf['DBP'] != round(max(wf['MAP'] - 15.0, 10.0), 0)


def test_v315_ui_abp_waveform_consumes_sbp_dbp():
    js = (ROOT / 'ui' / 'canvas_waveforms.js').read_text(encoding="utf-8")
    app = (ROOT / 'ui' / 'app.js').read_text(encoding="utf-8")
    html = (ROOT / 'ui' / 'index.html').read_text(encoding="utf-8")

    assert 'this.state.SBP ?? this.state.SAP' in js
    assert 'this.state.DBP ?? this.state.DAP' in js
    assert 'baseline = Math.max(25, Math.min(120, map))' not in js
    assert 'const pressure = dbp + (sbp - dbp) * pulseShape' in js
    assert 'id="vABP"' in html
    assert "const sbp = st.SBP ?? st.SAP;" in app

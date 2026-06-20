from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.server import app
from api.state_profiles import waveform_fast_state, bedside_state
from core.bus import BusState, PhysiologicalBus
from modules.respiratory.gas_exchange import GasExchangeModule


def test_v316_etco2_target_widens_with_dead_space_at_same_paco2():
    module = GasExchangeModule()
    bus = PhysiologicalBus()
    low_et, low_grad, _ = module._end_tidal_co2_target(
        bus=bus,
        PaCO2=45.0,
        deadspace=0.25,
        shunt=0.10,
        sigma=0.35,
        VA_dot=3.0,
        VCO2=100.0,
        CO=3.8,
        weight_kg=20.0,
    )
    high_et, high_grad, _ = module._end_tidal_co2_target(
        bus=bus,
        PaCO2=45.0,
        deadspace=0.70,
        shunt=0.10,
        sigma=0.35,
        VA_dot=3.0,
        VCO2=100.0,
        CO=3.8,
        weight_kg=20.0,
    )
    assert high_et < low_et
    assert high_grad > low_grad


def test_v316_etco2_target_falls_with_low_cardiac_output_at_same_paco2():
    module = GasExchangeModule()
    bus = PhysiologicalBus()
    normal_et, normal_grad, normal_pf = module._end_tidal_co2_target(
        bus=bus,
        PaCO2=45.0,
        deadspace=0.30,
        shunt=0.10,
        sigma=0.35,
        VA_dot=3.0,
        VCO2=100.0,
        CO=3.8,
        weight_kg=20.0,
    )
    low_et, low_grad, low_pf = module._end_tidal_co2_target(
        bus=bus,
        PaCO2=45.0,
        deadspace=0.30,
        shunt=0.10,
        sigma=0.35,
        VA_dot=3.0,
        VCO2=100.0,
        CO=0.7,
        weight_kg=20.0,
    )
    assert low_et < normal_et
    assert low_grad > normal_grad
    assert low_pf < normal_pf


def test_v316_gas_exchange_writes_etco2_and_alias_to_bus():
    bus = PhysiologicalBus()
    bus.update({
        "RR_total": 24.0,
        "RR": 24.0,
        "Vt": 180.0,
        "CO": 3.2,
        "VO2": 110.0,
        "airway_VdVt_add": 0.35,
        "air_trapping_index": 0.4,
        "airway_obstruction_index": 0.5,
    })
    module = GasExchangeModule()
    module.initialize(bus)
    for _ in range(100):
        module.step(bus, 0.2)

    st = bus.state
    assert hasattr(st, "EtCO2")
    assert hasattr(st, "EtCO2_proxy")
    assert st.EtCO2_proxy == st.EtCO2
    assert st.etco2_source == "gas_exchange_v316_model_coupled"
    assert st.EtCO2 < st.PaCO2
    assert st.etco2_pa_gradient > 5.0
    assert st.etco2_deadspace_factor >= 0.30


def test_v316_waveform_profiles_use_model_etco2_not_paco2_minus_five():
    state = BusState(PaCO2=80.0, EtCO2=42.0, EtCO2_proxy=42.0)
    wf = waveform_fast_state(state)
    bs = bedside_state(state)
    assert wf["EtCO2"] == 42.0
    assert wf["EtCO2_proxy"] == 42.0
    assert wf["EtCO2_proxy"] != 75.0
    assert bs["EtCO2"] == 42.0


def test_v316_api_waveform_returns_real_etco2_key():
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
    assert 'EtCO2' in wf and 'EtCO2_proxy' in wf
    assert wf['EtCO2_proxy'] == wf['EtCO2']
    assert wf['EtCO2'] < wf['PaCO2']


def test_v316_ui_consumes_etco2_before_legacy_proxy():
    js = (ROOT / 'ui' / 'canvas_waveforms.js').read_text(encoding="utf-8")
    app = (ROOT / 'ui' / 'app.js').read_text(encoding="utf-8")
    html = (ROOT / 'ui' / 'index.html').read_text(encoding="utf-8")

    assert 'this.state.EtCO2 ?? this.state.EtCO2_proxy' in js
    assert 'EtCO₂ <span id="vEtCO2">' in html
    assert 'st.EtCO2 ?? st.EtCO2_proxy' in app

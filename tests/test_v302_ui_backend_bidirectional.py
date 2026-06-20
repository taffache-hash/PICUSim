from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.server import app


def test_v302_bedside_state_exposes_control_roundtrip_values():
    client = TestClient(app)
    r = client.post('/session/load', json={'scenario': 'healthy_child_20kg', 'dt': 0.5})
    assert r.status_code == 200, r.text
    data = r.json()
    sid = data['session_id']
    controls = data['state']['controls']
    for key in ['FiO2', 'PEEP', 'RR', 'adrenaline_mcg_kg_min', 'norad_mcg_kg_min', 'fentanyl_mcg_kg_h']:
        assert key in controls

    r = client.post(f'/session/{sid}/action', json={'action': 'set_adrenaline', 'payload': {'value': 0.2}})
    assert r.status_code == 200, r.text
    state = r.json()['session']['state']
    assert state['controls']['adrenaline_mcg_kg_min'] == 0.2

    r = client.post(f'/session/{sid}/action', json={'action': 'set_peep', 'payload': {'value': 8}})
    assert r.status_code == 200, r.text
    state = r.json()['session']['state']
    assert state['controls']['PEEP'] == 8


def test_v302_controls_profile_returns_only_command_values():
    client = TestClient(app)
    r = client.post('/session/load', json={'scenario': 'healthy_child_20kg', 'dt': 0.5})
    assert r.status_code == 200, r.text
    sid = r.json()['session_id']
    r = client.get(f'/session/{sid}/state?profile=controls')
    assert r.status_code == 200, r.text
    controls = r.json()['state']
    assert 'FiO2' in controls
    assert 'adrenaline_mcg_kg_min' in controls
    assert 'HR' not in controls
    assert 'MAP' not in controls


def test_v302_ui_syncs_controls_from_backend_state():
    js = (ROOT / 'ui' / 'app.js').read_text(encoding="utf-8")
    assert 'function syncControlsFromState' in js
    assert 'RANGE_CONTROL_BINDINGS' in js
    assert 'DRUG_CONTROL_BINDINGS' in js
    assert "set_adrenaline: 'adrenaline_mcg_kg_min'" in js
    assert "set_norad: 'norad_mcg_kg_min'" in js
    assert 'syncControlsFromState(st);' in js
    assert 'document.activeElement === el' in js

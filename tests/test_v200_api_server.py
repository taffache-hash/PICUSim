from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.server import app


def test_api_health_and_scenarios():
    client = TestClient(app)
    r = client.get('/health')
    assert r.status_code == 200
    assert r.json()['status'] == 'ok'
    r = client.get('/scenarios')
    assert r.status_code == 200
    scenarios = r.json()['scenarios']
    assert isinstance(scenarios, list)
    assert any(s['id'] == 'healthy_child_20kg' for s in scenarios)


def test_api_load_step_state_history_delete():
    client = TestClient(app)
    r = client.post('/session/load', json={'scenario': 'healthy_child_20kg', 'dt': 0.5})
    assert r.status_code == 200, r.text
    data = r.json()
    sid = data['session_id']
    assert data['status'] == 'paused'
    assert data['state']['time_s'] == 0.0

    r = client.post(f'/session/{sid}/step', json={'seconds': 2.0})
    assert r.status_code == 200, r.text
    assert r.json()['time_s'] >= 1.5

    r = client.get(f'/session/{sid}/state?profile=waveform')
    assert r.status_code == 200
    st = r.json()['state']
    assert 'HR' in st and 'EtCO2_proxy' in st

    r = client.get(f'/session/{sid}/history?limit=10')
    assert r.status_code == 200
    assert len(r.json()['history']) >= 1

    r = client.delete(f'/session/{sid}')
    assert r.status_code == 200


def test_api_action_router_set_fio2_and_airway_event():
    client = TestClient(app)
    r = client.post('/session/load', json={'scenario': 'airway_rsi_hypoxic_child_v1_24', 'dt': 0.5})
    assert r.status_code == 200, r.text
    sid = r.json()['session_id']

    r = client.post(f'/session/{sid}/action', json={'action': 'set_fio2', 'payload': {'value': 1.0}})
    assert r.status_code == 200, r.text
    assert r.json()['session']['state']['FiO2'] == 1.0

    r = client.post(f'/session/{sid}/action', json={'action': 'airway_event', 'payload': {'name': 'failed_intubation_attempt', 'severity': 'moderate'}})
    assert r.status_code == 200, r.text
    st = r.json()['session']['state']
    assert st['airway_event_type'] == 'failed_intubation_attempt'

    client.delete(f'/session/{sid}')

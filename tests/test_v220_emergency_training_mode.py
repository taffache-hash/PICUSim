from fastapi.testclient import TestClient

from api.server import app


def test_training_scenarios_endpoint_exposes_airway_and_epals():
    c = TestClient(app)
    r = c.get('/training/scenarios')
    assert r.status_code == 200
    rows = r.json()['scenarios']
    ids = {x['id'] for x in rows}
    cats = {x['category'] for x in rows}
    assert 'airway_failed_intubation_cannot_oxygenate_v1_25' in ids
    assert 'epals_hypoxia_airway_obstruction' in ids
    assert {'airway_decision', 'EPALS_5H', 'EPALS_5T'} <= cats


def test_session_debrief_endpoint_returns_metrics():
    c = TestClient(app)
    r = c.post('/session/load', json={'scenario': 'airway_rsi_hypoxic_child_v1_24', 'dt': 1.0})
    assert r.status_code == 200
    sid = r.json()['session_id']
    r = c.post(f'/session/{sid}/step', json={'seconds': 20})
    assert r.status_code == 200
    r = c.get(f'/session/{sid}/debrief')
    assert r.status_code == 200
    d = r.json()['debrief']
    assert d['status'] == 'ok'
    assert 'SpO2_nadir' in d['metrics']
    assert isinstance(d['flags'], list)
    assert isinstance(d['threshold_events'], list)


def test_web_monitor_contains_emergency_training_panel():
    c = TestClient(app)
    r = c.get('/monitor')
    assert r.status_code == 200
    text = r.text
    assert 'Emergency training' in text
    assert 'Generate debrief' in text

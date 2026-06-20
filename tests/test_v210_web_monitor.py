from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.server import app


def test_web_monitor_routes_and_assets():
    client = TestClient(app)
    r = client.get('/')
    assert r.status_code == 200
    assert 'PDT Clinical Training Console' in r.text
    assert '/ui/app.js' in r.text

    r = client.get('/monitor')
    assert r.status_code == 200
    assert 'Bedside monitor' in r.text

    for path in ['/ui/styles.css', '/ui/app.js', '/ui/canvas_waveforms.js']:
        r = client.get(path)
        assert r.status_code == 200, path
        assert len(r.text) > 500


def test_api_reset_and_events_for_ui():
    client = TestClient(app)
    r = client.post('/session/load', json={'scenario': 'airway_rsi_hypoxic_child_v1_24', 'dt': 0.5})
    assert r.status_code == 200, r.text
    sid = r.json()['session_id']

    r = client.post(f'/session/{sid}/action', json={'action': 'airway_event', 'payload': {'name': 'failed_intubation_attempt'}})
    assert r.status_code == 200, r.text

    r = client.get(f'/session/{sid}/events')
    assert r.status_code == 200
    events = r.json()['events']
    assert any('airway_event' in str(e.get('label', '')) or e.get('result', {}).get('event') == 'failed_intubation_attempt' for e in events)

    r = client.post(f'/session/{sid}/reset')
    assert r.status_code == 200, r.text
    new_sid = r.json()['session_id']
    assert new_sid != sid
    assert r.json()['time_s'] == 0.0

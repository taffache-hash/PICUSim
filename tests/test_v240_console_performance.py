
from pathlib import Path
import sys
import json
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from api.server import app
from api.performance import json_size_bytes
from start_pdt_console import find_free_port


def test_v24_fast_profiles_and_performance_endpoint():
    client = TestClient(app)
    r = client.get('/performance/config')
    assert r.status_code == 200
    assert 'bedside_fast' in r.json()['profiles']

    r = client.post('/session/load', json={
        'scenario': 'airway_rsi_hypoxic_child_v1_24',
        'dt': 0.5,
        'max_history_points': 100,
        'history_window_s': 300,
        'history_decimation_s': 1.0,
    })
    assert r.status_code == 200, r.text
    sid = r.json()['session_id']

    r = client.post(f'/session/{sid}/step', json={'seconds': 5})
    assert r.status_code == 200, r.text

    fast = client.get(f'/session/{sid}/state?profile=bedside_fast').json()
    wave = client.get(f'/session/{sid}/state?profile=waveform_fast').json()
    training = client.get(f'/session/{sid}/state?profile=training').json()
    assert json_size_bytes(fast) < 6000
    assert json_size_bytes(wave) < 4000
    assert 'airway_interface' in training['state']

    perf = client.get(f'/session/{sid}/performance')
    assert perf.status_code == 200
    assert perf.json()['performance']['history_points'] <= 100

    hist = client.get(f'/session/{sid}/history?limit=10&profile=training')
    assert hist.status_code == 200
    assert hist.json()['profile'] == 'training'
    client.delete(f'/session/{sid}')


def test_v24_launcher_port_helper():
    port = find_free_port('127.0.0.1', start=8010, attempts=20)
    assert isinstance(port, int)
    assert 8010 <= port < 8030

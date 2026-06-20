from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from api.server import app


def test_v329_ventilator_rr_command_survives_physiologic_rr_updates():
    client = TestClient(app)
    r = client.post('/session/load', json={'scenario': 'ventilator_modes_demo', 'dt': 0.2})
    assert r.status_code == 200, r.text
    sid = r.json()['session_id']
    client.post(f'/session/{sid}/step', json={'seconds': 5.0})

    r = client.post(f'/session/{sid}/action', json={'action': 'set_rr', 'payload': {'value': 35}})
    assert r.status_code == 200, r.text
    assert r.json()['result']['key'] == 'ventilator_RR_set'
    client.post(f'/session/{sid}/step', json={'seconds': 10.0})
    high = client.get(f'/session/{sid}/state?profile=waveform_fast').json()['state']
    controls = client.get(f'/session/{sid}/state?profile=controls').json()['state']
    assert abs(high['RR_total'] - 35) < 1.0
    assert controls['RR'] == 35
    assert controls['ventilator_RR_set'] == 35

    client.post(f'/session/{sid}/action', json={'action': 'set_rr', 'payload': {'value': 12}})
    client.post(f'/session/{sid}/step', json={'seconds': 10.0})
    low = client.get(f'/session/{sid}/state?profile=waveform_fast').json()['state']
    assert abs(low['RR_total'] - 12) < 1.0
    assert low['PaCO2'] > high['PaCO2']

from pathlib import Path
import csv
import io
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from api.server import app


def test_v51a_reproducibility_pack_exports_and_saves():
    client = TestClient(app)
    loaded = client.post('/session/load', json={
        'scenario': 'epals_v2_septic_shock_warm',
        'dt': 1.0,
        'max_history_points': 300,
        'history_window_s': 600,
        'history_decimation_s': 1.0,
    })
    assert loaded.status_code == 200, loaded.text
    sid = loaded.json()['session_id']

    action = client.post(f'/session/{sid}/action', json={
        'action': 'airway_event',
        'payload': {'name': 'failed_intubation_attempt', 'severity': 'moderate'},
    })
    assert action.status_code == 200, action.text
    stepped = client.post(f'/session/{sid}/step', json={'seconds': 12})
    assert stepped.status_code == 200, stepped.text

    pack_resp = client.get(f'/session/{sid}/reproducibility?format=json&seed=123')
    assert pack_resp.status_code == 200, pack_resp.text
    pack = pack_resp.json()
    assert pack['manifest']['schema'] == 'pdt-reproducibility-pack-v5.1A'
    assert pack['manifest']['seed'] == 123
    assert pack['manifest']['scenario_file_sha256']
    assert pack['manifest']['timeline_rows'] >= 2
    assert pack['manifest']['action_rows'] >= 1
    assert 'session_bundle' in pack
    assert pack['timeline_rows']
    assert pack['action_rows']
    assert 'Reproducibility Pack' in pack['structured_report_md']

    timeline = client.get(f'/session/{sid}/reproducibility?format=timeline_csv')
    assert timeline.status_code == 200, timeline.text
    rows = list(csv.DictReader(io.StringIO(timeline.text)))
    assert rows
    assert 'time_s' in rows[0]
    assert 'MAP' in rows[0]

    actions = client.get(f'/session/{sid}/reproducibility?format=interventions_csv')
    assert actions.status_code == 200, actions.text
    action_rows = list(csv.DictReader(io.StringIO(actions.text)))
    assert any(r['action'] == 'airway_event' for r in action_rows)

    md = client.get(f'/session/{sid}/reproducibility?format=md')
    assert md.status_code == 200, md.text
    assert 'Scenario SHA-256' in md.text

    saved = client.post(f'/session/{sid}/reproducibility/save', json={'basename': 'test_v51a_pack', 'seed': 123})
    assert saved.status_code == 200, saved.text
    files = saved.json()['saved']['files']
    for rel in files.values():
        assert (ROOT / rel).exists(), rel

    client.delete(f'/session/{sid}')

from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from api.server import app


def test_v25_export_save_and_load_saved_session():
    client = TestClient(app)
    r = client.post('/session/load', json={
        'scenario': 'airway_rsi_hypoxic_child_v1_24',
        'dt': 1.0,
        'max_history_points': 200,
        'history_window_s': 300,
        'history_decimation_s': 1.0,
    })
    assert r.status_code == 200, r.text
    sid = r.json()['session_id']

    r = client.post(f'/session/{sid}/action', json={'action': 'airway_event', 'payload': {'name': 'failed_intubation_attempt', 'severity': 'moderate'}})
    assert r.status_code == 200, r.text
    r = client.post(f'/session/{sid}/step', json={'seconds': 10})
    assert r.status_code == 200, r.text
    r = client.post(f'/session/{sid}/instructor/note', json={'text': 'Learner delayed rescue ventilation.', 'kind': 'observation', 'pinned': True})
    assert r.status_code == 200, r.text

    exported = client.get(f'/session/{sid}/export?format=json')
    assert exported.status_code == 200, exported.text
    bundle = exported.json()
    assert bundle['schema'] == 'pdt-session-save-v2.5'
    assert bundle['session']['scenario']
    assert bundle['debrief']['status'] == 'ok'
    assert bundle['instructor']['notes']
    assert any(e.get('action') == 'airway_event' for e in bundle['event_log'])

    md = client.get(f'/session/{sid}/export?format=md')
    assert md.status_code == 200, md.text
    assert 'PDT Session Report' in md.text
    assert 'Not for clinical use' in md.text

    saved = client.post(f'/session/{sid}/save', json={'basename': 'test_v25_saved_session', 'history_limit': 1000})
    assert saved.status_code == 200, saved.text
    saved_json = ROOT / saved.json()['saved']['json_path']
    saved_md = ROOT / saved.json()['saved']['markdown_path']
    assert saved_json.exists()
    assert saved_md.exists()

    loaded = client.post('/session/load_saved', json={'path': str(saved_json.relative_to(ROOT)), 'replay_actions': True})
    assert loaded.status_code == 200, loaded.text
    restored = loaded.json()
    assert restored['scenario'] == bundle['session']['scenario']
    assert restored['time_s'] >= bundle['session']['time_s'] - 1.0
    assert restored['state']['airway_event_type'] in {'failed_intubation_attempt', 'none', ''} or restored['state']['intubation_attempt_count'] >= 1

    client.delete(f'/session/{sid}')
    client.delete(f"/session/{restored['session_id']}")

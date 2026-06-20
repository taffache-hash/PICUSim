from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from api.server import app


def test_v27_authoring_templates_draft_validate_save_and_load():
    client = TestClient(app)
    r = client.get('/authoring/templates')
    assert r.status_code == 200, r.text
    templates = r.json()['templates']
    assert any(t['id'] == 'airway_deterioration' for t in templates)

    draft = client.post('/authoring/draft', json={
        'template_id': 'airway_deterioration',
        'title': 'Test authored airway scenario',
        'description': 'Authored airway scenario for automated test. Not for clinical use.',
        'severity': 'severe',
        'age_y': 4,
        'weight_kg': 18,
        'duration_s': 360,
        'debrief_questions': ['What failed first?', 'When was rescue ventilation started?']
    })
    assert draft.status_code == 200, draft.text
    body = draft.json()
    assert body['validation']['status'] == 'pass', body
    assert 'yaml_text' in body and 'airway_events' in body['yaml_text']

    val = client.post('/authoring/validate', json={'yaml_text': body['yaml_text']})
    assert val.status_code == 200, val.text
    assert val.json()['validation']['status'] == 'pass'

    filename = 'user_test_authored_airway_scenario_v2_7.yaml'
    saved = client.post('/authoring/save', json={'yaml_text': body['yaml_text'], 'filename': filename, 'overwrite': True, 'publish_to_scenarios': True})
    assert saved.status_code == 200, saved.text
    assert saved.json()['scenario_id'] == filename.replace('.yaml', '')
    assert (ROOT / saved.json()['path']).exists()

    scenarios = client.get('/scenarios').json()['scenarios']
    assert any(s['id'] == filename.replace('.yaml', '') for s in scenarios)

    loaded = client.post('/session/load', json={'scenario': filename.replace('.yaml', ''), 'dt': 1.0})
    assert loaded.status_code == 200, loaded.text
    sid = loaded.json()['session_id']
    assert loaded.json()['scenario'] == 'test_authored_airway_scenario'
    client.delete(f'/session/{sid}')


def test_v27_monitor_contains_authoring_panel_assets():
    client = TestClient(app)
    html = client.get('/monitor').text
    assert 'Scenario authoring assistant' in html
    assert 'authoringPanel' in html
    assert 'authorYamlText' in html
    js = (ROOT / 'ui' / 'app.js').read_text(encoding="utf-8")
    assert '/authoring/draft' in js
    assert 'loadAuthoringTemplates' in js
    css = (ROOT / 'ui' / 'styles.css').read_text(encoding="utf-8")
    assert '.yaml-editor' in css

from fastapi.testclient import TestClient

from api.server import app


def test_instructor_presets_endpoint():
    c = TestClient(app)
    r = c.get('/instructor/presets')
    assert r.status_code == 200
    presets = r.json()['presets']
    ids = {p['id'] for p in presets}
    assert 'failed_attempt_moderate' in ids
    assert 'bag_mask_adequate' in ids
    assert all(p.get('available') is not False for p in presets)


def test_instructor_note_visibility_and_report():
    c = TestClient(app)
    r = c.post('/session/load', json={'scenario': 'airway_rsi_hypoxic_child_v1_24', 'dt': 1.0})
    assert r.status_code == 200, r.text
    sid = r.json()['session_id']

    r = c.post(f'/session/{sid}/instructor/visibility', json={'hide_diagnosis': True})
    assert r.status_code == 200, r.text
    assert r.json()['learner_diagnosis_hidden'] is True

    r = c.post(f'/session/{sid}/instructor/note', json={'text': 'Learner delayed BVM', 'kind': 'teaching_point', 'pinned': True})
    assert r.status_code == 200, r.text
    assert r.json()['note']['pinned'] is True

    r = c.post(f'/session/{sid}/action', json={'action': 'airway_event', 'payload': {'name': 'failed_intubation_attempt', 'severity': 'moderate'}})
    assert r.status_code == 200, r.text
    r = c.post(f'/session/{sid}/step', json={'seconds': 5})
    assert r.status_code == 200, r.text

    r = c.get(f'/session/{sid}/instructor/report')
    assert r.status_code == 200, r.text
    report = r.json()['report']
    assert report['learner_diagnosis_hidden'] is True
    assert report['summary']['notes'] >= 1
    assert report['event_count'] >= 1

    r = c.get(f'/session/{sid}/instructor/report?format=md')
    assert r.status_code == 200
    assert '# PDT instructor report' in r.text


def test_web_monitor_contains_instructor_panel():
    c = TestClient(app)
    r = c.get('/monitor')
    assert r.status_code == 200
    text = r.text
    assert 'Instructor mode' in text
    assert 'Hide diagnosis from learner' in text
    assert 'Instructor report' in text

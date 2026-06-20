from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from api.server import app
from core.airway_events import airway_event_to_perturbation, load_airway_event_spec


def test_v333_perform_intubation_moderate_is_resolved_for_backward_compatibility():
    p = airway_event_to_perturbation({"name": "perform_intubation", "severity": "moderate", "t": 0}, load_airway_event_spec())
    assert "perform_intubation" in p.label


def test_v333_api_quick_intubation_action_no_longer_raises_unknown_moderate():
    client = TestClient(app)
    r = client.post('/session/load', json={'scenario': 'healthy_child_20kg', 'dt': 0.2})
    assert r.status_code == 200, r.text
    sid = r.json()['session_id']
    r = client.post(f'/session/{sid}/action', json={'action': 'airway_event', 'payload': {'name': 'perform_intubation', 'severity': 'moderate'}})
    assert r.status_code == 200, r.text
    st = r.json()['session']['state']
    assert st['intubated'] is True
    assert st['airway_interface'] == 'ETT'


def test_v333_ui_uses_event_specific_airway_severities_and_audio_toggle():
    html = (ROOT / 'ui' / 'index.html').read_text(encoding='utf-8')
    js = (ROOT / 'ui' / 'app.js').read_text(encoding='utf-8')
    assert 'id="audioMonitorBtn"' in html
    assert 'data-event="perform_intubation" data-severity="emergency"' in html
    assert 'data-event="start_bag_mask_ventilation" data-severity="adequate"' in html
    assert 'AIRWAY_EVENT_DEFAULT_SEVERITIES' in js
    assert 'toggleAudioMonitor' in js
    assert 'saturationToneHz' in js
    assert 'driveMonitorAudio(now);' in js


def test_v333_abp_waveform_amplitude_is_pulse_pressure_coupled():
    js = (ROOT / 'ui' / 'canvas_waveforms.js').read_text(encoding='utf-8')
    assert 'const pulsePressure = Math.max(4, sbp - dbp);' in js
    assert 'const pulseGain = Math.max(0.35, Math.min(1.35, pulsePressure / 35));' in js
    assert 'const pressure = map + (modelPressure - map) * pulseGain;' in js

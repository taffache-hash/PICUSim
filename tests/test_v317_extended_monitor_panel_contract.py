from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from api.server import app


def test_v317_ui_exposes_extended_monitor_panel_and_tab():
    html = (ROOT / 'ui' / 'index.html').read_text(encoding="utf-8")
    assert 'data-open-panel="extendedMonitorPanel"' in html
    assert 'data-panel-tab="extendedMonitorPanel"' in html
    assert 'id="extendedMonitorPanel"' in html
    assert 'id="extendedMonitorGrid"' in html
    assert 'Emodinamica' not in html  # rendered dynamically by JS, not duplicated in HTML


def test_v317_js_defines_five_extended_monitor_groups_and_fetches_full_profile():
    js = (ROOT / 'ui' / 'app.js').read_text(encoding="utf-8")
    for label in [
        'Emodinamica / perfusione',
        'Respiratorio',
        'Metabolico / labs',
        'Neurologico / sedazione',
        'Renale / fluidi',
    ]:
        assert label in js
    for key in ['lactate', 'glucose_mmol_L', 'CVP', 'DO2', 'VO2', 'ICP_mmHg', 'GCS_proxy', 'RASS_proxy', 'urine_rate_mL_h', 'fluid_balance']:
        assert key in js
    assert "profile=full" in js
    assert 'function renderExtendedMonitor' in js
    assert 'function refreshExtendedMonitor' in js
    assert 'function deriveScvO2' in js


def test_v317_css_supports_extended_monitor_grid():
    css = (ROOT / 'ui' / 'styles.css').read_text(encoding="utf-8")
    assert '.extended-monitor-grid' in css
    assert '.extended-card' in css
    assert '.extended-param-grid' in css
    assert '.extended-param.missing' in css


def test_v317_existing_full_profile_contains_core_extended_monitor_values():
    client = TestClient(app)
    r = client.post('/session/load', json={'scenario': 'healthy_child_20kg', 'dt': 0.5})
    assert r.status_code == 200, r.text
    sid = r.json()['session_id']
    r = client.get(f'/session/{sid}/state?profile=full')
    assert r.status_code == 200, r.text
    state = r.json()['state']
    for key in ['lactate', 'glucose_mmol_L', 'CVP', 'DO2', 'VO2', 'GCS_proxy', 'RASS_proxy', 'urine_rate_mL_h', 'fluid_balance', 'CO', 'Hb', 'SaO2']:
        assert key in state

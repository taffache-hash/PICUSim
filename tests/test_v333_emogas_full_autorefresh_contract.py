from pathlib import Path
import sys
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_emogas_panel_autorefreshes_full_profile_when_open():
    js = (ROOT / 'ui' / 'app.js').read_text(encoding='utf-8')
    assert 'function shouldRefreshFullProfilePanels()' in js
    assert 'isEmogasOpen()' in js
    assert 'setInterval(() =>' in js
    assert 'profile=full' in js
    assert 'waiting full profile' in js
    assert 'full profile + bedside update' in js


def test_full_state_contains_complete_emogas_fields_bedside_fast_does_not():
    from api.server import app
    client = TestClient(app)
    first = client.get('/scenarios').json()['scenarios'][0]['id']
    loaded = client.post('/session/load', json={'scenario': first}).json()
    sid = loaded['session_id']
    client.post(f'/session/{sid}/step', json={'seconds': 1.0})
    full = client.get(f'/session/{sid}/state?profile=full').json()['state']
    bedside_fast = client.get(f'/session/{sid}/state?profile=bedside_fast').json()['state']
    for key in ['pH_a', 'PaO2', 'PaCO2', 'EtCO2', 'SaO2', 'HCO3_mmol_L',
                'base_excess_mmol_L', 'lactate', 'Hb', 'Na_mmol_L', 'K_mmol_L',
                'glucose_mmol_L']:
        assert key in full, key
    assert 'HCO3_mmol_L' not in bedside_fast

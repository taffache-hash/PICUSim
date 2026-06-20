from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.server import app


NEW_DRUG_ACTIONS = {
    'set_dopamine': 'dopamine_mcg_kg_min',
    'set_vasopressin': 'vasopressin_mU_kg_min',
    'set_milrinone': 'milrinone_mcg_kg_min',
    'set_ketamine': 'ketamine_mg_kg_h',
    'set_remifentanil': 'remifentanil_mcg_kg_min',
    'set_dexmedetomidine': 'dexmedetomidine_mcg_kg_h',
    'set_clonidine': 'clonidine_mcg_kg_h',
    'set_salbutamol': 'salbutamol_mcg_kg_min',
    'set_ipratropium': 'ipratropium_mcg_kg_h',
    'set_magnesium': 'magnesium_mg_kg_h',
    'set_nebulized_epinephrine': 'nebulized_epinephrine_mcg_kg_min',
    'set_ino_ppm': 'ino_ppm',
    'set_hydrocortisone': 'hydrocortisone_mg_kg_h',
    'set_dexamethasone': 'dexamethasone_mcg_kg_h',
    'set_insulin': 'insulin_UI_h',
    'set_furosemide': 'furosemide_mg_kg',
    'set_furosemide_infusion': 'furosemide_mg_kg_h',
    'set_vancomycin': 'vancomycin_mg_kg_h',
    'set_piperacillin': 'piperacillin_mg_kg_h',
}


def test_v303_api_accepts_extended_drug_controls_and_roundtrips_values():
    client = TestClient(app)
    r = client.post('/session/load', json={'scenario': 'healthy_child_20kg', 'dt': 0.5})
    assert r.status_code == 200, r.text
    sid = r.json()['session_id']

    for action, key in NEW_DRUG_ACTIONS.items():
        r = client.post(f'/session/{sid}/action', json={'action': action, 'payload': {'value': 1.23}})
        assert r.status_code == 200, f'{action}: {r.text}'
        state = r.json()['session']['state']
        assert state['controls'][key] == 1.23, f'{action} did not round-trip {key}'


def test_v303_controls_profile_contains_extended_drug_surface():
    client = TestClient(app)
    r = client.post('/session/load', json={'scenario': 'healthy_child_20kg', 'dt': 0.5})
    assert r.status_code == 200, r.text
    sid = r.json()['session_id']
    r = client.get(f'/session/{sid}/state?profile=controls')
    assert r.status_code == 200, r.text
    controls = r.json()['state']
    for key in NEW_DRUG_ACTIONS.values():
        assert key in controls


def test_v303_ui_exposes_extended_drug_inputs_and_sync_bindings():
    html = (ROOT / 'ui' / 'index.html').read_text(encoding="utf-8")
    js = (ROOT / 'ui' / 'app.js').read_text(encoding="utf-8")
    for action, key in NEW_DRUG_ACTIONS.items():
        assert f'data-drug="{action}"' in html
        assert f"{action}: '{key}'" in js

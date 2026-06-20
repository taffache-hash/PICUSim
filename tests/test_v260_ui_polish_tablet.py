from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from api.server import app


def test_v26_clean_layout_and_apparatus_panels_are_served():
    client = TestClient(app)
    r = client.get('/monitor')
    assert r.status_code == 200, r.text
    html = r.text
    assert 'Bedside monitor' in html
    assert 'control-dock' in html
    assert 'apparatusOverlay' in html
    assert 'data-open-panel="airwayPanel"' in html
    assert 'data-open-panel="drugPanel"' in html
    assert 'data-panel-tab="instructorPanel"' in html
    assert 'Learner view' in html
    assert 'Instructor view' in html


def test_v26_css_contains_responsive_tablet_layout_rules():
    css = (ROOT / 'ui' / 'styles.css').read_text(encoding="utf-8")
    assert '.apparatus-overlay' in css
    assert '.apparatus-window' in css
    assert '.control-dock' in css
    assert '@media (max-width: 1320px)' in css
    assert '@media (max-width: 860px)' in css
    assert 'body.learner-mode' in css


def test_v26_javascript_contains_modal_navigation_hooks():
    js = (ROOT / 'ui' / 'app.js').read_text(encoding="utf-8")
    assert 'function openApparatus' in js
    assert 'function setApparatusPanel' in js
    assert 'setupApparatusNavigation' in js
    assert 'data-open-panel' in js
    assert 'learner-mode' in js


def test_v26_monitor_assets_still_load_after_layout_refactor():
    client = TestClient(app)
    for path in ['/ui/styles.css', '/ui/app.js', '/ui/canvas_waveforms.js']:
        r = client.get(path)
        assert r.status_code == 200, path
        assert len(r.text) > 500

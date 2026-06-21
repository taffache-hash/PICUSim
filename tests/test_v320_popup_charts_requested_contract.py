from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v320_popup_chart_modal_exists_and_is_request_only():
    html = (ROOT / 'ui' / 'index.html').read_text(encoding="utf-8")
    for needle in [
        'id="extendedChartsBtn"',
        'id="popupChartOverlay"',
        'id="popupChartSelect"',
        'id="popupChartCanvas"',
        'Trend generati solo su richiesta',
    ]:
        assert needle in html


def test_v320_js_defines_popup_chart_sources_without_new_streams():
    js = (ROOT / 'ui' / 'app.js').read_text(encoding="utf-8")
    for needle in [
        'const extendedSnapshotBuffer = []',
        'const POPUP_CHART_DEFS = [',
        "{ id: 'CO2', label: 'PaCO₂ / EtCO₂'",
        "{ id: 'lactate', label: 'Lattato'",
        'function pushExtendedSnapshot',
        'function openPopupChart',
        'function drawPopupChart',
        'extendedChartsBtn',
    ]:
        assert needle in js
    assert '/ws/session/${sessionId}/monitor' not in js
    assert 'function openPopupChart' in js
    assert 'function shouldRefreshFullProfilePanels()' in js
    assert 'setInterval(() =>' in js  # panel-gated full-profile refresh added by Step 4.15, not popup-chart polling


def test_v320_popup_chart_css_present():
    css = (ROOT / 'ui' / 'styles.css').read_text(encoding="utf-8")
    for needle in ['.chart-overlay', '.chart-window', '.popup-chart-canvas', '.chart-toolbar']:
        assert needle in css

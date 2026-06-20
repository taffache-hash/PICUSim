from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v318_primary_vital_cards_have_sparkline_canvases():
    html = (ROOT / 'ui' / 'index.html').read_text(encoding="utf-8")
    for canvas_id in ['trendHR', 'trendSpO2', 'trendMAP', 'trendCO2', 'trendPaw', 'trendFiO2']:
        assert f'id="{canvas_id}"' in html
    assert html.count('class="vital-trend"') >= 6
    assert 'PaCO2 and EtCO2 trend' in html


def test_v318_app_js_keeps_bounded_bedside_trend_buffer_and_draws_sparklines():
    js = (ROOT / 'ui' / 'app.js').read_text(encoding="utf-8")
    for needle in [
        'const TREND_WINDOW_S = 600',
        'const TREND_MAX_SAMPLES = 2400',
        'const bedsideTrendBuffer = []',
        'function pushBedsideTrend',
        'function renderVitalSparklines',
        'function drawSparkline',
        "{ canvasId: 'trendCO2', primary: 'PaCO2', secondary: 'EtCO2' }",
        'pushBedsideTrend(st, envelope);',
        'renderVitalSparklines();',
    ]:
        assert needle in js


def test_v318_sparkline_css_is_present_and_responsive():
    css = (ROOT / 'ui' / 'styles.css').read_text(encoding="utf-8")
    assert '.vital-trend' in css
    assert 'height: 26px' in css
    assert '.vital:hover .vital-trend' in css
    assert 'height: 22px' in css

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v321_js_tracks_pending_confirmed_control_state():
    js = (ROOT / 'ui' / 'app.js').read_text(encoding="utf-8")
    for needle in [
        'const controlPendingValues = new Map()',
        'function markControlPending',
        'function confirmControlIfMatched',
        'function markControlError',
        "setControlStatus(key, 'pending')",
        "setControlStatus(key, 'confirmed')",
        'confirmControlIfMatched(inputId, value);',
        'confirmControlIfMatched(controlKey, value);',
    ]:
        assert needle in js


def test_v321_css_defines_pending_confirmed_error_badges():
    css = (ROOT / 'ui' / 'styles.css').read_text(encoding="utf-8")
    for needle in [
        'label.control-pending',
        'label.control-confirmed',
        'label.control-error',
        "content: 'pending'",
        "content: 'confirmed'",
        "content: 'error'",
    ]:
        assert needle in css

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v301_live_controls_use_input_events_with_debounce():
    js = (ROOT / 'ui' / 'app.js').read_text(encoding="utf-8")
    assert 'LIVE_CONTROL_DEBOUNCE_MS' in js
    assert 'function scheduleLiveAction' in js
    assert 'function flushLiveAction' in js
    assert 'function bindLiveRange' in js
    assert "bindLiveRange('fio2Range'" in js
    assert "bindLiveRange('peepRange'" in js
    assert "bindLiveRange('rrRange'" in js


def test_v301_drug_inputs_are_live_and_do_not_depend_only_on_change():
    js = (ROOT / 'ui' / 'app.js').read_text(encoding="utf-8")
    assert 'function bindLiveNumericInput' in js
    assert 'input.oninput = () => scheduleLiveAction' in js
    assert 'input.onchange = () => flushLiveAction' in js
    assert 'inp.onchange = () => sendAction(inp.dataset.drug' not in js


def test_v301_silent_live_updates_avoid_event_log_spam():
    js = (ROOT / 'ui' / 'app.js').read_text(encoding="utf-8")
    assert 'async function sendAction(action, payload, options={})' in js
    assert 'if (!options.silent) logEvent' in js
    assert 'silent: true' in js

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v346_monitor_quick_buttons_reflect_open_panel_state():
    js = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "ui" / "styles.css").read_text(encoding="utf-8")

    assert "function quickMonitorButtonTarget" in js
    assert "btn.id === 'quickEmogasBtn'" in js
    assert "btn.id === 'quickBolusBtn'" in js
    assert "btn.id === 'quickExtendedMonitorBtn'" in js
    assert "target.panel === panelId" in js
    assert "btn.classList.toggle('quick-active', active)" in js
    assert "btn.setAttribute('aria-pressed', active ? 'true' : 'false')" in js
    assert "updateDockButtonStates(null);" in js

    assert ".monitor-header-actions .quick-active" in css
    assert 'content: attr(data-state-label)' in css

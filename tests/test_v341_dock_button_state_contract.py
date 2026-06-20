from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v341_dock_cards_show_active_panel_state():
    js = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "ui" / "styles.css").read_text(encoding="utf-8")

    assert "function updateDockButtonStates" in js
    assert "btn.classList.toggle('dock-active', active)" in js
    assert "aria-pressed" in js
    assert "updateDockButtonStates(panelId);" in js
    assert "updateDockButtonStates(null);" in js

    assert ".dock-card.dock-active" in css
    assert "rgba(77,255,136" in css

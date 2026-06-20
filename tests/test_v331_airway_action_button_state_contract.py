from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v331_airway_action_button_state_contract_present():
    html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "ui" / "styles.css").read_text(encoding="utf-8")

    assert 'data-action="airway_event"' in html
    assert 'data-event="perform_intubation"' in html
    assert 'data-event="start_bag_mask_ventilation"' in html
    assert 'data-event="accidental_extubation"' in html
    assert 'function airwayActiveEvents' in js
    assert 'function updateAirwayActionButtons' in js
    assert 'updateAirwayActionButtons(st);' in js
    assert "btn.classList.add('pending')" in js
    assert "btn.setAttribute('aria-pressed', 'true')" in js
    assert "btn.setAttribute('aria-pressed', isActive ? 'true' : 'false')" in js
    assert "failed_intubation_count" in js
    assert "bag_mask_ventilation_active" in js
    assert "intubated" in js
    assert "extubation_time_s" in js
    assert 'button[data-action="airway_event"].action-active' in css
    assert 'button[data-action="airway_event"].pending' in css
    assert 'content: attr(data-state)' in css


def test_v331_bolus_panel_still_renders_when_drug_panel_opens():
    js = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
    assert "if (panelId === 'drugPanel')" in js
    assert 'renderBolusControls();' in js
    assert "$('clearBolusStatusBtn').onclick = clearBolusStatus" in js


from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v319_extended_monitor_v2_has_eleven_collapsible_groups():
    js = (ROOT / 'ui' / 'app.js').read_text(encoding="utf-8")
    for label in [
        'Emodinamica / perfusione',
        'Respiratorio',
        'Metabolico / labs',
        'Neurologico / sedazione',
        'Renale / fluidi',
        'Coagulazione / ematologia',
        'Epatico',
        'Infezione / sepsi',
        'Ventilazione avanzata',
        'Farmaci / concentrazioni',
        'Nutrizione / catabolismo',
    ]:
        assert label in js
    assert "<details class=\"extended-card\"" in js
    assert "<summary><h3>${group.title}</h3>" in js


def test_v319_extended_monitor_is_snapshot_only_no_polling_loop():
    js = (ROOT / 'ui' / 'app.js').read_text(encoding="utf-8")
    assert "const EXTENDED_MONITOR_REFRESH_MODE = 'snapshot-only'" in js
    assert 'function startExtendedMonitorSnapshot' in js
    assert 'setInterval(() =>' not in js
    assert 'EXTENDED_MONITOR_POLL_MS' not in js
    assert "'bedside stream'" not in js


def test_v319_extended_monitor_snapshot_wording_and_button():
    html = (ROOT / 'ui' / 'index.html').read_text(encoding="utf-8")
    assert 'Aggiorna snapshot' in html
    assert 'Snapshot su richiesta' in html
    assert 'senza polling continuo' in html


def test_v319_extended_monitor_css_supports_collapsible_cards():
    css = (ROOT / 'ui' / 'styles.css').read_text(encoding="utf-8")
    for needle in [
        '.extended-card summary',
        '.extended-card[open] summary::before',
        'padding: 0 12px 12px',
    ]:
        assert needle in css

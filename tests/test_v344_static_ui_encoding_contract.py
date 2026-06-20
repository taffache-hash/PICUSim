from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v344_static_monitor_labels_are_not_mojibake():
    html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "ui" / "styles.css").read_text(encoding="utf-8")

    for bad in ["Ã—", "SpOâ", "PaCOâ", "EtCOâ", "FiOâ", "cmHâ", "â–¸"]:
        assert bad not in html
        assert bad not in css

    for good in ["speed ×", "SpO₂", "PaCO₂", "EtCO₂", "FiO₂", "cmH₂O"]:
        assert good in html
    assert "content: '▸'" in css

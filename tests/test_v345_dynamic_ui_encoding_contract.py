from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v345_dynamic_ui_labels_are_not_mojibake():
    app_js = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")

    for bad in [
        "\u00c3",
        "\u00c2",
        "SpO\u00e2",
        "PaCO\u00e2",
        "EtCO\u00e2",
        "FiO\u00e2",
        "cmH\u00e2",
        "\u00c2\u00b7",
        "\u00c3\u2014",
        "\u00e2\u20ac\u201c",
    ]:
        assert bad not in app_js

    for good in [
        "SpO\u2082",
        "PaCO\u2082",
        "EtCO\u2082",
        "FiO\u2082",
        "ScvO\u2082",
        "DO\u2082",
        "VO\u2082",
        "cmH\u2082O",
        "HCO\u2083\u207b",
        "K\u207a",
        "Na\u207a",
        "\u00b0C",
        "\u00b5g/mL",
        "\u00d710\u2079/L",
        "speed \u00d7",
    ]:
        assert good in app_js


def test_v345_roadmap_is_not_mojibake():
    roadmap = (ROOT / "docs" / "PCCSIM_V3_1_PHARMACOLOGY_AND_UI_ROADMAP.md").read_text(
        encoding="utf-8"
    )

    for bad in ["\u00c3", "\u00c2", "\u00e2\u201a", "\u00e2\u20ac"]:
        assert bad not in roadmap

    assert "Step 4.26 completed \u2014 Dynamic UI and roadmap encoding fix" in roadmap
    assert "SpO\u2082, PaCO\u2082, EtCO\u2082, FiO\u2082, cmH\u2082O and speed \u00d7" in roadmap

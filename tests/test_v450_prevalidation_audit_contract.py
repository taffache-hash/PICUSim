from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def test_v450_ui_has_no_missing_static_id_targets():
    html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
    ids = set(re.findall(r'id="([^"]+)"', html))
    refs = set(re.findall(r"\$\('([^']+)'\)", js))
    refs |= set(re.findall(r"getElementById\([\"']([^\"']+)[\"']\)", js))
    assert refs - ids == set()


def test_v450_core_scenario_buttons_are_present():
    html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
    required_labels = [
        "Start", "Pause", "Step 5 s", "Reset",
        "Failed attempt", "Bag-mask", "Intubate",
        "Start compressions", "Stop compressions",
        "Defib asincrona", "Cardioversione sincronizzata",
        "Adrenalina bolo", "Amiodarone bolo", "Atropina bolo",
        "Generate debrief", "Validate", "Save to scenarios",
    ]
    for label in required_labels:
        assert label in html


def test_v450_hyperkalemia_v2_scenario_builds_timeline_with_calcium_marker():
    from core.scenario import ScenarioLoader

    loader = ScenarioLoader.from_yaml(ROOT / "scenarios" / "epals_v2_hyperkalemia_aki_instability.yaml")
    bus = loader.build_bus()
    perturbations = loader.build_perturbations()
    assert hasattr(bus.state, "calcium_given")
    assert any(p.key == "calcium_given" for p in perturbations)

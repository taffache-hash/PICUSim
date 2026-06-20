import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.scenario import ScenarioLoader
from core.scenario_timing import make_stable_start_config
from core.failure_to_rescue import (
    FAILURE_TO_RESCUE_REVISION,
    failure_to_rescue_metadata,
    with_failure_to_rescue,
    build_failure_escalation_perturbations,
)


def _stable_sepsis():
    original = ScenarioLoader.from_yaml(ROOT / "scenarios" / "epals_v2_septic_shock_warm.yaml").config
    healthy = ScenarioLoader.from_yaml(ROOT / "scenarios" / "healthy_child_20kg.yaml").config
    return make_stable_start_config(original, healthy, trigger_at_s=60)


def test_v446_failure_clock_exposes_golden_window_and_absolute_times():
    cfg = with_failure_to_rescue(_stable_sepsis())
    meta = failure_to_rescue_metadata(cfg)
    assert meta["revision"] == FAILURE_TO_RESCUE_REVISION
    assert meta["phenotype"] == "septic_shock"
    assert meta["trigger_s"] == 60
    assert meta["critical_window_s"] == 480
    assert meta["critical_window_end_s"] == 540
    assert meta["critical_window_end_mmss"] == "09:00"
    assert meta["point_of_no_return_abs_s"] > meta["reversibility_threshold_abs_s"] > meta["critical_window_end_s"]


def test_v446_failure_escalation_perturbations_start_after_window_closes():
    cfg = with_failure_to_rescue(_stable_sepsis())
    items = build_failure_escalation_perturbations(cfg)
    assert len(items) >= 5
    assert min(float(i["t"]) for i in items) == failure_to_rescue_metadata(cfg)["critical_window_end_s"]
    assert any("point_of_no_return" in i["label"] for i in items)
    assert any(i["action"] == "shock_vasoplegia_index" for i in items)


def test_v446_loader_adds_failure_to_rescue_perturbations_when_enabled():
    cfg = with_failure_to_rescue(_stable_sepsis())
    loader = ScenarioLoader.from_dict(cfg)
    perturbations = loader.build_perturbations()
    labels = [p.label for p in perturbations]
    assert loader.failure_to_rescue_info["phenotype"] == "septic_shock"
    assert any("failure_to_rescue" in label for label in labels)
    assert min(p.t for p in perturbations if "failure_to_rescue" in p.label) >= loader.failure_to_rescue_info["critical_window_end_s"]

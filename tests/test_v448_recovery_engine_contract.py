import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.bus import PhysiologicalBus
from core.engine import Perturbation
from core.scenario import ScenarioLoader
from core.scenario_timing import make_stable_start_config
from core.recovery_engine import (
    RECOVERY_ENGINE_REVISION,
    recovery_metadata,
    with_recovery_engine,
    detect_first_corrective_action_time,
    build_recovery_perturbations,
)


def _treated_sepsis():
    original = ScenarioLoader.from_yaml(ROOT / "scenarios" / "epals_v2_septic_shock_warm.yaml").config
    healthy = ScenarioLoader.from_yaml(ROOT / "scenarios" / "healthy_child_20kg.yaml").config
    cfg = make_stable_start_config(original, healthy, trigger_at_s=60)
    cfg.setdefault("interventions", [])
    cfg["interventions"].append({"t": 150, "action": "set_norad", "value": 0.08, "label": "correct norepi rescue"})
    return with_recovery_engine(cfg, phenotype="septic_shock")


def test_v448_recovery_metadata_exposes_treatment_response_windows():
    cfg = _treated_sepsis()
    meta = recovery_metadata(cfg)
    assert meta["revision"] == RECOVERY_ENGINE_REVISION
    assert meta["phenotype"] == "septic_shock"
    assert meta["trigger_s"] == 60
    assert meta["first_response_abs_s"] == 150
    assert meta["partial_response_mmss"] == "05:00"
    assert meta["near_baseline_abs_s"] > meta["partial_response_abs_s"]


def test_v448_detects_first_corrective_action_after_trigger():
    cfg = _treated_sepsis()
    assert detect_first_corrective_action_time(cfg) == 135


def test_v448_builds_recovery_only_after_corrective_action():
    cfg = _treated_sepsis()
    items = build_recovery_perturbations(cfg)
    assert items
    assert min(float(i["t"]) for i in items) >= 225  # 135 + septic first-response delay 90
    assert any(i["action"] == "shock_vasoplegia_index" for i in items)
    assert any(i["action"] == "recovery_engine_active" for i in items)


def test_v448_loader_adds_recovery_perturbations_when_enabled():
    loader = ScenarioLoader.from_dict(_treated_sepsis())
    perturbations = loader.build_perturbations()
    labels = [p.label for p in perturbations]
    assert loader.recovery_info["first_corrective_action_time_s"] == 135
    assert any("recovery_engine" in label for label in labels)


def test_v448_multiplier_perturbation_updates_audit_and_base_variable():
    bus = PhysiologicalBus()
    bus.set("lactate", 4.0)
    p = Perturbation(t=0, key="lactate_multiplier", value=0.75, label="test recovery lactate")
    p.apply(bus)
    assert bus.get("lactate_multiplier") == 0.75
    assert bus.get("lactate") == 3.0

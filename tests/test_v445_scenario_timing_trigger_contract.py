import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.scenario import ScenarioLoader
from core.scenario_timing import (
    SCENARIO_TIMING_REVISION,
    format_mmss,
    scenario_timing_metadata,
    shift_critical_timelines,
    make_stable_start_config,
)


def test_v445_timing_metadata_exposes_real_duration_and_trigger():
    cfg = {"name": "x", "simulation_time_s": 420, "scenario_timing": {"critical_event_trigger_at_s": 75}}
    meta = scenario_timing_metadata(cfg)
    assert meta["revision"] == SCENARIO_TIMING_REVISION
    assert meta["real_duration_s"] == 420
    assert meta["real_duration_mmss"] == "07:00"
    assert meta["critical_event_trigger_mmss"] == "01:15"
    assert format_mmss(61) == "01:01"


def test_v445_critical_timelines_are_shifted_after_manual_trigger():
    cfg = {
        "name": "event_case",
        "simulation_time_s": 300,
        "patient": {"age_y": 5, "weight_kg": 20},
        "perturbations": [{"t": 0, "action": "set_FiO2", "value": 0.21}],
        "events": [{"t": 30, "name": "pneumothorax_tension", "severity": "moderate"}],
    }
    shifted = shift_critical_timelines(cfg, 60)
    assert shifted["perturbations"][0]["t"] == 60
    assert shifted["events"][0]["t"] == 90
    assert shifted["scenario_timing"]["critical_event_trigger_at_s"] == 60


def test_v445_stable_start_wrapper_starts_from_healthy_baseline_then_triggers_case():
    original = ScenarioLoader.from_yaml(ROOT / "scenarios" / "epals_v2_septic_shock_warm.yaml").config
    healthy = ScenarioLoader.from_yaml(ROOT / "scenarios" / "healthy_child_20kg.yaml").config
    wrapped = make_stable_start_config(original, healthy, trigger_at_s=60)
    loader = ScenarioLoader.from_dict(wrapped)
    bus = loader.build_bus()
    perturbations = loader.build_perturbations()
    assert wrapped["scenario_timing"]["stable_start_applied"] is True
    assert loader.nominal_real_duration == float(original["simulation_time_s"])
    assert loader.critical_event_trigger_time == 60
    assert float(bus.get("MAP")) >= 55.0
    assert float(bus.get("SaO2")) >= 0.95
    assert min(p.t for p in perturbations) >= 60.0
    assert "critical_event_baseline" in wrapped

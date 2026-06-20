import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.scenario import ScenarioLoader
from core.scenario_engine_v2 import ScenarioEngineV2Catalog, SCENARIO_ENGINE_V2_REVISION


def test_v444_manifest_loads_eight_valid_epals_v2_scenarios():
    catalog = ScenarioEngineV2Catalog.from_yaml(ROOT / "data" / "scenario_engine_v2_step4.44.yaml", root=ROOT)
    summary = catalog.summary()
    assert summary["scenario_engine_revision"] == SCENARIO_ENGINE_V2_REVISION
    assert summary["scenario_count"] == 8
    assert summary["valid_count"] == 8
    assert summary["invalid_count"] == 0
    assert "epals_v2_septic_shock_warm" in summary["scenario_ids"]
    assert "epals_v2_bronchiolitis_respiratory_failure" in summary["scenario_ids"]


def test_v444_each_catalog_scenario_builds_bus_and_perturbation_timeline():
    catalog = ScenarioEngineV2Catalog.from_yaml(ROOT / "data" / "scenario_engine_v2_step4.44.yaml", root=ROOT)
    for path in catalog.scenario_paths():
        loader = ScenarioLoader.from_yaml(path)
        bus = loader.build_bus()
        perturbations = loader.build_perturbations()
        assert loader.scenario_name.startswith("epals_v2_")
        assert float(bus.get("weight_kg")) > 0.0
        assert loader.simulation_time > 0.0
        assert len(loader.config.get("outputs", [])) >= 4
        assert len(perturbations) >= 3


def test_v444_shock_and_neuro_hooks_are_applied_by_loader():
    septic = ScenarioLoader.from_yaml(ROOT / "scenarios" / "epals_v2_septic_shock_warm.yaml").build_bus()
    tbi = ScenarioLoader.from_yaml(ROOT / "scenarios" / "epals_v2_tbi_icp_crisis.yaml").build_bus()
    assert septic.get("shock_type") == "distributive"
    assert float(septic.get("shock_severity")) >= 0.7
    assert float(septic.get("infection_load")) >= 0.8
    assert float(tbi.get("ICP_mmHg")) >= 30.0
    assert float(tbi.get("CPP_mmHg")) <= 35.0

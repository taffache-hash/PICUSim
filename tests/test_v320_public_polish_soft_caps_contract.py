"""v3.2 public-polish contracts for softened public-display physiological caps.

These tests are intentionally qualitative. They do not claim clinical
validation; they prevent public-demo scenarios from visibly converging to
identical numerical ceilings such as PaCO2=105 or HR=180/210/220.
"""

import contextlib
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core import ScenarioLoader
from run_simulation import build_twin


def _run_scenario(name: str, dt: float = 5.0):
    loader = ScenarioLoader.from_yaml(str(ROOT / "scenarios" / f"{name}.yaml"))
    bus = loader.build_bus()
    with contextlib.redirect_stdout(io.StringIO()):
        engine = build_twin(bus, loader.config, dt=dt)
        engine.add_perturbations(loader.build_perturbations())
        df = engine.run(T=loader.simulation_time)
    return df


def test_obstructive_scenarios_no_longer_print_old_paco2_wall():
    for scenario in ["infant_bronchiolitis", "near_fatal_status_asthmaticus"]:
        df = _run_scenario(scenario)
        assert float(df["PaCO2"].max()) < 104.0
        assert not (df["PaCO2"].round(2) == 105.00).any()


def test_septic_scenarios_keep_hypercapnia_without_old_wall():
    for scenario in ["septic_shock", "septic_shock_refractory"]:
        df = _run_scenario(scenario)
        assert float(df["PaCO2"].max()) < 104.0
        assert float(df["PaCO2"].max()) > 70.0
        assert not (df["PaCO2"].round(2) == 105.00).any()


def test_public_golden_scenarios_do_not_print_exact_age_group_hr_ceilings():
    old_ceilings = {180.0, 210.0, 220.0}
    for scenario in [
        "septic_shock",
        "septic_shock_refractory",
        "infant_bronchiolitis",
        "neonatal_rds_3kg",
        "counterfactual_excessive_PEEP_ARDS",
    ]:
        df = _run_scenario(scenario)
        final_hr = round(float(df.iloc[-1]["HR"]), 1)
        max_hr = round(float(df["HR"].max()), 1)
        assert final_hr not in old_ceilings
        assert max_hr not in old_ceilings


def test_healthy_child_regression_after_soft_caps():
    df = _run_scenario("healthy_child_20kg")
    final = df.iloc[-1]
    assert float(final["SaO2"]) >= 0.935
    assert 35.0 <= float(final["PaCO2"]) <= 50.0
    assert float(final["pH_a"]) >= 7.30

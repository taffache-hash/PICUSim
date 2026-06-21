
"""v3.2 public-polish clinical-sanity contracts.

These tests guard the release-facing scenarios that a reviewer is most
likely to open first. They are qualitative educational contracts, not
clinical validation claims.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import ScenarioLoader
from run_simulation import build_twin


def _run_scenario(name: str):
    loader = ScenarioLoader.from_yaml(str(Path("scenarios") / f"{name}.yaml"))
    bus = loader.build_bus()
    engine = build_twin(bus, loader.config, dt=5.0)
    engine.verbose = False
    engine.snapshot_every = 1
    engine.add_perturbations(loader.build_perturbations())
    return engine.run(T=loader.simulation_time)


def test_v320_healthy_child_room_air_wean_remains_clinically_sane():
    df = _run_scenario("healthy_child_20kg")
    final = df.iloc[-1]
    assert final.SaO2 >= 0.935
    assert 35.0 <= final.PaCO2 <= 50.0
    assert final.pH_a >= 7.30
    assert final.shock_type == "none"
    assert final.shock_stage == "none"


def test_v320_pneumothorax_preserves_recovery_pattern_and_obstructive_label():
    df = _run_scenario("epals_tension_pneumothorax")
    final = df.iloc[-1]
    assert float(df.SaO2.min()) < 0.94
    assert final.SaO2 > float(df.SaO2.min()) + 0.04
    assert final.CO > float(df.CO.min()) + 0.5
    assert final.shock_type == "obstructive"
    assert final.shock_stage in {"compensated", "decompensated", "critical"}


def test_v320_excessive_peep_reduces_cardiac_output_and_flags_obstructive_shock():
    df = _run_scenario("counterfactual_excessive_PEEP_ARDS")
    assert float(df.CO.min()) < float(df.CO.iloc[0])
    assert float(df.MAP.min()) <= 35.0
    final = df.iloc[-1]
    assert final.shock_type == "obstructive"
    assert final.shock_stage in {"decompensated", "critical"}


def test_v320_septic_shock_has_distributive_label_and_metabolic_component():
    df = _run_scenario("septic_shock")
    final = df.iloc[-1]
    assert final.shock_type == "distributive"
    assert final.shock_stage in {"decompensated", "critical"}
    assert final.lactate >= 3.0
    assert final.HCO3_mmol_L < 23.5
    assert final.base_excess_mmol_L < -4.0

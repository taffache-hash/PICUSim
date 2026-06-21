"""v3.2 public RC2 external-review regression contracts.

These tests lock the fixes prompted by the RC1 independent review: DKA
oxygenation/Fick stability, a visible pneumothorax deterioration-recovery
teaching pattern, integrated hyperkalemia initialization, and short-horizon
norepinephrine visibility in septic shock.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import ScenarioLoader
from run_simulation import build_twin


def _run_scenario(name: str, dt: float = 5.0):
    loader = ScenarioLoader.from_yaml(str(Path("scenarios") / f"{name}.yaml"))
    bus = loader.build_bus()
    engine = build_twin(bus, loader.config, dt=dt)
    engine.verbose = False
    engine.snapshot_every = 1
    engine.add_perturbations(loader.build_perturbations())
    return engine.run(T=loader.simulation_time)


def test_v320_rc2_dka_does_not_enter_fick_oxygen_death_spiral():
    df = _run_scenario("epals_v2_dka_dehydration_shock")
    assert float(df.SaO2.min()) >= 0.90
    assert float(df.PaCO2.max()) <= 45.0
    assert 7.00 <= float(df.pH_a.iloc[-1]) <= 7.20
    assert float(df.K_mmol_L.iloc[0]) >= 5.5
    # Ignore the t=0 initialization row; after the first physiology step, CO
    # should no longer remain at the old hyperdynamic ceiling.
    after_start = df.loc[df.index >= 20.0]
    assert float(after_start.CO.max()) <= 6.6


def test_v320_rc2_tension_pneumothorax_has_deterioration_then_decompression_recovery():
    df = _run_scenario("epals_tension_pneumothorax")
    pre = df.loc[df.index < 170.0]
    post = df.loc[df.index >= 180.0]
    assert float(pre.SaO2.min()) <= 0.88
    assert float(pre.MAP.min()) <= 35.0
    assert float(pre.CO.min()) < float(df.CO.iloc[0]) - 0.8
    assert float(post.SaO2.max()) >= float(pre.SaO2.min()) + 0.10
    assert float(post.MAP.max()) >= float(pre.MAP.min()) + 8.0
    assert float(post.airway_shunt_add.iloc[-1]) < float(pre.airway_shunt_add.max())


def test_v320_rc2_integrated_hyperkalemia_starts_pathologic_not_default():
    df = _run_scenario("epals_hyperkalemia_aki")
    assert float(df.K_mmol_L.iloc[0]) >= 6.5
    assert float(df.K_mmol_L.iloc[-1]) <= float(df.K_mmol_L.iloc[0]) - 1.0


def test_v320_rc2_norepinephrine_has_visible_short_horizon_map_effect():
    df = _run_scenario("epals_acidosis_septic_shock")
    pre_ne = float(df.loc[(df.index >= 80.0) & (df.index <= 95.0), "MAP"].mean())
    post_ne = float(df.loc[(df.index >= 120.0) & (df.index <= 180.0), "MAP"].mean())
    assert float(df.loc[df.index >= 120.0, "vasoactive_effective_norad"].max()) >= 0.10
    assert post_ne >= pre_ne + 8.0

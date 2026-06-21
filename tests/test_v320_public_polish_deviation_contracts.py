"""v3.2 public-polish deviation contracts.

These tests cover the additional review findings from the public-release
candidate inspection: electrolyte baseline preservation, short-horizon
norepinephrine visibility in septic shock, direct antimicrobial-effect
perturbations, and stable numeric Paw display aliases.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import PhysiologicalBus, ScenarioLoader
from modules.acidbase import AcidBaseElectrolyteModule
from run_simulation import build_twin


def _run_scenario(name: str):
    loader = ScenarioLoader.from_yaml(str(Path("scenarios") / f"{name}.yaml"))
    bus = loader.build_bus()
    engine = build_twin(bus, loader.config, dt=5.0)
    engine.verbose = False
    engine.snapshot_every = 1
    engine.add_perturbations(loader.build_perturbations())
    return engine.run(T=loader.simulation_time)


def test_v320_acidbase_initialize_preserves_param_baselines_when_bus_has_defaults():
    bus = PhysiologicalBus()
    module = AcidBaseElectrolyteModule({
        "Na_baseline": 132.0,
        "K_baseline": 6.8,
        "Cl_baseline": 101.0,
        "HCO3_baseline": 17.0,
    })
    module.initialize(bus)
    assert bus.get("Na_mmol_L") == 132.0
    assert bus.get("K_mmol_L") == 6.8
    assert bus.get("Cl_mmol_L") == 101.0
    assert bus.get("HCO3_mmol_L") == 17.0


def test_v320_hyperkalemia_scenario_starts_hyperkalemic_and_then_improves():
    df = _run_scenario("epals_hyperkalemia_aki")
    assert float(df.K_mmol_L.iloc[0]) >= 6.5
    assert float(df.K_mmol_L.iloc[-1]) < float(df.K_mmol_L.iloc[0]) - 0.8


def test_v320_norepinephrine_visibly_raises_map_in_short_septic_shock_scenario():
    df = _run_scenario("epals_acidosis_septic_shock")
    pre_ne = float(df.loc[(df.index >= 80) & (df.index <= 90), "MAP"].mean())
    post_ne = float(df.loc[(df.index >= 120) & (df.index <= 180), "MAP"].mean())
    assert post_ne >= pre_ne + 10.0
    assert float(df.loc[(df.index >= 120) & (df.index <= 180), "vasoactive_effective_norad"].max()) > 0.10


def test_v320_direct_antibiotic_effect_perturbation_is_not_overwritten():
    df = _run_scenario("epals_acidosis_septic_shock")
    after_effect = df.loc[df.index >= 220]
    assert float(after_effect.antibiotic_effect.max()) >= 0.30


def test_v320_numeric_paw_display_uses_stable_mean_alias_not_instantaneous_waveform_only():
    df = _run_scenario("epals_acidosis_septic_shock")
    assert "Paw_mean" in df.columns
    assert "Paw_display" in df.columns
    # The instantaneous Paw may sample inspiratory/expiratory phases; the display
    # alias should expose a stable cycle-level value for numeric monitor panels.
    assert float(df.Paw_display.iloc[-1]) >= float(df.PEEP.iloc[-1])
    assert float(df.Paw_display.iloc[-1]) != float(df.Paw.iloc[-1])

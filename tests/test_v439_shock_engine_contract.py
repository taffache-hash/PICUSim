import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.bus import PhysiologicalBus
from modules.cardiovascular.shock import ShockModule


def _bus(**updates):
    bus = PhysiologicalBus()
    bus.update(updates)
    return bus


def test_distributive_shock_writes_coupled_modifiers():
    bus = _bus(
        shock_type="distributive",
        shock_severity=0.70,
        MAP=52.0,
        CVP=6.0,
        lactate=3.5,
        infection_load=0.8,
        vasoplegia_index=0.75,
        myocardial_depression_index=0.25,
    )
    mod = ShockModule()
    mod.initialize(bus)
    mod.step(bus, 1.0)

    assert bus.get("shock_engine_revision") == 439
    assert bus.get("shock_type") == "distributive"
    assert bus.get("shock_stage") in {"compensated", "decompensated", "critical"}
    assert bus.get("shock_SVR_mod") < 1.0
    assert bus.get("shock_HR_add") > 0.0
    assert bus.get("shock_lactate_prod_mod") > 1.0
    assert bus.get("shock_lactate_clearance_mod") <= 1.0
    assert math.isclose(bus.get("shock_perfusion_pressure_mmHg"), bus.get("MAP") - bus.get("CVP"), rel_tol=1e-6)


def test_hypovolemic_shock_preserves_compensatory_svr_and_lowers_preload():
    bus = _bus(
        shock_type="hypovolemic",
        shock_severity=0.65,
        MAP=58.0,
        CVP=3.0,
        lactate=2.4,
        fluid_balance=-550.0,
        blood_volume_mL=1600.0,
    )
    mod = ShockModule()
    mod.initialize(bus)
    mod.step(bus, 1.0)

    assert bus.get("shock_hypovolemia_index") >= 0.65
    assert bus.get("shock_preload_mod") < 1.0
    assert bus.get("shock_SVR_mod") > 1.0
    assert bus.get("shock_contractility_mod") <= 1.0


def test_no_shock_returns_neutral_modifiers():
    bus = _bus(shock_type="none", shock_severity=0.0, MAP=65.0, CVP=5.0)
    mod = ShockModule()
    mod.initialize(bus)
    mod.step(bus, 1.0)

    assert bus.get("shock_type") == "none"
    assert bus.get("shock_stage") == "none"
    assert bus.get("shock_SVR_mod") == 1.0
    assert bus.get("shock_preload_mod") == 1.0
    assert bus.get("shock_contractility_mod") == 1.0

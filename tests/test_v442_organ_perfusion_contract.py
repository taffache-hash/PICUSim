import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.bus import PhysiologicalBus
from modules.perfusion.organ_perfusion import OrganPerfusionModule


def _bus(**updates):
    bus = PhysiologicalBus()
    bus.update(updates)
    return bus


def test_low_map_shock_reduces_renal_hepatic_perfusion_and_urine():
    bus = _bus(
        age_y=6.0,
        weight_kg=20.0,
        MAP=42.0,
        CVP=8.0,
        CO=1.6,
        SaO2=0.92,
        PaO2=65.0,
        lactate=4.8,
        shock_severity=0.75,
        shock_low_output_index=0.55,
        shock_hypovolemia_index=0.40,
        shock_lactate_clearance_mod=0.65,
        microcirculatory_failure_index=0.45,
    )
    mod = OrganPerfusionModule()
    mod.initialize(bus)
    for _ in range(6):
        mod.step(bus, 60.0)

    assert bus.get("organ_perfusion_revision") == 442
    assert bus.get("organ_perfusion_pressure_mmHg") == bus.get("MAP") - bus.get("CVP")
    assert bus.get("pediatric_MAP_low_threshold_mmHg") == 55.0
    assert bus.get("renal_perfusion_index") < 0.65
    assert bus.get("hepatic_perfusion_index") < 0.75
    assert bus.get("urine_output_mL_kg_h") < 1.0
    assert bus.get("organ_lactate_clearance_mod") < 0.85
    assert bus.get("renal_warning") != "none"


def test_preserved_perfusion_keeps_outputs_near_normal():
    bus = _bus(age_y=10.0, weight_kg=30.0, MAP=72.0, CVP=5.0, CO=4.2, SaO2=0.98, PaO2=95.0)
    mod = OrganPerfusionModule()
    mod.initialize(bus)
    mod.step(bus, 60.0)

    assert bus.get("renal_perfusion_index") > 0.85
    assert bus.get("hepatic_perfusion_index") > 0.85
    assert bus.get("urine_output_mL_kg_h") >= 0.9
    assert bus.get("organ_lactate_clearance_mod") >= 0.9
    assert bus.get("renal_warning") == "none"
    assert bus.get("hepatic_warning") == "none"


def test_infant_has_lower_map_threshold_than_school_age_child():
    infant = _bus(age_y=0.5, weight_kg=7.0, MAP=48.0, CVP=5.0, CO=1.0)
    child = _bus(age_y=6.0, weight_kg=20.0, MAP=48.0, CVP=5.0, CO=2.5)
    mod_i = OrganPerfusionModule(); mod_i.initialize(infant)
    mod_c = OrganPerfusionModule(); mod_c.initialize(child)

    assert infant.get("pediatric_MAP_low_threshold_mmHg") == 45.0
    assert child.get("pediatric_MAP_low_threshold_mmHg") == 55.0
    assert infant.get("renal_perfusion_index") > child.get("renal_perfusion_index")

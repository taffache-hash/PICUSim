from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.bus import PhysiologicalBus
from modules.airway.obstruction import AirwayObstructionModule
from modules.pharmacology.ino import INOModule
from modules.cardiovascular.circulation import CirculationModule


def _obstructed_bus() -> PhysiologicalBus:
    bus = PhysiologicalBus()
    bus.set("bronchospasm_index", 0.75)
    bus.set("mucus_load", 0.25)
    bus.set("small_airway_obstruction", 0.45)
    bus.set("R_rs", 10.0)
    bus.set("C_rs", 22.0)
    bus.set("RR", 36.0)
    bus.set("RR_total", 36.0)
    bus.set("IE_ratio", 0.38)
    bus.set("PEEP", 5.0)
    bus.set("Paw_current", 18.0)
    bus.set("drug_MAP_mod", 1.0)
    bus.set("drug_SVR_mod", 1.0)
    return bus


def _run_airway(**drug_values):
    bus = _obstructed_bus()
    for key, value in drug_values.items():
        bus.set(key, value)
    mod = AirwayObstructionModule({"tau_obstruction_s": 1.0})
    mod.initialize(bus)
    mod.step(bus, 1.0)
    return bus


def test_v311_bronchodilators_reduce_obstruction_resistance_and_autopeep_monotonically():
    base = _run_airway()
    low = _run_airway(salbutamol_mcg_kg_min=0.04)
    high = _run_airway(salbutamol_mcg_kg_min=0.20)

    assert base.get("bronchodilator_effect") < low.get("bronchodilator_effect") < high.get("bronchodilator_effect")
    assert base.get("airway_obstruction_index") > low.get("airway_obstruction_index") > high.get("airway_obstruction_index")
    assert base.get("airway_resistance_mod") > low.get("airway_resistance_mod") > high.get("airway_resistance_mod")
    assert base.get("air_trapping_index") >= low.get("air_trapping_index") >= high.get("air_trapping_index")
    assert base.get("auto_PEEP_obstructive") >= low.get("auto_PEEP_obstructive") >= high.get("auto_PEEP_obstructive")


def test_v311_respiratory_drug_components_are_separate_and_directional():
    sal = _run_airway(salbutamol_mcg_kg_min=0.20)
    ipr = _run_airway(ipratropium_mcg_kg_h=10.0)
    mag = _run_airway(magnesium_mg_kg_h=50.0)
    epi = _run_airway(nebulized_epinephrine_mcg_kg_min=0.10)

    assert sal.get("salbutamol_bronchodilation_signal") > 0.40
    assert ipr.get("ipratropium_bronchodilation_signal") > 0.15
    assert mag.get("magnesium_bronchodilation_signal") > 0.15
    assert epi.get("nebulized_epinephrine_bronchodilation_signal") > 0.20
    assert epi.get("nebulized_epinephrine_upper_airway_relief_signal") > 0.45

    # Salbutamol/nebulized epinephrine can create a small HR signal; ipratropium
    # and magnesium should not do that in this model contract.
    assert sal.get("bronchodilator_HR_mod") > 1.0
    assert epi.get("bronchodilator_HR_mod") > 1.0
    assert ipr.get("bronchodilator_HR_mod") == 1.0
    assert mag.get("bronchodilator_HR_mod") == 1.0


def test_v311_bronchodilators_do_not_directly_write_map_or_svr_drug_modifiers():
    sal = _run_airway(salbutamol_mcg_kg_min=0.25)
    epi = _run_airway(nebulized_epinephrine_mcg_kg_min=0.12)

    assert sal.get("drug_MAP_mod") == 1.0
    assert sal.get("drug_SVR_mod") == 1.0
    assert epi.get("drug_MAP_mod") == 1.0
    assert epi.get("drug_SVR_mod") == 1.0


def test_v311_ino_reduces_pvr_and_shunt_modifiers_with_onset_and_offset():
    bus = PhysiologicalBus()
    ino = INOModule({"tau_onset_s": 10.0, "tau_offset_s": 5.0})
    ino.initialize(bus)

    bus.set("ino_ppm", 20.0)
    for _ in range(10):
        ino.step(bus, 1.0)
    on_pvr_mod = bus.get("ino_PVR_mod")
    on_qs_mod = bus.get("ino_Qs_Qt_mod")

    assert on_pvr_mod < 1.0
    assert on_qs_mod < 1.0
    assert bus.get("ino_pulmonary_vasodilation_signal") > 0.20
    assert bus.get("ino_oxygenation_signal") > 0.10

    bus.set("ino_ppm", 0.0)
    ino.step(bus, 1.0)
    assert bus.get("ino_rebound_risk_signal") > 0.0
    for _ in range(40):
        ino.step(bus, 1.0)

    assert bus.get("ino_PVR_mod") > on_pvr_mod
    assert bus.get("ino_Qs_Qt_mod") > on_qs_mod
    assert bus.get("ino_PVR_mod") > 0.95
    assert bus.get("ino_Qs_Qt_mod") > 0.95


def test_v311_ino_affects_pulmonary_not_systemic_vascular_tone_in_circulation():
    def run(ino_ppm: float):
        bus = PhysiologicalBus()
        bus.set("CO", 3.5)
        bus.set("MAP", 65.0)
        bus.set("PAP_mean", 28.0)
        bus.set("CVP", 5.0)
        bus.set("PAWP", 8.0)
        bus.set("PaO2", 55.0)
        bus.set("PEEP", 6.0)
        bus.set("Paw_current", 18.0)
        bus.set("ino_ppm", ino_ppm)
        ino = INOModule({"tau_onset_s": 1.0})
        circ = CirculationModule()
        ino.initialize(bus)
        circ.initialize(bus)
        for _ in range(40):
            ino.step(bus, 1.0)
            circ.step(bus, 1.0)
        return bus

    off = run(0.0)
    on = run(20.0)

    assert on.get("PVR") < off.get("PVR")
    assert on.get("PAP_mean") <= off.get("PAP_mean")
    # iNO should not directly vasodilate the systemic circulation.
    assert abs(on.get("SVR") - off.get("SVR")) < 1e-6

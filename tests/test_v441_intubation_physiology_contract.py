import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.bus import PhysiologicalBus
from modules.airway.intubation_physiology import IntubationPhysiologyModule


def _bus(**updates):
    bus = PhysiologicalBus()
    bus.update(updates)
    return bus


def test_preoxygenation_builds_reservoir_when_high_fio2_and_ventilation_effective():
    bus = _bus(FiO2_delivered=1.0, FiO2=1.0, intubated=True, ventilator_connected=True, RR_total=24.0, Vt=180.0)
    mod = IntubationPhysiologyModule()
    mod.initialize(bus)
    start = bus.get("preoxygenation_reservoir")

    for _ in range(60):
        mod.step(bus, 1.0)

    assert bus.get("intubation_physiology_revision") == 441
    assert bus.get("preoxygenation_active") is True
    assert bus.get("preoxygenation_reservoir") > start
    assert bus.get("peri_intubation_phase") == "preoxygenation"
    assert bus.get("apnea_active") is False


def test_apnea_timer_and_desaturation_risk_rise_after_failed_rsi_attempt():
    bus = _bus(
        FiO2_delivered=0.21,
        FiO2=0.21,
        intubated=False,
        ventilator_connected=False,
        manual_ventilation_active=False,
        bag_mask_ventilation_active=False,
        RR_total=0.0,
        Vt=0.0,
        drug_NMB_frac=1.0,
        sed_resp_mod=0.05,
        airway_event_type="failed_intubation_attempt",
        SaO2=0.97,
        PaO2=92.0,
    )
    mod = IntubationPhysiologyModule()
    mod.initialize(bus)

    for _ in range(35):
        mod.step(bus, 1.0)

    assert bus.get("apnea_active") is True
    assert bus.get("apnea_timer_s") >= 35.0
    assert bus.get("rsi_effect_active") is True
    assert bus.get("rsi_resp_suppression_index") > 0.75
    assert bus.get("peri_intubation_desaturation_risk") > 0.25
    assert bus.get("SaO2") < 0.97
    assert bus.get("peri_intubation_phase") == "apnea"


def test_bag_mask_ventilation_reduces_apnea_burden_and_recovers_phase():
    bus = _bus(
        FiO2_delivered=1.0,
        FiO2=1.0,
        intubated=False,
        ventilator_connected=True,
        manual_ventilation_active=True,
        bag_mask_ventilation_active=True,
        bag_mask_quality=0.85,
        RR_total=20.0,
        Vt=160.0,
        apnea_timer_s=20.0,
        preoxygenation_reservoir=0.35,
        SaO2=0.88,
        PaO2=55.0,
    )
    mod = IntubationPhysiologyModule()
    mod.initialize(bus)
    start_timer = bus.get("apnea_timer_s")

    for _ in range(10):
        mod.step(bus, 1.0)

    assert bus.get("apnea_active") is False
    assert bus.get("apnea_timer_s") < start_timer
    assert bus.get("preoxygenation_reservoir") > 0.35
    assert bus.get("peri_intubation_desaturation_risk") < 0.60

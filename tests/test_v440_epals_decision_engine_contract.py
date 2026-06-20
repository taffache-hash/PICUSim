import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.bus import PhysiologicalBus
from modules.decision.epals import EPALSDecisionModule


def _bus(**updates):
    bus = PhysiologicalBus()
    bus.update(updates)
    return bus


def test_epals_decision_detects_airway_breathing_priority():
    bus = _bus(SaO2=0.82, intubated=True, ventilator_connected=False, airway_interface="ETT")
    mod = EPALSDecisionModule()
    mod.initialize(bus)

    assert bus.get("decision_engine_revision") == 440
    assert bus.get("decision_priority") == "airway_breathing_first"
    assert bus.get("decision_abcde_step") == "A/B"
    assert bus.get("decision_escalation_needed") is True
    assert bus.get("decision_warning_level") == "high"
    assert "hypoxemia" in bus.get("decision_context_flags")


def test_epals_decision_detects_shock_and_antibiotic_gap():
    bus = _bus(
        shock_type="distributive",
        shock_stage="decompensated",
        shock_severity=0.72,
        MAP=48.0,
        lactate=5.2,
        infection_load=0.8,
        antibiotic_started=False,
    )
    mod = EPALSDecisionModule()
    mod.initialize(bus)

    assert bus.get("decision_priority") == "circulation_shock"
    assert bus.get("decision_pattern") == "distributive_shock"
    assert bus.get("decision_abcde_step") == "C"
    assert bus.get("decision_escalation_needed") is True
    assert bus.get("decision_warning_level") == "high"
    assert "antibiotic_started" in bus.get("decision_warning")


def test_epals_decision_detects_arrest_without_cpr_as_critical_warning():
    bus = _bus(cardiac_arrest_active=True, shockable_rhythm=True, CPR_active=False)
    mod = EPALSDecisionModule()
    mod.step(bus, 1.0)

    assert bus.get("decision_priority") == "cardiac_arrest_algorithm"
    assert bus.get("decision_pattern") == "shockable_arrest"
    assert bus.get("decision_warning_level") == "critical"
    assert bus.get("decision_escalation_needed") is True

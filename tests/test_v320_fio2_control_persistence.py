"""v3.2 public-polish FiO2 command persistence contracts.

These tests guard against a visible UI/API failure where the FiO2 slider appeared
or behaved as if it always snapped back to room air.  The core contract is that
FiO2 is the commanded set-point, while FiO2_delivered may differ according to
interface efficiency/leak.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.session import SessionManager


def _session(scenario: str):
    return SessionManager().create(scenario, dt=0.2)


def test_fio2_command_persists_on_ventilator_ett():
    s = _session("healthy_child_20kg")
    result = s.apply("set_fio2", {"value": 0.80})
    assert result["value"] == 0.80
    s.step(1.0)
    assert abs(float(s.bus.get("FiO2")) - 0.80) < 1e-9
    assert abs(float(s.bus.get("FiO2_delivered")) - 0.80) < 1e-9


def test_fio2_command_accepts_percent_input():
    s = _session("healthy_child_20kg")
    s.apply("set_fio2", {"value": 80})
    s.step(1.0)
    assert abs(float(s.bus.get("FiO2")) - 0.80) < 1e-9


def test_fio2_command_persists_on_hfnc_setpoint():
    s = _session("airway_hfnc_bronchiolitis_v1_23_1")
    s.apply("set_fio2", {"value": 0.80})
    assert abs(float(s.bus.get("HFNC_FiO2_set")) - 0.80) < 1e-9
    assert abs(float(s.bus.get("oxygen_FiO2_set")) - 0.80) < 1e-9
    s.step(2.0)
    assert abs(float(s.bus.get("FiO2")) - 0.80) < 1e-9
    assert abs(float(s.bus.get("HFNC_FiO2_set")) - 0.80) < 1e-9
    assert float(s.bus.get("FiO2_delivered")) > 0.60


def test_fio2_command_persists_on_low_flow_oxygen_setpoint():
    s = _session("airway_unassisted_spontaneous_breathing_v1_23")
    s.apply("set_fio2", {"value": 0.80})
    assert abs(float(s.bus.get("oxygen_FiO2_set")) - 0.80) < 1e-9
    s.step(2.0)
    assert abs(float(s.bus.get("FiO2")) - 0.80) < 1e-9
    assert abs(float(s.bus.get("oxygen_FiO2_set")) - 0.80) < 1e-9
    # Delivered FiO2 may be lower because low-flow oxygen is not a blender at the alveolus.
    assert float(s.bus.get("FiO2_delivered")) > 0.21


def test_fio2_command_persists_on_niv_setpoint():
    s = _session("airway_niv_cpap_bronchiolitis_v1_23_2")
    s.apply("set_fio2", {"value": 0.80})
    assert abs(float(s.bus.get("NIV_FiO2_set")) - 0.80) < 1e-9
    s.step(2.0)
    assert abs(float(s.bus.get("FiO2")) - 0.80) < 1e-9
    assert abs(float(s.bus.get("NIV_FiO2_set")) - 0.80) < 1e-9
    assert float(s.bus.get("FiO2_delivered")) > 0.50

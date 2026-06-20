from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.bus import PhysiologicalBus, BusState
from modules.pharmacology.pk_pd import PharmacologyModule



def test_vancomycin_concentration_and_audit_increase():
    bus = PhysiologicalBus(BusState(weight_kg=20.0, age_y=6.0, GFR=70.0, GFR_baseline=70.0))
    bus.set("vancomycin_mg_kg_h", 60.0)
    mod = PharmacologyModule({"weight_kg": 20.0, "age_y": 6.0, "age_group": "child"})
    mod.initialize(bus)
    for _ in range(120):
        mod.step(bus, 1.0)
    assert bus.get("pk_supported_drug_count") == 15
    assert bus.get("C_vancomycin_mg_L") > 1.0
    assert 0.0 <= bus.get("vancomycin_target_attainment") <= 1.0
    assert bus.get("vancomycin_coverage_mod") > 0.0


def test_vancomycin_renal_clearance_factor_tracks_gfr():
    bus_normal = PhysiologicalBus(BusState(weight_kg=20.0, age_y=6.0, GFR=70.0, GFR_baseline=70.0))
    bus_low = PhysiologicalBus(BusState(weight_kg=20.0, age_y=6.0, GFR=14.0, GFR_baseline=70.0, AKI_stage=2))
    mod_n = PharmacologyModule({"weight_kg": 20.0, "age_y": 6.0, "age_group": "child"})
    mod_l = PharmacologyModule({"weight_kg": 20.0, "age_y": 6.0, "age_group": "child"})
    mod_n.initialize(bus_normal); mod_l.initialize(bus_low)
    mod_n.step(bus_normal, 1.0); mod_l.step(bus_low, 1.0)
    assert bus_low.get("vancomycin_renal_clearance_factor") < bus_normal.get("vancomycin_renal_clearance_factor")


def test_vancomycin_crrt_clearance_field_positive_when_active():
    bus = PhysiologicalBus(BusState(weight_kg=20.0, age_y=6.0, GFR=25.0, GFR_baseline=70.0, CRRT_active=True, CRRT_effluent_mL_kg_h=35.0))
    bus.set("vancomycin_mg_kg_h", 2.5)
    mod = PharmacologyModule({"weight_kg": 20.0, "age_y": 6.0, "age_group": "child"})
    mod.initialize(bus)
    mod.step(bus, 1.0)
    assert bus.get("pk_crrt_active") is True
    assert bus.get("pk_crrt_vancomycin_CL_L_min") > 0.0


def test_vancomycin_scenario_smoke():
    cmd = [sys.executable, str(ROOT / "run_simulation.py"), "--scenario", str(ROOT / "scenarios" / "picu_vancomycin_aki_crrt_v1_12.yaml"), "--dt", "5", "--no-plot"]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stderr[-1000:] + result.stdout[-1000:]
    assert "C_vancomycin_mg_L" in result.stdout

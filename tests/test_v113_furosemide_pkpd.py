from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.bus import PhysiologicalBus, BusState
from modules.pharmacology.pk_pd import PharmacologyModule


def _step_module(bus, seconds=180, dt=1.0):
    mod = PharmacologyModule({"weight_kg": float(bus.get("weight_kg")), "age_y": float(bus.get("age_y")), "age_group": "child"})
    mod.initialize(bus)
    for _ in range(int(seconds / dt)):
        mod.step(bus, dt)
    return mod


def test_furosemide_bolus_generates_concentration_and_effect_signal():
    bus = PhysiologicalBus(BusState(weight_kg=20.0, age_y=6.0, GFR=70.0, GFR_baseline=70.0))
    bus.set("furosemide_mg_kg", 1.0)
    _step_module(bus, seconds=60, dt=1.0)
    assert bus.get("pk_supported_drug_count") == 15
    assert bus.get("C_furosemide_mg_L") > 0.1
    assert 0.0 <= bus.get("furosemide_effect_signal") <= 1.0
    assert bus.get("furosemide_effect_signal") > 0.0


def test_furosemide_renal_factor_tracks_aki_and_gfr():
    normal = PhysiologicalBus(BusState(weight_kg=20.0, age_y=6.0, GFR=70.0, GFR_baseline=70.0, AKI_stage=0))
    aki = PhysiologicalBus(BusState(weight_kg=20.0, age_y=6.0, GFR=14.0, GFR_baseline=70.0, AKI_stage=2))
    normal.set("furosemide_mg_kg_h", 0.2)
    aki.set("furosemide_mg_kg_h", 0.2)
    _step_module(normal, seconds=30, dt=1.0)
    _step_module(aki, seconds=30, dt=1.0)
    assert aki.get("furosemide_renal_clearance_factor") < normal.get("furosemide_renal_clearance_factor")
    assert aki.get("furosemide_effect_signal") < normal.get("furosemide_effect_signal")


def test_furosemide_crrt_audit_field_positive_when_active():
    bus = PhysiologicalBus(BusState(weight_kg=20.0, age_y=6.0, GFR=25.0, GFR_baseline=70.0, CRRT_active=True, CRRT_effluent_mL_kg_h=35.0))
    bus.set("furosemide_mg_kg_h", 0.2)
    _step_module(bus, seconds=1, dt=1.0)
    assert bus.get("pk_crrt_active") is True
    assert bus.get("pk_crrt_furosemide_CL_L_min") > 0.0


def test_furosemide_scenario_smoke():
    cmd = [sys.executable, str(ROOT / "run_simulation.py"), "--scenario", str(ROOT / "scenarios" / "picu_furosemide_fluid_overload_v1_13.yaml"), "--dt", "5", "--no-plot"]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stderr[-1000:] + result.stdout[-1000:]
    assert "C_furosemide_mg_L" in result.stdout
    assert "furosemide_effect_signal" in result.stdout

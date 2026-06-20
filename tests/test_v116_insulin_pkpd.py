from __future__ import annotations
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.bus import PhysiologicalBus
from modules.pharmacology.pk_pd import PharmacologyModule
from modules.nutrition.glucose import GlucoseModule
from modules.acidbase.electrolytes import AcidBaseElectrolyteModule


def step_modules(bus, ph, gl, ab=None, seconds=600, dt=5.0):
    ph.initialize(bus); gl.initialize(bus)
    if ab is not None:
        ab.initialize(bus)
    for _ in range(int(seconds // dt)):
        ph.step(bus, dt)
        gl.step(bus, dt)
        if ab is not None:
            ab.step(bus, dt)


def test_insulin_generates_concentration_and_pd_signals():
    bus = PhysiologicalBus()
    bus.set("insulin_UI_h", 1.0)
    bus.set("glucose_mmol_L", 12.0)
    bus.set("GIR_mg_kg_min", 6.0)
    ph = PharmacologyModule({"weight_kg": 20.0, "age_y": 6.0, "age_group": "child"})
    gl = GlucoseModule({"weight_kg": 20.0, "glucose_baseline_mmol_L": 12.0, "GIR_mg_kg_min": 6.0})
    step_modules(bus, ph, gl)
    assert bus.get("C_insulin_mU_L") > 0.0
    assert bus.get("insulin_glucose_clearance_signal") > 0.0
    assert bus.get("insulin_potassium_shift_signal") >= 0.0
    assert 0.0 <= bus.get("insulin_hypoglycemia_risk") <= 1.0
    assert bus.get("pk_supported_drug_count") == 15
    assert bus.get("pk_extension_revision") == 117


def test_insulin_lowers_glucose_vs_no_insulin():
    def run(insulin):
        bus = PhysiologicalBus()
        bus.set("insulin_UI_h", insulin)
        bus.set("glucose_mmol_L", 12.0)
        bus.set("GIR_mg_kg_min", 4.0)
        ph = PharmacologyModule({"weight_kg": 20.0})
        gl = GlucoseModule({"weight_kg": 20.0, "glucose_baseline_mmol_L": 12.0, "GIR_mg_kg_min": 4.0})
        step_modules(bus, ph, gl, seconds=900)
        return bus.get("glucose_mmol_L"), bus.get("C_insulin_mU_L")
    g0, c0 = run(0.0)
    g1, c1 = run(1.0)
    assert c0 == 0.0
    assert c1 > 0.0
    assert g1 < g0


def test_insulin_potassium_signal_moves_k_down():
    def run(insulin):
        bus = PhysiologicalBus()
        bus.set("insulin_UI_h", insulin)
        bus.set("glucose_mmol_L", 12.0)
        bus.set("GIR_mg_kg_min", 4.0)
        bus.set("K_mmol_L", 4.8)
        ph = PharmacologyModule({"weight_kg": 20.0})
        gl = GlucoseModule({"weight_kg": 20.0, "glucose_baseline_mmol_L": 12.0, "GIR_mg_kg_min": 4.0})
        ab = AcidBaseElectrolyteModule({})
        step_modules(bus, ph, gl, ab, seconds=600)
        return bus.get("K_mmol_L")
    assert run(1.5) < run(0.0)


def test_insulin_audit_tool_passes():
    cmd = [sys.executable, str(ROOT / "tools" / "pkpd_insulin_audit_v1_16.py"), "--fail-on-review"]
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=90)
    assert result.returncode == 0, result.stderr + result.stdout
    assert '"status": "PASS"' in result.stdout


def test_insulin_scenario_smoke():
    cmd = [sys.executable, str(ROOT / "run_simulation.py"), "--scenario", str(ROOT / "scenarios" / "picu_insulin_stress_hyperglycemia_v1_16.yaml"), "--dt", "5", "--no-plot"]
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=90)
    assert result.returncode == 0, result.stderr + result.stdout
    assert "C_insulin_mU_L" in result.stdout
    assert "insulin_glucose_clearance_signal" in result.stdout

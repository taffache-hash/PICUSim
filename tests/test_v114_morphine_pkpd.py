from __future__ import annotations
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.bus import PhysiologicalBus
from modules.pharmacology.pk_pd import PharmacologyModule
from modules.analgosedation.pain_stress_sedation import PainStressSedationModule


def step_pair(bus, ph, ps, seconds=600, dt=5.0):
    ph.initialize(bus)
    ps.initialize(bus)
    for _ in range(int(seconds // dt)):
        ph.step(bus, dt)
        ps.step(bus, dt)


def test_morphine_generates_concentration_and_pd_signals():
    bus = PhysiologicalBus()
    bus.set("morphine_mcg_kg_h", 25.0)
    ph = PharmacologyModule({"weight_kg": 20.0, "age_y": 6.0, "age_group": "child"})
    ps = PainStressSedationModule({"weight_kg": 20.0})
    step_pair(bus, ph, ps)
    assert bus.get("C_morphine_ng_mL") > 0.1
    assert bus.get("morphine_analgesia_signal") > 0.0
    assert 0.0 <= bus.get("morphine_resp_depression_signal") <= 1.0
    assert bus.get("pk_supported_drug_count") == 15


def test_morphine_aki_increases_renal_accumulation_risk():
    normal = PhysiologicalBus(); aki = PhysiologicalBus()
    for b in (normal, aki):
        b.set("morphine_mcg_kg_h", 20.0)
        b.set("GFR_baseline", 70.0)
    normal.set("GFR", 70.0); normal.set("AKI_stage", 0)
    aki.set("GFR", 25.0); aki.set("AKI_stage", 2)
    ph1 = PharmacologyModule({"weight_kg": 20.0}); ps1 = PainStressSedationModule({"weight_kg": 20.0})
    ph2 = PharmacologyModule({"weight_kg": 20.0}); ps2 = PainStressSedationModule({"weight_kg": 20.0})
    step_pair(normal, ph1, ps1)
    step_pair(aki, ph2, ps2)
    assert aki.get("morphine_renal_accumulation_risk") > normal.get("morphine_renal_accumulation_risk")
    assert aki.get("M6G_accumulation_proxy") >= normal.get("M6G_accumulation_proxy")


def test_morphine_crrt_audit_field_positive_when_active():
    bus = PhysiologicalBus()
    bus.set("morphine_mcg_kg_h", 20.0)
    bus.set("CRRT_active", True)
    bus.set("CRRT_effluent_mL_kg_h", 35.0)
    ph = PharmacologyModule({"weight_kg": 20.0}); ps = PainStressSedationModule({"weight_kg": 20.0})
    step_pair(bus, ph, ps)
    assert bus.get("pk_crrt_morphine_CL_L_min") > 0.0


def test_morphine_scenario_smoke():
    cmd = [sys.executable, str(ROOT / "run_simulation.py"), "--scenario", str(ROOT / "scenarios" / "picu_morphine_analgesia_aki_v1_14.yaml"), "--dt", "5", "--no-plot"]
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=90)
    assert result.returncode == 0, result.stderr + result.stdout
    assert "C_morphine_ng_mL" in result.stdout
    assert "morphine_analgesia_signal" in result.stdout

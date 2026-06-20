from __future__ import annotations
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.bus import PhysiologicalBus
from modules.pharmacology.pk_pd import PharmacologyModule
from modules.analgosedation.pain_stress_sedation import PainStressSedationModule


def step_pair(bus, ph, ps, seconds=900, dt=5.0):
    ph.initialize(bus); ps.initialize(bus)
    for _ in range(int(seconds // dt)):
        ph.step(bus, dt); ps.step(bus, dt)


def test_clonidine_generates_centralized_concentration_and_pd_signals():
    bus = PhysiologicalBus()
    bus.set("clonidine_mcg_kg_h", 0.8)
    ph = PharmacologyModule({"weight_kg": 20.0, "age_y": 6.0, "age_group": "child"})
    ps = PainStressSedationModule({"weight_kg": 20.0})
    step_pair(bus, ph, ps)
    assert bus.get("C_clonidine_ng_mL") > 0.01
    assert bus.get("clonidine_sedation_signal") > 0.0
    assert bus.get("clonidine_sympatholysis_signal") > 0.0
    assert 0.0 <= bus.get("clonidine_bradycardia_risk") <= 1.0
    assert 0.0 <= bus.get("clonidine_hypotension_risk") <= 1.0
    assert bus.get("pk_supported_drug_count") == 15
    assert bus.get("pk_extension_revision") == 117


def test_clonidine_external_pk_prevents_analgosedation_overwrite():
    bus = PhysiologicalBus()
    bus.set("clonidine_mcg_kg_h", 0.8)
    ph = PharmacologyModule({"weight_kg": 20.0}); ps = PainStressSedationModule({"weight_kg": 20.0})
    ph.initialize(bus); ps.initialize(bus)
    for _ in range(60):
        ph.step(bus, 5.0)
        before = bus.get("C_clonidine_ng_mL")
        ps.step(bus, 5.0)
        after = bus.get("C_clonidine_ng_mL")
        assert abs(after - before) < 1e-9


def test_clonidine_crrt_audit_field_positive_when_active():
    bus = PhysiologicalBus()
    bus.set("clonidine_mcg_kg_h", 0.8)
    bus.set("CRRT_active", True)
    bus.set("CRRT_effluent_mL_kg_h", 35.0)
    ph = PharmacologyModule({"weight_kg": 20.0}); ps = PainStressSedationModule({"weight_kg": 20.0})
    step_pair(bus, ph, ps)
    assert bus.get("pk_crrt_clonidine_CL_L_min") > 0.0


def test_clonidine_scenario_smoke():
    cmd = [sys.executable, str(ROOT / "run_simulation.py"), "--scenario", str(ROOT / "scenarios" / "picu_clonidine_withdrawal_weaning_v1_15.yaml"), "--dt", "5", "--no-plot"]
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=90)
    assert result.returncode == 0, result.stderr + result.stdout
    assert "C_clonidine_ng_mL" in result.stdout
    assert "clonidine_sedation_signal" in result.stdout

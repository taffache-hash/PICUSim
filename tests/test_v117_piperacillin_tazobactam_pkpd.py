from __future__ import annotations
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.bus import PhysiologicalBus
from modules.pharmacology.pk_pd import PharmacologyModule
from modules.infection.antimicrobial_basic import InfectionAntimicrobialModule


def step_pharm(bus, mod, seconds=1800, dt=5.0):
    mod.initialize(bus)
    for _ in range(int(seconds // dt)):
        mod.step(bus, dt)


def test_piperacillin_generates_concentration_and_coverage_signal():
    bus = PhysiologicalBus()
    bus.set('piperacillin_mg_kg_h', 12.5)
    ph = PharmacologyModule({'weight_kg': 20.0, 'age_y': 6.0, 'age_group': 'child'})
    step_pharm(bus, ph)
    assert bus.get('C_piperacillin_mg_L') > 0.0
    assert 0.0 <= bus.get('piperacillin_ft_above_MIC') <= 1.0
    assert 0.0 <= bus.get('piperacillin_target_attainment') <= 1.0
    assert bus.get('piperacillin_coverage_mod') >= 0.0
    assert bus.get('antibiotic_started') is True
    assert bus.get('pk_supported_drug_count') == 15
    assert bus.get('pk_extension_revision') == 117


def test_piperacillin_dose_response_concentration():
    def run(dose):
        bus = PhysiologicalBus(); bus.set('piperacillin_mg_kg_h', dose)
        ph = PharmacologyModule({'weight_kg': 20.0})
        step_pharm(bus, ph)
        return bus.get('C_piperacillin_mg_L'), bus.get('piperacillin_coverage_mod')
    c_low, cov_low = run(6.0)
    c_std, cov_std = run(12.5)
    assert c_std > c_low
    assert cov_std >= cov_low


def test_piperacillin_renal_function_changes_clearance():
    def run(gfr, aki):
        bus = PhysiologicalBus()
        bus.set('piperacillin_mg_kg_h', 12.5)
        bus.set('GFR', gfr); bus.set('GFR_baseline', 70.0); bus.set('AKI_stage', aki)
        ph = PharmacologyModule({'weight_kg': 20.0})
        step_pharm(bus, ph)
        return bus.get('C_piperacillin_mg_L'), bus.get('piperacillin_renal_clearance_factor')
    c_arc, rf_arc = run(130.0, 0)
    c_aki, rf_aki = run(25.0, 2)
    assert rf_arc > rf_aki
    assert c_aki > c_arc


def test_piperacillin_signal_feeds_infection_module():
    bus = PhysiologicalBus()
    bus.set('infection_load', 0.7); bus.set('microbial_burden', 0.7)
    bus.set('source_control', 0.5); bus.set('pathogen_resistance_index', 0.1)
    bus.set('piperacillin_mg_kg_h', 18.0)
    ph = PharmacologyModule({'weight_kg': 20.0}); inf = InfectionAntimicrobialModule({})
    ph.initialize(bus); inf.initialize(bus)
    for _ in range(int(1800 // 5)):
        ph.step(bus, 5.0)
        inf.step(bus, 5.0)
    assert bus.get('antibiotic_started') is True
    assert bus.get('antibiotic_coverage') > 0.0
    assert bus.get('antibiotic_effect') > 0.0


def test_piperacillin_audit_tool_passes():
    cmd = [sys.executable, str(ROOT / 'tools' / 'pkpd_piperacillin_tazobactam_audit_v1_17.py'), '--fail-on-review']
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=90)
    assert result.returncode == 0, result.stderr + result.stdout
    assert '"status": "PASS"' in result.stdout


def test_piperacillin_scenario_smoke():
    cmd = [sys.executable, str(ROOT / 'run_simulation.py'), '--scenario', str(ROOT / 'scenarios' / 'picu_piperacillin_tazobactam_sepsis_v1_17.yaml'), '--dt', '5', '--no-plot']
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=90)
    assert result.returncode == 0, result.stderr + result.stdout
    assert 'C_piperacillin_mg_L' in result.stdout
    assert 'piperacillin_target_attainment' in result.stdout

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import yaml
import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_v500c_guardrail_spec_has_critical_and_logical_rules():
    spec = yaml.safe_load((ROOT / "data" / "plausibility_guardrails_v5.0C.yaml").read_text(encoding="utf-8"))
    assert spec["version"] == "v5.0C"
    for key in ["SaO2_final", "FiO2_final", "MAP_min", "pH_a_min"]:
        assert key in spec["critical_bounds"]
        assert len(spec["critical_bounds"][key]) == 2
    assert len(spec["logical_rules"]) >= 4
    assert spec["clamp_policy"]["mode"] == "audit_only"


def test_v500c_guardrail_runner_detects_impossible_states(tmp_path):
    rows = pd.DataFrame([
        {"scenario": "healthy_child_20kg", "run": 0, "SaO2_final": 1.2, "SaO2_min": 0.9, "FiO2_final": 0.3, "PaO2_final": 80, "PaCO2_final": 40, "PaCO2_max": 40, "pH_a_final": 7.4, "pH_a_min": 7.4, "MAP_final": 80, "MAP_min": 70, "HR_final": 100, "lactate_final": 1, "lactate_max": 1, "K_mmol_L_final": 4, "Na_mmol_L_final": 138, "glucose_mmol_L_final": 5, "creatinine_mg_dL_final": 0.4, "urine_rate_mL_h_final": 40, "PEEP_final": 5, "Paw_final": 10, "VILI_risk_final": 0.1, "VILI_risk_max": 0.1},
        {"scenario": "epals_v2_septic_shock_warm", "run": 1, "SaO2_final": 0.92, "SaO2_min": 0.9, "FiO2_final": 0.4, "PaO2_final": 80, "PaCO2_final": 40, "PaCO2_max": 40, "pH_a_final": 7.2, "pH_a_min": 7.2, "MAP_final": 35, "MAP_min": 30, "HR_final": 170, "lactate_final": 0.5, "lactate_max": 0.5, "K_mmol_L_final": 4, "Na_mmol_L_final": 138, "glucose_mmol_L_final": 5, "creatinine_mg_dL_final": 0.4, "urine_rate_mL_h_final": 10, "PEEP_final": 5, "Paw_final": 10, "VILI_risk_final": 0.1, "VILI_risk_max": 0.1},
    ])
    input_csv = tmp_path / "input.csv"
    rows.to_csv(input_csv, index=False)
    outdir = tmp_path / "guardrails"
    cmd = [sys.executable, str(ROOT / "tools" / "plausibility_guardrails_v5_0C.py"), "--input", str(input_csv), "--outdir", str(outdir)]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr + result.stdout
    summary = json.loads((outdir / "plausibility_guardrail_summary_v50C.json").read_text(encoding="utf-8"))
    assert summary["release_step"] == "5.0C"
    assert summary["rows_audited"] == 2
    assert summary["critical_findings"] >= 2
    assert summary["pass_guardrails"] is False
    assert (outdir / "plausibility_guardrail_report_v50C.md").exists()


def test_v500c_guardrail_runner_accepts_current_monte_carlo_outputs(tmp_path):
    mc = ROOT / "outputs" / "monte_carlo_v5.0B" / "monte_carlo_results_v50B.csv"
    if not mc.exists():
        pytest.skip("Generated Monte Carlo output artifacts are intentionally excluded from the distributed public source package")
    outdir = tmp_path / "guardrails_current"
    cmd = [sys.executable, str(ROOT / "tools" / "plausibility_guardrails_v5_0C.py"), "--input", str(mc), "--outdir", str(outdir)]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr + result.stdout
    summary = json.loads((outdir / "plausibility_guardrail_summary_v50C.json").read_text(encoding="utf-8"))
    assert summary["rows_audited"] > 0
    assert summary["critical_findings"] == 0

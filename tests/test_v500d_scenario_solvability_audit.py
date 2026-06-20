from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_scenario_solvability_audit_runs_and_has_no_critical_findings(tmp_path):
    outdir = tmp_path / "solvability"
    cmd = [
        sys.executable,
        str(ROOT / "tools" / "scenario_solvability_audit_v5_0D.py"),
        "--outdir",
        str(outdir),
        "--fail-on-critical",
    ]
    subprocess.run(cmd, cwd=ROOT, check=True)
    summary = json.loads((outdir / "scenario_solvability_summary_v50D.json").read_text())
    assert summary["scenarios_audited"] == 8
    assert summary["critical_findings"] == 0
    assert summary["playable"] == 8
    assert summary["recoverable"] >= 8
    assert summary["failable"] >= 8
    assert summary["non_deterministic"] >= 8


def test_scenario_solvability_report_is_written(tmp_path):
    outdir = tmp_path / "solvability"
    subprocess.run([
        sys.executable,
        str(ROOT / "tools" / "scenario_solvability_audit_v5_0D.py"),
        "--outdir",
        str(outdir),
    ], cwd=ROOT, check=True)
    report = outdir / "scenario_solvability_report_v50D.md"
    csv_file = outdir / "scenario_solvability_audit_v50D.csv"
    assert report.exists()
    assert csv_file.exists()
    text = report.read_text()
    assert "Scenario Solvability Audit" in text
    assert "epals_v2_septic_shock_warm" in text

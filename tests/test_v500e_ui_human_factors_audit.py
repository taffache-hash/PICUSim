from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_ui_human_factors_audit_runs_without_critical_findings(tmp_path):
    outdir = tmp_path / "ui_human_factors"
    subprocess.run([
        sys.executable,
        str(ROOT / "tools" / "ui_human_factors_audit_v5_0E.py"),
        "--outdir",
        str(outdir),
        "--fail-on-critical",
    ], cwd=ROOT, check=True)
    summary = json.loads((outdir / "ui_human_factors_summary_v50E.json").read_text())
    assert summary["critical"] == 0
    assert summary["ui_human_factors_gate_passed"] is True
    assert summary["side_vital_font_min_px"] >= 32
    assert summary["compact_waveform_max_px"] <= 110


def test_ui_human_factors_report_and_csv_are_written(tmp_path):
    outdir = tmp_path / "ui_human_factors"
    subprocess.run([
        sys.executable,
        str(ROOT / "tools" / "ui_human_factors_audit_v5_0E.py"),
        "--outdir",
        str(outdir),
    ], cwd=ROOT, check=True)
    report = outdir / "ui_human_factors_report_v50E.md"
    csv_file = outdir / "ui_human_factors_audit_v50E.csv"
    assert report.exists()
    assert csv_file.exists()
    text = report.read_text()
    assert "UI Human Factors Audit" in text
    assert "Numeric vital signs remain the primary monitor surface" in text

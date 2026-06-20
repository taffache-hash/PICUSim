import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_v121_spec_has_presets_and_core_scenarios():
    spec = yaml.safe_load((ROOT / "data" / "sobol_full_specs_v1.21.yaml").read_text(encoding="utf-8"))
    assert spec["version"] == "v1.21"
    assert {"smoke", "exploratory", "report", "paper"}.issubset(spec["presets"])
    for key in ["ards_mild", "septic_shock", "status_asthmaticus", "neonatal_rds_3kg"]:
        assert key in spec["scenarios"]
        assert len(spec["scenarios"][key]["parameters"]) >= 4


def test_v121_dry_run_writes_plan(tmp_path):
    outdir = tmp_path / "sobol_dry"
    cmd = [
        sys.executable,
        str(ROOT / "tools" / "sobol_full_runner_v1_21.py"),
        "--preset", "exploratory",
        "--dry-run",
        "--scenarios", "ards_mild", "septic_shock",
        "--outdir", str(outdir),
    ]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr[-1000:] + result.stdout[-1000:]
    summary = json.loads((outdir / "sobol_full_summary_v121.json").read_text(encoding="utf-8"))
    assert summary["status"] == "PASS"
    assert summary["dry_run"] is True
    assert summary["total_expected_evaluations"] > 0
    assert (outdir / "sobol_full_plan_v121.csv").exists()
    assert (outdir / "sobol_full_report_v121.md").exists()


def test_v121_smoke_execution_one_scenario(tmp_path):
    outdir = tmp_path / "sobol_smoke"
    cmd = [
        sys.executable,
        str(ROOT / "tools" / "sobol_full_runner_v1_21.py"),
        "--preset", "smoke",
        "--scenarios", "ards_mild",
        "--outdir", str(outdir),
        "--fail-on-error",
    ]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stderr[-1000:] + result.stdout[-1000:]
    summary = json.loads((outdir / "sobol_full_summary_v121.json").read_text(encoding="utf-8"))
    assert summary["status"] == "PASS"
    assert summary["total_actual_evaluations"] == summary["scenario_rows"][0]["expected_evaluations"]
    assert summary["total_actual_indices"] > 0
    assert (outdir / "sobol_full_indices_v121.csv").exists()
    assert (outdir / "sobol_full_evaluations_v121.csv").exists()

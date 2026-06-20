import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_v500b_spec_has_core_scenarios_and_bounds():
    spec = yaml.safe_load((ROOT / "data" / "monte_carlo_specs_v5.0B.yaml").read_text(encoding="utf-8"))
    assert spec["version"] == "v5.0B"
    assert len(spec["scenarios"]) >= 5
    for scenario in spec["scenarios"]:
        assert (ROOT / "scenarios" / f"{scenario}.yaml").exists()
    for key in ["SaO2_final", "MAP_min", "PaCO2_max", "pH_a_min"]:
        assert key in spec["plausibility_bounds"]
        assert len(spec["plausibility_bounds"][key]) == 2


def test_v500b_short_monte_carlo_run_writes_outputs(tmp_path):
    outdir = tmp_path / "mc"
    cmd = [
        sys.executable,
        str(ROOT / "tools" / "monte_carlo_runner_v5_0B.py"),
        "--outdir", str(outdir),
        "--n", "2",
        "--dt", "30",
        "--scenarios", "healthy_child_20kg", "infant_bronchiolitis",
    ]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stderr[-1000:] + result.stdout[-1000:]
    summary = json.loads((outdir / "monte_carlo_summary_v50B.json").read_text(encoding="utf-8"))
    assert summary["release_step"] == "5.0B"
    assert summary["total_runs"] == 4
    assert summary["scenarios"] == 2
    assert (outdir / "monte_carlo_results_v50B.csv").exists()
    assert (outdir / "monte_carlo_draws_v50B.csv").exists()
    assert (outdir / "monte_carlo_report_v50B.md").exists()


def test_v500b_runner_records_flags_without_crashing(tmp_path):
    outdir = tmp_path / "mc_flags"
    cmd = [
        sys.executable,
        str(ROOT / "tools" / "monte_carlo_runner_v5_0B.py"),
        "--outdir", str(outdir),
        "--n", "1",
        "--dt", "30",
        "--scenarios", "epals_v2_septic_shock_warm",
    ]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stderr[-1000:] + result.stdout[-1000:]
    summary = json.loads((outdir / "monte_carlo_summary_v50B.json").read_text(encoding="utf-8"))
    assert summary["total_runs"] == 1
    assert summary["stable_runs"] + summary["flagged_runs"] == 1

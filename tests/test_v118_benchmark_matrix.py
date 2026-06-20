import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_v118_benchmark_spec_expands_coverage_and_has_traceable_sources():
    spec = yaml.safe_load((ROOT / "data" / "literature_benchmark_targets_v1.18.yaml").read_text(encoding="utf-8"))
    assert spec["version"] == "v1.18"
    assert len(spec["scenarios"]) >= 25
    assert "infant_bronchiolitis" in spec["scenarios"]
    assert "neonatal_rds_3kg" in spec["scenarios"]
    assert "picu_piperacillin_tazobactam_sepsis_v1_17" in spec["scenarios"]
    sources = set(spec["sources"])
    for scenario, scfg in spec["scenarios"].items():
        for variable, tcfg in scfg.get("targets", {}).items():
            assert "range" in tcfg, f"missing range for {scenario}:{variable}"
            assert tcfg.get("source"), f"missing source for {scenario}:{variable}"
            assert set(tcfg["source"]).issubset(sources), f"unknown source in {scenario}:{variable}"


def test_benchmark_matrix_no_run_outputs_summary(tmp_path):
    outdir = tmp_path / "bench"
    cmd = [sys.executable, str(ROOT / "tools" / "benchmark_matrix_v1_18.py"), "--no-run", "--outdir", str(outdir)]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr[-1000:]
    summary = json.loads((outdir / "benchmark_matrix_summary_v118.json").read_text(encoding="utf-8"))
    assert summary["benchmark_scenarios"] >= 25
    assert summary["target_rows"] >= 100
    assert summary["missing_source_rows"] == 0
    assert (outdir / "benchmark_target_matrix_v118.csv").exists()
    assert (outdir / "benchmark_scenario_coverage_v118.csv").exists()


def test_benchmark_matrix_targeted_evaluation_passes(tmp_path):
    outdir = tmp_path / "bench_eval"
    cmd = [
        sys.executable, str(ROOT / "tools" / "benchmark_matrix_v1_18.py"),
        "--outdir", str(outdir), "--dt", "10", "--fail-on-review",
        "--scenarios", "infant_bronchiolitis", "neonatal_rds_3kg", "picu_piperacillin_tazobactam_sepsis_v1_17",
    ]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stderr[-1000:] + result.stdout[-1000:]
    summary = json.loads((outdir / "benchmark_matrix_summary_v118.json").read_text(encoding="utf-8"))
    assert summary["evaluated_checks"] > 0
    assert summary["review"] == 0

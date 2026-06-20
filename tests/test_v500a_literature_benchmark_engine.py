import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_v500a_spec_has_traceable_core_benchmark_scenarios():
    spec = yaml.safe_load((ROOT / "data" / "literature_benchmark_targets_v5.0A.yaml").read_text(encoding="utf-8"))
    assert spec["version"] == "v5.0A"
    for scenario in [
        "healthy_child_20kg",
        "infant_bronchiolitis",
        "epals_v2_septic_shock_warm",
        "epals_v2_dka_dehydration_shock",
        "epals_v2_anaphylactic_shock",
    ]:
        assert scenario in spec["scenarios"]
        assert (ROOT / "scenarios" / f"{scenario}.yaml").exists()
    known_sources = set(spec["sources"])
    target_rows = 0
    for scfg in spec["scenarios"].values():
        for tcfg in scfg.get("targets", {}).values():
            target_rows += 1
            assert len(tcfg.get("range", [])) == 2
            assert set(tcfg.get("source", [])).issubset(known_sources)
    assert target_rows >= 15


def test_v500a_no_run_writes_source_matrix_and_summary(tmp_path):
    outdir = tmp_path / "bench"
    cmd = [sys.executable, str(ROOT / "tools" / "literature_benchmark_engine_v5_0A.py"), "--no-run", "--outdir", str(outdir)]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr[-1000:]
    summary = json.loads((outdir / "literature_benchmark_summary_v50A.json").read_text(encoding="utf-8"))
    assert summary["benchmark_scenarios"] >= 5
    assert summary["target_rows"] >= 15
    assert summary["missing_source_rows"] == 0
    assert (outdir / "literature_benchmark_source_matrix_v50A.csv").exists()
    assert (outdir / "literature_benchmark_report_v50A.md").exists()


def test_v500a_targeted_evaluation_produces_pass_or_review_without_crash(tmp_path):
    outdir = tmp_path / "bench_eval"
    cmd = [
        sys.executable,
        str(ROOT / "tools" / "literature_benchmark_engine_v5_0A.py"),
        "--outdir",
        str(outdir),
        "--dt",
        "10",
        "--scenarios",
        "healthy_child_20kg",
        "infant_bronchiolitis",
    ]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stderr[-1000:] + result.stdout[-1000:]
    summary = json.loads((outdir / "literature_benchmark_summary_v50A.json").read_text(encoding="utf-8"))
    assert summary["evaluated_checks"] > 0
    assert summary["no_data"] == 0
    assert (outdir / "literature_benchmark_results_v50A.csv").exists()

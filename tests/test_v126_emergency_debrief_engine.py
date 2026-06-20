from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "data" / "emergency_debrief_spec_v1.26.yaml"


def test_emergency_debrief_spec_exists_and_is_alpha():
    spec = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
    assert spec["version"] == "v1.26-alpha"
    assert "SpO2_nadir" in spec["core_metrics"]["oxygenation"]
    assert "decision_flags_csv" in spec["outputs"]


def test_emergency_debrief_engine_subset_smoke():
    cmd = [
        sys.executable,
        str(ROOT / "tools" / "emergency_debrief_engine_v1_26.py"),
        "--dt", "10",
        "--scenarios", "airway_failed_intubation_cannot_oxygenate_v1_25",
        "--fail-on-review",
    ]
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=180)
    assert res.returncode == 0, res.stdout + res.stderr
    outdir = ROOT / "outputs" / "emergency_debrief_v1.26"
    summary = json.loads((outdir / "emergency_debrief_summary_v126.json").read_text(encoding="utf-8"))
    assert summary["status"] == "PASS"
    assert summary["completed_scenarios"] == 1
    metrics = pd.read_csv(outdir / "emergency_debrief_scenario_metrics_v126.csv")
    assert metrics.loc[0, "scenario"] == "airway_failed_intubation_cannot_oxygenate_v1_25"
    assert metrics.loc[0, "failed_intubation_count"] >= 2
    assert metrics.loc[0, "intubation_success_time_s"] > 0
    flags = pd.read_csv(outdir / "emergency_debrief_decision_flags_v126.csv")
    assert "repeated_failed_attempts" in set(flags["flag"])


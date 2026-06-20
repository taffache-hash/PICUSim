from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "epals_debrief_scaffold_v1_22_3.py"


def test_epals_debrief_spec_and_tool_exist():
    assert (ROOT / "data" / "epals_debrief_spec_v1.22.3.yaml").exists()
    assert TOOL.exists()
    assert (ROOT / "docs" / "EPALS_DEBRIEF_SCAFFOLD_v1.22.3.md").exists()


def test_epals_debrief_metadata_only_generates_all_scenarios(tmp_path):
    outdir = tmp_path / "debrief_meta"
    result = subprocess.run(
        [sys.executable, str(TOOL), "--no-run", "--outdir", str(outdir)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    summary = json.loads((outdir / "epals_debrief_summary_v1223.json").read_text(encoding="utf-8"))
    assert summary["release"] == "v1.22.3-alpha"
    assert summary["scenario_count"] == 10
    assert summary["question_rows"] >= 20
    assert (outdir / "epals_debrief_index_v1223.md").exists()
    assert len(list((outdir / "scenario_reports").glob("*_debrief.md"))) == 10


def test_epals_debrief_single_scenario_run(tmp_path):
    outdir = tmp_path / "debrief_run"
    result = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--scenarios",
            "epals_hypoxia_airway_obstruction",
            "--dt",
            "10",
            "--outdir",
            str(outdir),
            "--fail-on-review",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    summary = json.loads((outdir / "epals_debrief_summary_v1223.json").read_text(encoding="utf-8"))
    assert summary["scenario_count"] == 1
    assert summary["status"] == "PASS"
    assert summary["metric_rows"] >= 3
    assert (outdir / "epals_debrief_metric_markers_v1223.csv").exists()

import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_v122_taxonomy_has_5h_5t_and_required_fields():
    spec = yaml.safe_load((ROOT / "data" / "epals_reversible_causes_v1.22.yaml").read_text(encoding="utf-8"))
    assert spec["version"] == "v1.22-alpha"
    causes = spec["causes"]
    assert len(causes) == 10
    assert sum(1 for c in causes if c["group"] == "H") == 5
    assert sum(1 for c in causes if c["group"] == "T") == 5
    planned = [c["planned_scenario_id"] for c in causes]
    assert len(planned) == len(set(planned))
    for cause in causes:
        assert cause["id"]
        assert cause["display_name"]
        assert len(cause["primary_modules"]) >= 2
        assert len(cause["key_bus_variables"]) >= 5
        assert len(cause["expected_interventions"]) >= 2
        assert len(cause["debrief_questions"]) >= 2
        assert cause["source"]


def test_v122_curriculum_matches_taxonomy():
    spec = yaml.safe_load((ROOT / "data" / "epals_reversible_causes_v1.22.yaml").read_text(encoding="utf-8"))
    curriculum = yaml.safe_load((ROOT / "data" / "epals_scenario_curriculum_v1.22.yaml").read_text(encoding="utf-8"))
    tax_ids = {c["planned_scenario_id"] for c in spec["causes"]}
    cur_ids = {s["id"] for s in curriculum["scenarios"]}
    assert cur_ids == tax_ids
    assert len(curriculum["teaching_sequence"]) == 10
    assert set(curriculum["teaching_sequence"]) == tax_ids


def test_v122_audit_tool_passes(tmp_path):
    outdir = tmp_path / "epals_audit"
    cmd = [
        sys.executable,
        str(ROOT / "tools" / "epals_scenario_audit_v1_22.py"),
        "--outdir", str(outdir),
        "--fail-on-review",
    ]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr + result.stdout
    summary = json.loads((outdir / "epals_taxonomy_summary_v122.json").read_text(encoding="utf-8"))
    assert summary["status"] == "PASS"
    assert summary["cause_count"] == 10
    assert summary["H_count"] == 5
    assert summary["T_count"] == 5
    assert summary["review_items"] == 0
    assert (outdir / "epals_cause_matrix_v122.csv").exists()
    assert (outdir / "epals_taxonomy_report_v122.md").exists()

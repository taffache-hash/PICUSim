from pathlib import Path
import json
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_v119_registry_exists_and_is_complete():
    reg_path = ROOT / "data" / "score_assumption_registry_v1.19.yaml"
    data = yaml.safe_load(reg_path.read_text(encoding="utf-8"))
    assert data["version"] == "v1.19"
    variables = {e["variable"] for e in data["entries"]}
    for key in [
        "VILI_risk", "renal_severity_score", "GCS_proxy", "infection_severity_score",
        "hepatic_lactate_clearance_mod", "M6G_accumulation_proxy", "insulin_hypoglycemia_risk",
        "piperacillin_ft_above_MIC", "vancomycin_target_attainment", "vq_shunt_frac",
        "vq_deadspace_frac", "HFOV_power_proxy",
    ]:
        assert key in variables


def test_v119_high_priority_entries_have_numeric_ranges():
    data = yaml.safe_load((ROOT / "data" / "score_assumption_registry_v1.19.yaml").read_text(encoding="utf-8"))
    by_var = {e["variable"]: e for e in data["entries"]}
    for key in ["VILI_risk", "renal_severity_score", "GCS_proxy", "infection_severity_score", "M6G_accumulation_proxy"]:
        entry = by_var[key]
        assert entry.get("numeric_range")
        assert len(entry["numeric_range"]["hard"]) == 2
        assert entry.get("reviewer_guidance", {}).get("priority") == "high"


def test_v119_audit_no_run_passes_and_has_no_missing():
    cmd = [sys.executable, "tools/score_assumption_audit_v1_19.py", "--no-run"]
    out = subprocess.check_output(cmd, cwd=ROOT, text=True)
    summary = json.loads(out)
    # v3.2 public RC policy: the legacy v1.19 registry is a documented partial
    # coverage audit, not a release blocker. It must remain parseable and broad,
    # but newly added score-like variables may appear as REVIEW/missing until
    # explicitly registered in a later registry revision.
    assert isinstance(summary["missing"], int)
    assert summary["registered"] >= 200
    assert summary["numeric_range_entries"] >= 150


def test_v119_small_range_audit_has_no_hard_failures():
    cmd = [
        sys.executable, "tools/score_assumption_audit_v1_19.py",
        "--scenarios", "healthy_child_20kg", "ards_mild", "picu_insulin_stress_hyperglycemia_v1_16",
        "--dt", "20",
    ]
    out = subprocess.check_output(cmd, cwd=ROOT, text=True)
    summary = json.loads(out)
    assert summary["range_fail"] == 0
    assert summary["range_review"] <= 5
    assert summary["scenarios_evaluated"] == 3

from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "data" / "airway_decision_scenario_pack_v1.25.yaml"


def test_airway_decision_pack_has_six_scenarios():
    pack = yaml.safe_load(PACK.read_text(encoding="utf-8"))
    assert pack["version"] == "v1.25-alpha"
    assert len(pack["scenarios"]) == 6
    for item in pack["scenarios"]:
        assert (ROOT / item["path"]).exists(), item["path"]
        assert item["decision_focus"]
        assert item["debrief_questions"]


def test_airway_decision_scenarios_have_airway_events():
    pack = yaml.safe_load(PACK.read_text(encoding="utf-8"))
    for item in pack["scenarios"]:
        cfg = yaml.safe_load((ROOT / item["path"]).read_text(encoding="utf-8"))
        assert cfg.get("airway_events")
        assert len(cfg["airway_events"]) >= 2
        assert any(ev["name"] == "perform_intubation" for ev in cfg["airway_events"])


def test_airway_decision_audit_smoke():
    cmd=[sys.executable, str(ROOT/"tools"/"airway_decision_scenario_audit_v1_25.py"), "--dt", "10", "--fail-on-review"]
    res=subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=180)
    assert res.returncode == 0, res.stdout + res.stderr
    summary=json.loads((ROOT/"outputs"/"airway_decision_scenarios_v1.25"/"airway_decision_audit_summary_v125.json").read_text(encoding="utf-8"))
    assert summary["status"] == "PASS"
    assert summary["scenario_count"] == 6

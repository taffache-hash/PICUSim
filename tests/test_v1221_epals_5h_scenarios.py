import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = [
    "epals_hypoxia_airway_obstruction.yaml",
    "epals_hypovolemia_hemorrhagic_shock.yaml",
    "epals_acidosis_septic_shock.yaml",
    "epals_hyperkalemia_aki.yaml",
    "epals_hypothermia_rewarming.yaml",
]


def test_v1221_5h_scenarios_exist_and_match_taxonomy():
    taxonomy = yaml.safe_load((ROOT / "data" / "epals_reversible_causes_v1.22.yaml").read_text(encoding="utf-8"))
    planned = {c["planned_scenario_id"] for c in taxonomy["causes"] if c["group"] == "H"}
    assert planned == {Path(s).stem for s in SCENARIOS}
    for filename in SCENARIOS:
        p = ROOT / "scenarios" / filename
        assert p.exists(), filename
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        assert data["version"] == "v1.22.1-alpha"
        assert data["epals"]["group"] == "H"
        assert len(data.get("outputs", [])) >= 8
        assert len(data.get("debrief_questions", [])) >= 2
        assert data.get("simulation_time_s", 0) >= 300


def test_v1221_5h_audit_tool_passes(tmp_path):
    outdir = tmp_path / "epals_5h"
    cmd = [sys.executable, str(ROOT / "tools" / "epals_5h_scenario_audit_v1_22_1.py"), "--outdir", str(outdir), "--dt", "10", "--fail-on-review"]
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=180)
    assert res.returncode == 0, res.stderr + res.stdout
    summary = json.loads((outdir / "epals_5h_audit_summary_v1221.json").read_text(encoding="utf-8"))
    assert summary["status"] == "PASS"
    assert summary["scenario_count"] == 5
    assert summary["fail"] == 0
    assert summary["review"] == 0

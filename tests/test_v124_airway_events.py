from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_airway_event_spec_has_required_events():
    spec = yaml.safe_load((ROOT / "data" / "airway_events_v1.24.yaml").read_text(encoding="utf-8"))
    events = set(spec["events"])
    required = {
        "perform_intubation", "failed_intubation_attempt", "start_bag_mask_ventilation",
        "accidental_extubation", "planned_extubation", "laryngospasm",
        "aspiration_event", "airway_obstruction_event",
    }
    assert required <= events


def test_airway_event_scenarios_have_events():
    for rel in ["scenarios/airway_rsi_hypoxic_child_v1_24.yaml", "scenarios/airway_accidental_extubation_picu_v1_24.yaml"]:
        cfg = yaml.safe_load((ROOT / rel).read_text(encoding="utf-8"))
        assert cfg.get("airway_events")
        assert len(cfg["airway_events"]) >= 3


def test_airway_event_audit_smoke():
    cmd = [sys.executable, str(ROOT / "tools" / "airway_event_audit_v1_24.py"), "--dt", "10", "--fail-on-review"]
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert res.returncode == 0, res.stdout + res.stderr
    summary = json.loads((ROOT / "outputs" / "airway_events_v1.24" / "airway_event_audit_summary_v124.json").read_text(encoding="utf-8"))
    assert summary["status"] == "PASS"
    assert summary["scenario_count"] == 2

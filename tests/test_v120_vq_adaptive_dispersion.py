import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_v120_bus_fields_registered():
    text = (ROOT / "core" / "bus.py").read_text(encoding="utf-8")
    for key in [
        "vq_adaptive_sigma", "vq_ards_weight", "vq_obstruction_weight",
        "vq_shock_weight", "vq_neonatal_weight", "vq_pathology_driver",
        "vq_adaptive_revision",
    ]:
        assert key in text


def test_v120_gas_exchange_outputs_adaptive_fields():
    text = (ROOT / "modules" / "respiratory" / "gas_exchange.py").read_text(encoding="utf-8")
    assert "v1.20_adaptive_three_zone_vq" in text
    assert "_adaptive_vq_drivers" in text
    assert "vq_ards_sigma_gain" in text


def test_v120_audit_tool_passes():
    cmd = [
        sys.executable,
        "tools/vq_adaptive_dispersion_audit_v1_20.py",
        "--dt", "10",
        "--fail-on-review",
    ]
    out = subprocess.check_output(cmd, cwd=ROOT, text=True)
    summary = json.loads(out)
    assert summary["status"] == "PASS"
    assert summary["checks"] >= 8
    assert summary["review_items"] == 0


def test_v120_registry_mentions_adaptive_vq_fields():
    data = yaml.safe_load((ROOT / "data" / "score_assumption_registry_v1.19.yaml").read_text(encoding="utf-8"))
    variables = {e["variable"] for e in data["entries"]}
    for key in ["vq_adaptive_sigma", "vq_ards_weight", "vq_obstruction_weight", "vq_shock_weight", "vq_neonatal_weight"]:
        assert key in variables

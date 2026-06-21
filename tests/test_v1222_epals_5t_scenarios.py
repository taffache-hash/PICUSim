from pathlib import Path
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_epals_5t_pack_files_exist_and_load():
    pack = ROOT / "data" / "epals_5t_scenario_pack_v1.22.2.yaml"
    assert pack.exists()
    data = yaml.safe_load(pack.read_text(encoding="utf-8"))
    assert data["version"] == "v1.22.2-alpha"
    assert len(data["scenarios"]) == 5
    for item in data["scenarios"]:
        p = ROOT / item["file"]
        assert p.exists(), item
        scen = yaml.safe_load(p.read_text(encoding="utf-8"))
        assert scen["epals"]["group"] == "T"
        assert scen.get("clinical_narrative")
        assert len(scen.get("debrief_questions", [])) >= 2


def test_epals_5t_audit_passes():
    cmd = [sys.executable, str(ROOT / "tools" / "epals_5t_scenario_audit_v1_22_2.py"), "--dt", "10"]
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=180)
    assert res.returncode == 0, res.stdout + res.stderr

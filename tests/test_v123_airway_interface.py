from pathlib import Path
import subprocess
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def test_airway_interface_files_present():
    assert (ROOT / "modules" / "respiratory" / "airway_interface.py").exists()
    assert (ROOT / "scenarios" / "airway_unassisted_spontaneous_breathing_v1_23.yaml").exists()
    assert (ROOT / "tools" / "airway_interface_audit_v1_23.py").exists()


def test_airway_unassisted_smoke_outputs(tmp_path):
    out = tmp_path / "airway.csv"
    cmd = [sys.executable, str(ROOT / "run_simulation.py"), "--scenario", str(ROOT / "scenarios" / "airway_unassisted_spontaneous_breathing_v1_23.yaml"), "--dt", "2", "--no-plot", "--save-csv", str(out)]
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=90)
    assert res.returncode == 0, res.stderr[-1500:] + res.stdout[-1500:]
    df = pd.read_csv(out, index_col=0)
    final = df.iloc[-1]
    assert str(final["vent_mode"]).upper() == "NONE"
    assert str(final["airway_interface"]).upper() == "UNASSISTED"
    assert abs(float(final["Paw"])) <= 0.2
    assert abs(float(final["PEEP"])) <= 0.2
    assert float(final["Pmus"]) > 0.5
    assert float(final["Vt"]) > 20.0


def test_airway_interface_audit_passes():
    cmd = [sys.executable, str(ROOT / "tools" / "airway_interface_audit_v1_23.py"), "--dt", "2", "--fail-on-review"]
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert res.returncode == 0, res.stderr[-1500:] + res.stdout[-1500:]

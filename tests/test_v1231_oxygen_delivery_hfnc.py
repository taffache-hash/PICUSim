from pathlib import Path
import subprocess
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def _run_scenario(name: str, tmp_path: Path) -> pd.DataFrame:
    out = tmp_path / f"{name}.csv"
    cmd = [
        sys.executable, str(ROOT / "run_simulation.py"),
        "--scenario", str(ROOT / "scenarios" / f"{name}.yaml"),
        "--dt", "2", "--no-plot", "--save-csv", str(out),
    ]
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert res.returncode == 0, res.stderr[-1500:] + res.stdout[-1500:]
    return pd.read_csv(out, index_col=0)


def test_v1231_files_present():
    assert (ROOT / "data" / "oxygen_delivery_hfnc_spec_v1.23.1.yaml").exists()
    assert (ROOT / "docs" / "OXYGEN_DELIVERY_HFNC_v1.23.1.md").exists()
    assert (ROOT / "tools" / "oxygen_delivery_hfnc_audit_v1_23_1.py").exists()
    assert (ROOT / "scenarios" / "airway_low_flow_oxygen_v1_23_1.yaml").exists()
    assert (ROOT / "scenarios" / "airway_hfnc_bronchiolitis_v1_23_1.yaml").exists()


def test_low_flow_oxygen_non_pressurised(tmp_path):
    df = _run_scenario("airway_low_flow_oxygen_v1_23_1", tmp_path)
    final = df.iloc[-1]
    assert str(final["airway_interface"]).upper() == "LOW_FLOW_OXYGEN"
    assert str(final["oxygen_interface"]).upper() == "LOW_FLOW_OXYGEN"
    assert not bool(final["intubated"])
    assert not bool(final["ventilator_connected"])
    assert float(final["FiO2_delivered"]) > 0.21
    assert float(final["effective_external_PEEP_cmH2O"]) <= 0.2
    assert float(final["Paw"]) <= 0.2


def test_hfnc_bronchiolitis_outputs(tmp_path):
    df = _run_scenario("airway_hfnc_bronchiolitis_v1_23_1", tmp_path)
    final = df.iloc[-1]
    assert str(final["airway_interface"]).upper() == "HFNC"
    assert str(final["oxygen_interface"]).upper() == "HFNC"
    assert not bool(final["intubated"])
    assert not bool(final["ventilator_connected"])
    assert float(final["HFNC_flow_L_min"]) >= 18.0
    assert float(final["FiO2_delivered"]) > 0.30
    assert float(final["HFNC_distending_pressure_cmH2O"]) > 0.5
    assert float(final["HFNC_deadspace_washout"]) > 0.05
    assert 0.0 <= float(final["HFNC_failure_risk"]) <= 1.0


def test_oxygen_delivery_audit_passes():
    cmd = [sys.executable, str(ROOT / "tools" / "oxygen_delivery_hfnc_audit_v1_23_1.py"), "--dt", "2", "--fail-on-review"]
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=180)
    assert res.returncode == 0, res.stderr[-1500:] + res.stdout[-1500:]

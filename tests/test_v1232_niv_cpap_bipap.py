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
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=160)
    assert res.returncode == 0, res.stderr[-1500:] + res.stdout[-1500:]
    return pd.read_csv(out, index_col=0)


def test_v1232_files_present():
    assert (ROOT / "data" / "niv_cpap_bipap_spec_v1.23.2.yaml").exists()
    assert (ROOT / "docs" / "NIV_CPAP_BIPAP_v1.23.2.md").exists()
    assert (ROOT / "tools" / "niv_cpap_bipap_audit_v1_23_2.py").exists()
    assert (ROOT / "scenarios" / "airway_niv_cpap_bronchiolitis_v1_23_2.yaml").exists()
    assert (ROOT / "scenarios" / "airway_niv_bipap_hypercapnia_v1_23_2.yaml").exists()


def test_niv_cpap_outputs(tmp_path):
    df = _run_scenario("airway_niv_cpap_bronchiolitis_v1_23_2", tmp_path)
    final = df.iloc[-1]
    assert str(final["airway_interface"]).upper() == "NIV_CPAP"
    assert str(final["NIV_mode"]).upper() == "CPAP"
    assert not bool(final["intubated"])
    assert bool(final["ventilator_connected"])
    assert bool(final["airway_pressure_delivery_enabled"])
    assert float(final["NIV_delivered_PEEP_cmH2O"]) > 2.0
    assert float(final["NIV_delivered_PS_cmH2O"]) <= 0.5
    assert 0.0 <= float(final["NIV_failure_risk"]) <= 1.0


def test_niv_bipap_outputs(tmp_path):
    df = _run_scenario("airway_niv_bipap_hypercapnia_v1_23_2", tmp_path)
    final = df.iloc[-1]
    assert str(final["airway_interface"]).upper() == "NIV_BIPAP"
    assert str(final["NIV_mode"]).upper() == "BIPAP"
    assert not bool(final["intubated"])
    assert bool(final["ventilator_connected"])
    assert float(final["NIV_delivered_PEEP_cmH2O"]) > 2.0
    assert float(final["NIV_delivered_PS_cmH2O"]) > 2.0
    assert float(final["NIV_delivered_PIP_cmH2O"]) > float(final["NIV_delivered_PEEP_cmH2O"])
    assert float(final["NIV_deadspace_washout"]) > 0.02
    assert 0.0 <= float(final["NIV_failure_risk"]) <= 1.0


def test_niv_audit_passes():
    cmd = [sys.executable, str(ROOT / "tools" / "niv_cpap_bipap_audit_v1_23_2.py"), "--dt", "2", "--fail-on-review"]
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=240)
    assert res.returncode == 0, res.stderr[-1500:] + res.stdout[-1500:]

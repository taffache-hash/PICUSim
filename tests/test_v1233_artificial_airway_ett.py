from pathlib import Path
import subprocess
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

def run_scenario(name, tmp_path):
    out = tmp_path / (Path(name).stem + ".csv")
    subprocess.run([
        sys.executable, str(ROOT / "run_simulation.py"),
        "--scenario", name, "--dt", "10", "--no-plot", "--save-csv", str(out)
    ], cwd=str(ROOT), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return pd.read_csv(out)

def test_ett_tube_resistance_scenario(tmp_path):
    df = run_scenario("scenarios/airway_ett_tube_resistance_v1_23_3.yaml", tmp_path)
    final = df.iloc[-1]
    assert str(final["airway_interface"]).upper() == "ETT"
    assert bool(final["intubated"])
    assert int(final["artificial_airway_revision"]) == 1233
    assert final["tube_resistance_cmH2O_L_s"] > 0
    assert final["tube_dead_space_mL"] > 0
    assert 0 <= final["tube_VdVt_add"] <= 0.25

def test_ett_partial_obstruction_has_visible_resistance(tmp_path):
    df = run_scenario("scenarios/airway_ett_partial_obstruction_v1_23_3.yaml", tmp_path)
    final = df.iloc[-1]
    assert final["tube_obstruction_score"] >= 0.5
    assert final["tube_resistance_factor"] > 1.5
    assert final["airway_resistance_mod"] > 1.5
    assert 0 <= final["ETT_failure_risk"] <= 1.0


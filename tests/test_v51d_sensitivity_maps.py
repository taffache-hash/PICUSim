import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_sensitivity_maps_generate_expected_outputs():
    subprocess.run([sys.executable, str(ROOT / "tools" / "sensitivity_maps_v5_1D.py")], check=True, cwd=ROOT)
    out = ROOT / "outputs" / "sensitivity_maps_v5.1D"
    assert (out / "sensitivity_map_long_v51D.csv").exists()
    assert (out / "sensitivity_ranking_v51D.csv").exists()
    assert (out / "sensitivity_fragility_flags_v51D.csv").exists()
    assert (out / "sensitivity_summary_v51D.json").exists()
    assert (out / "sensitivity_report_v51D.md").exists()

    summary = json.loads((out / "sensitivity_summary_v51D.json").read_text())
    assert summary["status"] == "pass"
    assert summary["scenarios"] >= 5
    assert summary["parameters"] >= 6
    assert summary["outcomes"] >= 4
    assert summary["map_rows"] == summary["scenarios"] * summary["parameters"] * summary["outcomes"] * 7
    assert summary["ranking_rows"] == summary["scenarios"] * summary["parameters"] * summary["outcomes"]


def test_sensitivity_ranking_has_direction_and_dominance_columns():
    out = ROOT / "outputs" / "sensitivity_maps_v5.1D"
    if not (out / "sensitivity_ranking_v51D.csv").exists():
        subprocess.run([sys.executable, str(ROOT / "tools" / "sensitivity_maps_v5_1D.py")], check=True, cwd=ROOT)
    with (out / "sensitivity_ranking_v51D.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows
    assert {"scenario", "parameter", "outcome", "normalized_sensitivity", "direction", "dominant"}.issubset(rows[0])
    assert any(row["direction"] in {"positive", "negative"} for row in rows)

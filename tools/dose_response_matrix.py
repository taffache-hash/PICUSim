#!/usr/bin/env python3
"""Run a compact dose-response matrix for key PDT interventions (v0.28)."""
from __future__ import annotations
import argparse, copy, sys
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.simtools import load_yaml, scenario_path, run_config, summarize_dataframe, write_json  # noqa: E402

CASES = {
    "iNO_PVR": {"scenario": "pulmonary_hypertension_ino", "action": "set_ino_ppm", "doses": [0, 5, 10, 20], "metric": "PVR_final", "direction": "down"},
    "salbutamol_Rrs": {"scenario": "status_asthmaticus", "action": "set_salbutamol", "doses": [0, 0.08, 0.16, 0.24], "metric": "R_rs_final", "direction": "down"},
    "hypertonic_Na": {"scenario": "tbi_hypertonic_electrolytes", "action": "set_hypertonic_saline_3pct", "doses": [0, 25, 50, 100], "metric": "Na_mmol_L_final", "direction": "up"},
    "crrt_urea": {"scenario": "aki_crrt_lite", "action": "set_CRRT_effluent", "doses": [0, 15, 30, 45], "metric": "urea_mmol_L_final", "direction": "down"},
}


def run_case(name: str, spec: Dict[str, Any], dt: float) -> pd.DataFrame:
    base_cfg = load_yaml(scenario_path(spec["scenario"]))
    rows: List[Dict[str, Any]] = []
    for dose in spec["doses"]:
        cfg = copy.deepcopy(base_cfg)
        cfg.setdefault("perturbations", []).append({"t": 1, "action": spec["action"], "value": dose, "label": f"v0.28 dose-response {name}"})
        df = run_config(cfg, dt=dt, quiet=True)
        summ = summarize_dataframe(df)
        rows.append({"case": name, "scenario": spec["scenario"], "action": spec["action"], "dose": dose, "target_metric": spec["metric"], "direction": spec["direction"], **summ})
    return pd.DataFrame(rows)


def monotonic(values: list[float], direction: str) -> bool:
    pairs = zip(values, values[1:])
    if direction == "down":
        return all(b <= a + 1e-6 for a, b in pairs)
    return all(b >= a - 1e-6 for a, b in pairs)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", nargs="+", default=list(CASES.keys()))
    ap.add_argument("--dt", type=float, default=1.0)
    ap.add_argument("--outdir", default=str(ROOT / "outputs" / "validation_pack"))
    args = ap.parse_args()
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    frames = [run_case(c, CASES[c], args.dt) for c in args.cases]
    df = pd.concat(frames, ignore_index=True)
    df.to_csv(outdir / "dose_response_matrix.csv", index=False)
    checks = []
    for name, spec in CASES.items():
        if name not in args.cases:
            continue
        sub = df[df["case"] == name]
        metric = spec["metric"]
        vals = [float(v) for v in sub[metric].tolist() if metric in sub]
        checks.append({"case": name, "metric": metric, "direction": spec["direction"], "monotonic": monotonic(vals, spec["direction"]), "values": vals})
    write_json({"checks": checks}, outdir / "dose_response_summary.json")
    print(f"dose-response matrix written to {outdir}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

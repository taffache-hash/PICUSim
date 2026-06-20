#!/usr/bin/env python3
"""Expanded dose-response matrix for PDT v0.29.

The aim is not pharmacological calibration, but qualitative monotonic sanity
checks across clinically meaningful levers.
"""
from __future__ import annotations
import argparse, copy, sys
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.simtools import load_yaml, scenario_path, run_config, summarize_dataframe, write_json  # noqa: E402
from tools.dose_response_matrix import monotonic  # noqa: E402

CASES: Dict[str, Dict[str, Any]] = {
    'iNO_PVR': {'scenario': 'pulmonary_hypertension_ino', 'action': 'set_ino_ppm', 'doses': [0, 5, 10, 20], 'metric': 'PVR_final', 'direction': 'down'},
    'salbutamol_Rrs': {'scenario': 'status_asthmaticus', 'action': 'set_salbutamol', 'doses': [0, 0.08, 0.16, 0.24], 'metric': 'R_rs_final', 'direction': 'down'},
    'hypertonic_Na': {'scenario': 'tbi_hypertonic_electrolytes', 'action': 'set_hypertonic_saline_3pct', 'doses': [0, 25, 50, 100], 'metric': 'Na_mmol_L_final', 'direction': 'up'},
    'hypertonic_ICP': {'scenario': 'tbi_hypertonic_electrolytes', 'action': 'set_hypertonic_saline_3pct', 'doses': [0, 25, 50, 100], 'metric': 'ICP_mmHg_final', 'direction': 'down'},
    'crrt_urea': {'scenario': 'aki_crrt_lite', 'action': 'set_CRRT_effluent', 'doses': [0, 15, 30, 45], 'metric': 'urea_mmol_L_final', 'direction': 'down'},
    'crrt_K': {'scenario': 'aki_crrt_lite', 'action': 'set_CRRT_effluent', 'doses': [0, 15, 30, 45], 'metric': 'K_mmol_L_final', 'direction': 'down'},
    'GRC_Hb': {'scenario': 'hematology_anemia_transfusion', 'action': 'transfuse_GRC', 'doses': [0, 5, 10, 15], 'metric': 'Hb_final', 'direction': 'up'},
    'antibiotic_burden': {'scenario': 'infection_antibiotic_delay', 'action': 'set_antibiotic_coverage', 'doses': [0.15, 0.35, 0.65, 0.90], 'metric': 'microbial_burden_final', 'direction': 'down'},
}


def run_case(name: str, spec: Dict[str, Any], dt: float, max_time_s: float | None = None) -> pd.DataFrame:
    base_cfg = load_yaml(scenario_path(spec['scenario']))
    if max_time_s is not None:
        base_cfg['simulation_time_s'] = min(float(base_cfg.get('simulation_time_s', max_time_s)), float(max_time_s))
    rows: List[Dict[str, Any]] = []
    for dose in spec['doses']:
        cfg = copy.deepcopy(base_cfg)
        cfg.setdefault('perturbations', []).append({'t': 1, 'action': spec['action'], 'value': dose, 'label': f'v0.29 dose-response {name}'})
        df = run_config(cfg, dt=dt, quiet=True)
        summ = summarize_dataframe(df)
        rows.append({'case': name, 'scenario': spec['scenario'], 'action': spec['action'], 'dose': dose, 'target_metric': spec['metric'], 'direction': spec['direction'], **summ})
    return pd.DataFrame(rows)


def evaluate(cases: list[str], dt: float = 1.0, max_time_s: float | None = None) -> tuple[pd.DataFrame, list[dict]]:
    frames = [run_case(c, CASES[c], dt=dt, max_time_s=max_time_s) for c in cases]
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    checks = []
    for name in cases:
        spec = CASES[name]
        sub = df[df['case'] == name]
        metric = spec['metric']
        vals = [float(v) for v in sub[metric].tolist()] if metric in sub.columns else []
        checks.append({'case': name, 'metric': metric, 'direction': spec['direction'], 'monotonic': monotonic(vals, spec['direction']) if vals else False, 'values': vals})
    return df, checks


def write_md(checks: list[dict], path: Path) -> None:
    passed = sum(1 for c in checks if c.get('monotonic'))
    lines = ['# PDT v0.29 Deep Dose-Response Matrix', '', f'Passed **{passed}/{len(checks)}** monotonic checks.', '', '| Case | Metric | Direction | Values | Status |', '|---|---|---|---|---|']
    for c in checks:
        vals = ', '.join(f"{v:.3g}" for v in c.get('values', []))
        lines.append(f"| {c['case']} | {c['metric']} | {c['direction']} | {vals} | {'PASS' if c.get('monotonic') else 'REVIEW'} |")
    path.write_text('\n'.join(lines))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--cases', nargs='+', default=list(CASES.keys()))
    ap.add_argument('--dt', type=float, default=1.0)
    ap.add_argument('--max-time-s', type=float, default=None)
    ap.add_argument('--outdir', default=str(ROOT / 'outputs' / 'validation_pack'))
    ap.add_argument('--fail-on-error', action='store_true')
    args = ap.parse_args()
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    df, checks = evaluate(args.cases, args.dt, args.max_time_s)
    df.to_csv(outdir / 'dose_response_deep_matrix.csv', index=False)
    write_json({'checks': checks}, outdir / 'dose_response_deep_summary.json')
    write_md(checks, outdir / 'dose_response_deep_matrix.md')
    print(f'deep dose-response matrix written to {outdir}')
    if args.fail_on_error and not all(c.get('monotonic') for c in checks):
        return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""Batch sensitivity summary for selected PDT scenarios (v0.29)."""
from __future__ import annotations
import argparse, sys
from pathlib import Path
from typing import Dict, List, Any
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.simtools import infer_default_parameters, load_yaml, run_config, scenario_path, set_nested, summarize_dataframe, write_json  # noqa: E402

DEFAULT_SCENARIOS = ['ards_mild', 'septic_shock', 'status_asthmaticus', 'aki_crrt_lite', 'infection_antibiotic_delay']
DEFAULT_OUTCOMES = ['PaO2_final', 'PaCO2_final', 'MAP_final', 'lactate_final', 'VILI_risk_final', 'microbial_burden_final']


def one_scenario(scenario: str, dt: float, fraction: float, max_params: int) -> pd.DataFrame:
    cfg = load_yaml(scenario_path(scenario))
    specs = infer_default_parameters(cfg)
    params = list(specs.keys())[:max_params]
    base_df = run_config(cfg, dt=dt, quiet=True)
    base = summarize_dataframe(base_df)
    rows: List[Dict[str, Any]] = []
    for p in params:
        # skip absent or zeroish bases with no sd
        base_val = float(specs[p].get('base', 0.0))
        vals = [('down', base_val * (1 - fraction)), ('up', base_val * (1 + fraction))] if base_val else [('down', base_val - float(specs[p].get('sd', 0.05))), ('up', base_val + float(specs[p].get('sd', 0.05)))]
        for direction, val in vals:
            val = max(float(specs[p].get('min', -1e99)), min(float(specs[p].get('max', 1e99)), float(val)))
            mod = load_yaml(scenario_path(scenario))
            set_nested(mod, p, val)
            try:
                summ = summarize_dataframe(run_config(mod, dt=dt, quiet=True))
                row = {'scenario': scenario, 'parameter': p, 'direction': direction, 'baseline_value': base_val, 'value': val}
                for outcome in DEFAULT_OUTCOMES:
                    if outcome in base and outcome in summ:
                        row[f'delta_{outcome}'] = float(summ[outcome]) - float(base[outcome])
                rows.append(row)
            except Exception as exc:
                rows.append({'scenario': scenario, 'parameter': p, 'direction': direction, 'error': str(exc)})
    return pd.DataFrame(rows)


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    metric_cols = [c for c in df.columns if c.startswith('delta_')]
    rows = []
    for (scenario, param), sub in df.groupby(['scenario', 'parameter']):
        row = {'scenario': scenario, 'parameter': param}
        for c in metric_cols:
            vals = sub[c].dropna().abs()
            if len(vals):
                row[f'{c}_max_abs'] = float(vals.max())
        rows.append(row)
    return pd.DataFrame(rows)


def write_md(summary: pd.DataFrame, path: Path) -> None:
    lines = ['# PDT v0.29 Batch Sensitivity Summary', '', 'Top parameter effects by scenario. Values are absolute one-at-a-time changes from baseline.', '']
    for scenario, sub in summary.groupby('scenario'):
        lines += [f'## {scenario}', '', '| Parameter | Largest absolute delta |', '|---|---:|']
        score_cols = [c for c in sub.columns if c.endswith('_max_abs')]
        if not score_cols:
            lines.append('| none | 0 |')
            continue
        tmp = sub.copy(); tmp['score'] = tmp[score_cols].max(axis=1)
        for _, r in tmp.sort_values('score', ascending=False).head(10).iterrows():
            lines.append(f"| {r['parameter']} | {float(r['score']):.3g} |")
        lines.append('')
    path.write_text('\n'.join(lines))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--scenarios', nargs='+', default=DEFAULT_SCENARIOS)
    ap.add_argument('--dt', type=float, default=1.0)
    ap.add_argument('--fraction', type=float, default=0.20)
    ap.add_argument('--max-params', type=int, default=6)
    ap.add_argument('--outdir', default=str(ROOT / 'outputs' / 'validation_pack'))
    args = ap.parse_args()
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    frames = [one_scenario(s, args.dt, args.fraction, args.max_params) for s in args.scenarios]
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    summary = summarize(df) if len(df) else pd.DataFrame()
    df.to_csv(outdir / 'sensitivity_batch_results.csv', index=False)
    summary.to_csv(outdir / 'sensitivity_batch_summary.csv', index=False)
    write_md(summary, outdir / 'sensitivity_batch_summary.md')
    write_json({'scenarios': args.scenarios, 'runs': int(len(df)), 'parameters_per_scenario_max': args.max_params}, outdir / 'sensitivity_batch_metadata.json')
    print(f'batch sensitivity summary written to {outdir}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""Counterfactual/error-management report for PDT v0.42.

Compares baseline scenarios against harmful/excessive management scenarios.
This is an educational plausibility layer, not clinical validation.
"""
from __future__ import annotations
import argparse, json, math, sys
from pathlib import Path
from typing import Any, Dict
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.simtools import run_scenario


def stat_value(df: pd.DataFrame, variable: str, statistic: str) -> float:
    if variable not in df.columns:
        return float('nan')
    s = pd.to_numeric(df[variable], errors='coerce').dropna()
    if s.empty:
        return float('nan')
    if statistic == 'final': return float(s.iloc[-1])
    if statistic == 'max': return float(s.max())
    if statistic == 'min': return float(s.min())
    if statistic == 'mean': return float(s.mean())
    raise ValueError(f'Unsupported statistic: {statistic}')


def passes(base: float, cf: float, direction: str, min_delta: float) -> tuple[bool, float]:
    delta = cf - base
    if not (math.isfinite(base) and math.isfinite(cf)):
        return False, delta
    if direction == 'increase':
        return delta >= min_delta, delta
    if direction == 'decrease':
        return (-delta) >= min_delta, delta
    raise ValueError(f'Unsupported direction: {direction}')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--spec', default=str(ROOT/'data'/'counterfactual_specs_v0.42.yaml'))
    ap.add_argument('--dt', type=float, default=2.0)
    ap.add_argument('--outdir', default=str(ROOT/'outputs'/'validation_pack'))
    ap.add_argument('--ids', nargs='*', default=None)
    ap.add_argument('--fail-on-error', action='store_true')
    args = ap.parse_args()

    spec = yaml.safe_load(open(args.spec))
    checks = spec.get('checks', [])
    if args.ids:
        ids = set(args.ids)
        checks = [c for c in checks if c['id'] in ids]

    # cache scenario runs
    cache: Dict[str, pd.DataFrame] = {}
    rows = []
    for c in checks:
        for sname in (c['baseline'], c['counterfactual']):
            if sname not in cache:
                try:
                    _, df = run_scenario(sname, dt=args.dt)
                except Exception as e:
                    rows.append({
                        'id': c['id'], 'baseline': c['baseline'], 'counterfactual': c['counterfactual'],
                        'variable': c['variable'], 'statistic': c['statistic'], 'status': 'ERROR',
                        'error': f'{type(e).__name__}: {e}'
                    })
                    cache[sname] = None  # type: ignore
                else:
                    cache[sname] = df
        bdf = cache.get(c['baseline']); cdf = cache.get(c['counterfactual'])
        if bdf is None or cdf is None:
            continue
        b = stat_value(bdf, c['variable'], c['statistic'])
        v = stat_value(cdf, c['variable'], c['statistic'])
        ok, delta = passes(b, v, c['expected_direction'], float(c.get('min_delta', 0)))
        rows.append({
            'id': c['id'], 'baseline': c['baseline'], 'counterfactual': c['counterfactual'],
            'variable': c['variable'], 'statistic': c['statistic'], 'baseline_value': b,
            'counterfactual_value': v, 'delta': delta, 'expected_direction': c['expected_direction'],
            'min_delta': float(c.get('min_delta', 0)), 'status': 'PASS' if ok else 'REVIEW',
            'rationale': c.get('rationale', '')
        })

    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    csv_path = outdir/'counterfactual_report_v042.csv'
    md_path = outdir/'counterfactual_report_v042.md'
    js_path = outdir/'counterfactual_summary_v042.json'
    df.to_csv(csv_path, index=False)
    n_pass = int((df.get('status') == 'PASS').sum()) if not df.empty else 0
    n_review = int((df.get('status') == 'REVIEW').sum()) if not df.empty else 0
    n_error = int((df.get('status') == 'ERROR').sum()) if not df.empty else 0
    summary = {'version': spec.get('version'), 'dt': args.dt, 'checks': len(df), 'passed': n_pass, 'review': n_review, 'error': n_error}
    js_path.write_text(json.dumps(summary, indent=2))
    lines = ["# PDT v0.42 Counterfactual/Error-Management Report", "", f"dt: `{args.dt}`", "", f"Checks: {len(df)} | PASS: {n_pass} | REVIEW: {n_review} | ERROR: {n_error}", ""]
    if not df.empty:
        cols = ['id','variable','statistic','baseline_value','counterfactual_value','delta','expected_direction','min_delta','status']
        lines.append(df[cols].to_markdown(index=False))
    md_path.write_text('\n'.join(lines))
    print(json.dumps(summary, indent=2))
    return 1 if args.fail_on_error and (n_review or n_error) else 0

if __name__ == '__main__':
    raise SystemExit(main())

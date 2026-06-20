#!/usr/bin/env python3
"""Run acute-event demo scenarios and summarize pre/post event changes (PDT v0.43)."""
from __future__ import annotations
import argparse, json, sys, math
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.simtools import run_scenario

DEFAULT_DEMOS = [
    'acute_event_pneumothorax_tension',
    'acute_event_tube_obstruction_severe',
    'acute_event_acute_bleeding_moderate',
    'acute_event_seizure_severe',
    'acute_event_hypoglycemia_severe',
    'acute_event_sedative_bolus_hypotension',
]
WATCH = ['SaO2','PaCO2','pH_a','MAP','CO','C_rs','R_rs','Hb','lactate','T_core','glucose_mmol_L','GCS_proxy','seizure_risk_index','sedation_score','auto_PEEP_obstructive','RV_afterload_index']


def _mean_window(df: pd.DataFrame, t0: float, t1: float, key: str) -> float:
    if key not in df.columns:
        return float('nan')
    time = df['t'] if 't' in df.columns else df.index.to_series()
    sub = df[(time >= t0) & (time <= t1)]
    s = pd.to_numeric(sub[key], errors='coerce').dropna()
    if s.empty:
        return float('nan')
    return float(s.mean())


def event_time(cfg: Dict[str, Any]) -> float:
    evs = cfg.get('events', []) or []
    if not evs:
        return 0.0
    return float(evs[0].get('t', evs[0].get('time', 0.0)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--scenarios', nargs='*', default=DEFAULT_DEMOS)
    ap.add_argument('--dt', type=float, default=2.0)
    ap.add_argument('--window', type=float, default=40.0)
    ap.add_argument('--outdir', default=str(ROOT/'outputs'/'validation_pack'))
    ap.add_argument('--fail-on-error', action='store_true')
    args = ap.parse_args()
    rows: List[Dict[str, Any]] = []
    errors = []
    for name in args.scenarios:
        try:
            cfg, df = run_scenario(name, dt=args.dt)
            te = event_time(cfg)
            ev = (cfg.get('events') or [{}])[0]
            for key in WATCH:
                pre = _mean_window(df, max(0, te-args.window), max(0, te-args.dt), key)
                post = _mean_window(df, te+args.dt, te+args.window, key)
                if math.isfinite(pre) or math.isfinite(post):
                    rows.append({'scenario': name, 'event': ev.get('name'), 'severity': ev.get('severity'), 't_event': te, 'variable': key, 'pre_mean': pre, 'post_mean': post, 'delta': post-pre if math.isfinite(pre) and math.isfinite(post) else float('nan')})
        except Exception as e:
            errors.append({'scenario': name, 'error': f'{type(e).__name__}: {e}'})
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    dfout = pd.DataFrame(rows)
    csv_path = outdir/'acute_event_demo_report_v043.csv'
    md_path = outdir/'acute_event_demo_report_v043.md'
    js_path = outdir/'acute_event_demo_summary_v043.json'
    dfout.to_csv(csv_path, index=False)
    summary = {'version': 'v0.43', 'scenarios': len(args.scenarios), 'rows': len(rows), 'errors': len(errors), 'dt': args.dt, 'window_s': args.window}
    js_path.write_text(json.dumps({'summary': summary, 'errors': errors}, indent=2))
    lines = ['# PDT v0.43 Acute Event Demo Report','',f"dt: `{args.dt}` | window: `{args.window}` s",'',f"Scenarios: {len(args.scenarios)} | rows: {len(rows)} | errors: {len(errors)}",'']
    if errors:
        lines.append('## Errors')
        lines.append(pd.DataFrame(errors).to_markdown(index=False))
        lines.append('')
    if not dfout.empty:
        for sc, sub in dfout.groupby('scenario'):
            lines += [f'## {sc}', '']
            show = sub[['event','severity','variable','pre_mean','post_mean','delta']].copy()
            lines.append(show.to_markdown(index=False))
            lines.append('')
    md_path.write_text('\n'.join(lines))
    print(json.dumps(summary, indent=2))
    return 1 if args.fail_on_error and errors else 0

if __name__ == '__main__':
    raise SystemExit(main())

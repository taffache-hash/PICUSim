#!/usr/bin/env python3
"""Mass-balance report for PDT fluid/CRRT tracking (v0.29)."""
from __future__ import annotations
import argparse, sys
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.simtools import run_scenario, write_json  # noqa: E402

DEFAULT_SCENARIOS = ['acid_base_electrolyte_challenge', 'aki_crrt_lite', 'fluid_overload_diuretic_challenge', 'septic_shock', 'tbi_hypertonic_electrolytes']


def evaluate(scenarios: list[str], dt: float = 1.0, tolerance_abs: float = 50.0, tolerance_rel: float = 0.10) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for scen in scenarios:
        try:
            _, df = run_scenario(scen, dt=dt, quiet=True)
            final = df.iloc[-1]
            fb = float(final.get('fluid_balance', 0.0))
            err = abs(float(final.get('fluid_balance_error_mL', 0.0)))
            scale = max(abs(fb), 100.0)
            allowed = max(tolerance_abs, tolerance_rel * scale)
            rows.append({
                'scenario': scen,
                'fluid_balance_mL': fb,
                'cumulative_fluid_input_mL': float(final.get('cumulative_fluid_input_mL', 0.0)),
                'cumulative_urine_output_mL': float(final.get('cumulative_urine_output_mL', 0.0)),
                'cumulative_crrt_UF_mL': float(final.get('cumulative_crrt_UF_mL', 0.0)),
                'cumulative_insensible_loss_mL': float(final.get('cumulative_insensible_loss_mL', 0.0)),
                'fluid_balance_error_mL': err,
                'allowed_error_mL': allowed,
                'pass': err <= allowed,
            })
        except Exception as exc:
            rows.append({'scenario': scen, 'error': str(exc), 'pass': False})
    return pd.DataFrame(rows)


def write_md(df: pd.DataFrame, path: Path) -> None:
    total = len(df); passed = int(df.get('pass', pd.Series(dtype=bool)).sum()) if total else 0
    lines = ['# PDT v0.29 Mass-Balance Report', '', f'Passed **{passed}/{total}** scenario checks.', '',
             '| Scenario | Fluid balance | Input | Urine | CRRT UF | Insensible | Error | Allowed | Status |',
             '|---|---:|---:|---:|---:|---:|---:|---:|---|']
    for _, r in df.iterrows():
        if 'error' in r and isinstance(r.get('error'), str):
            lines.append(f"| {r.get('scenario')} | - | - | - | - | - | - | - | ERROR: {r.get('error')} |")
            continue
        status = 'PASS' if bool(r.get('pass')) else 'FAIL'
        lines.append(f"| {r['scenario']} | {r['fluid_balance_mL']:.1f} | {r['cumulative_fluid_input_mL']:.1f} | {r['cumulative_urine_output_mL']:.1f} | {r['cumulative_crrt_UF_mL']:.1f} | {r['cumulative_insensible_loss_mL']:.1f} | {r['fluid_balance_error_mL']:.1f} | {r['allowed_error_mL']:.1f} | {status} |")
    path.write_text('\n'.join(lines))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--scenarios', nargs='+', default=DEFAULT_SCENARIOS)
    ap.add_argument('--dt', type=float, default=1.0)
    ap.add_argument('--outdir', default=str(ROOT / 'outputs' / 'validation_pack'))
    ap.add_argument('--fail-on-error', action='store_true')
    args = ap.parse_args()
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    df = evaluate(args.scenarios, dt=args.dt)
    df.to_csv(outdir / 'mass_balance_report.csv', index=False)
    write_md(df, outdir / 'mass_balance_report.md')
    write_json({'checks': int(len(df)), 'passed': int(df.get('pass', pd.Series(dtype=bool)).sum())}, outdir / 'mass_balance_summary.json')
    print(f'mass-balance report written to {outdir}')
    if args.fail_on_error and not bool(df.get('pass', pd.Series([False])).all()):
        return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""Aggregate structured expert-review CSV sheets (v0.29)."""
from __future__ import annotations
import argparse, sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.simtools import write_json  # noqa: E402

REQUIRED_OPTIONAL = {'scenario', 'variable', 'clinical_rating', 'notes', 'final_judgement'}


def load_reviews(input_dir: Path) -> pd.DataFrame:
    frames = []
    for p in sorted(input_dir.glob('*.csv')):
        try:
            df = pd.read_csv(p)
            df['source_file'] = p.name
            frames.append(df)
        except Exception:
            continue
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def summarize(df: pd.DataFrame) -> dict:
    out = {'files_rows': int(len(df))}
    if len(df) == 0:
        return out
    if 'clinical_rating' in df:
        numeric = pd.to_numeric(df['clinical_rating'], errors='coerce')
        out['clinical_rating_mean'] = float(numeric.mean()) if numeric.notna().any() else None
        out['clinical_rating_n'] = int(numeric.notna().sum())
    if 'final_judgement' in df:
        out['final_judgement_counts'] = df['final_judgement'].dropna().astype(str).value_counts().to_dict()
    if 'scenario' in df:
        out['scenario_counts'] = df['scenario'].dropna().astype(str).value_counts().to_dict()
    return out


def write_template(path: Path) -> None:
    pd.DataFrame([{
        'reviewer': '', 'scenario': 'healthy_child_20kg', 'variable': 'MAP', 'simulated_value': '',
        'expected_range': '', 'clinical_rating': '', 'notes': '', 'final_judgement': ''
    }]).to_csv(path, index=False)


def write_md(summary: dict, path: Path) -> None:
    lines = ['# PDT v0.29 Expert Review Aggregation', '', f"Rows aggregated: **{summary.get('files_rows', 0)}**", '']
    if summary.get('clinical_rating_mean') is not None:
        lines.append(f"Mean clinical rating: **{summary['clinical_rating_mean']:.2f}** (n={summary.get('clinical_rating_n', 0)})")
        lines.append('')
    if summary.get('final_judgement_counts'):
        lines += ['## Final judgements', '']
        for k, v in summary['final_judgement_counts'].items():
            lines.append(f'- {k}: {v}')
    path.write_text('\n'.join(lines))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--input-dir', default=str(ROOT / 'outputs' / 'validation_pack' / 'expert_review_completed'))
    ap.add_argument('--outdir', default=str(ROOT / 'outputs' / 'validation_pack'))
    ap.add_argument('--write-template', action='store_true')
    args = ap.parse_args()
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    if args.write_template:
        write_template(outdir / 'expert_review_completed_template.csv')
    df = load_reviews(Path(args.input_dir))
    if len(df):
        df.to_csv(outdir / 'expert_review_aggregate_raw.csv', index=False)
    summary = summarize(df)
    write_json(summary, outdir / 'expert_review_aggregate_summary.json')
    write_md(summary, outdir / 'expert_review_aggregate_summary.md')
    print(f'expert review aggregation written to {outdir}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

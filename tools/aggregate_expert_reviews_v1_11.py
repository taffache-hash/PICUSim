#!/usr/bin/env python3
"""Aggregate PDT v1.11 structured expert-review CSVs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import pandas as pd

SCENARIO_SCORE_COLUMNS = [
    "physiologic_plausibility_1_5", "trajectory_plausibility_1_5",
    "intervention_response_1_5", "educational_usefulness_1_5",
    "safety_misinterpretation_risk_1_5", "transparency_of_assumptions_1_5",
]
MODULE_SCORE_COLUMNS = [
    "formulation_transparency_1_5", "face_validity_1_5", "educational_value_1_5",
]


def load_csvs(input_dir: Path, kind: str) -> pd.DataFrame:
    frames: List[pd.DataFrame] = []
    patterns = {
        "scenario": ["*scenario*review*.csv", "scenario_review_completed*.csv"],
        "module": ["*module*review*.csv", "module_review_completed*.csv"],
        "reviewer": ["*reviewer*metadata*.csv"],
    }.get(kind, ["*.csv"])
    seen = set()
    for pat in patterns:
        for path in sorted(input_dir.glob(pat)):
            if path in seen:
                continue
            seen.add(path)
            try:
                df = pd.read_csv(path)
                if len(df) == 0:
                    continue
                df["source_file"] = path.name
                frames.append(df)
            except Exception:
                continue
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def yes_count(series: pd.Series) -> int:
    if series is None or len(series) == 0:
        return 0
    return int(series.fillna("").astype(str).str.strip().str.lower().isin({"yes", "y", "true", "1", "si", "sì"}).sum())


def numericize(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def summarize_scenarios(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "scenario" not in df.columns:
        return pd.DataFrame()
    df = numericize(df, SCENARIO_SCORE_COLUMNS)
    rows: List[Dict[str, object]] = []
    for scenario, sub in df.groupby("scenario", dropna=False):
        row: Dict[str, object] = {"scenario": scenario, "review_rows": int(len(sub))}
        for col in SCENARIO_SCORE_COLUMNS:
            if col in sub.columns:
                row[f"{col}_mean"] = float(sub[col].mean()) if sub[col].notna().any() else None
                row[f"{col}_n"] = int(sub[col].notna().sum())
        if "major_implausibility_yes_no" in sub.columns:
            row["major_implausibility_flags"] = yes_count(sub["major_implausibility_yes_no"])
        else:
            row["major_implausibility_flags"] = 0
        if "recommended_action_accept_minor_major_reject" in sub.columns:
            counts = sub["recommended_action_accept_minor_major_reject"].fillna("").astype(str).str.lower().value_counts().to_dict()
            row["recommendation_counts_json"] = json.dumps(counts, sort_keys=True)
        phys = row.get("physiologic_plausibility_1_5_mean")
        edu = row.get("educational_usefulness_1_5_mean")
        safety = row.get("safety_misinterpretation_risk_1_5_mean")
        triage = []
        if isinstance(phys, float) and phys < 3.0:
            triage.append("low_physiologic_plausibility")
        if isinstance(edu, float) and edu < 3.0:
            triage.append("low_educational_usefulness")
        if isinstance(safety, float) and safety >= 4.0:
            triage.append("high_safety_misinterpretation_risk")
        if row["major_implausibility_flags"]:
            triage.append("major_implausibility_flag")
        row["triage_status"] = "REVIEW" if triage else "PASS"
        row["triage_reasons"] = ";".join(triage)
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_modules(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "module" not in df.columns:
        return pd.DataFrame()
    df = numericize(df, MODULE_SCORE_COLUMNS)
    rows: List[Dict[str, object]] = []
    for module, sub in df.groupby("module", dropna=False):
        row: Dict[str, object] = {"module": module, "review_rows": int(len(sub))}
        for col in MODULE_SCORE_COLUMNS:
            if col in sub.columns:
                row[f"{col}_mean"] = float(sub[col].mean()) if sub[col].notna().any() else None
                row[f"{col}_n"] = int(sub[col].notna().sum())
        if "missing_feature_priority_low_medium_high" in sub.columns:
            row["missing_feature_priority_counts_json"] = json.dumps(sub["missing_feature_priority_low_medium_high"].fillna("").astype(str).str.lower().value_counts().to_dict(), sort_keys=True)
        if "recommended_action_accept_minor_major_reject" in sub.columns:
            row["recommendation_counts_json"] = json.dumps(sub["recommended_action_accept_minor_major_reject"].fillna("").astype(str).str.lower().value_counts().to_dict(), sort_keys=True)
        rows.append(row)
    return pd.DataFrame(rows)


def write_decision_matrix(scen_df: pd.DataFrame, mod_df: pd.DataFrame, outpath: Path) -> None:
    lines = ["# Expert Review Aggregation — Decision Matrix", ""]
    if scen_df.empty:
        lines += ["No scenario review rows were found.", ""]
    else:
        lines += ["## Scenario triage", "", "| Scenario | Rows | Status | Reasons |", "|---|---:|---|---|"]
        for _, r in scen_df.iterrows():
            lines.append(f"| {r.get('scenario','')} | {int(r.get('review_rows',0))} | {r.get('triage_status','')} | {r.get('triage_reasons','')} |")
        lines.append("")
    if not mod_df.empty:
        lines += ["## Module review coverage", "", "| Module | Rows |", "|---|---:|"]
        for _, r in mod_df.iterrows():
            lines.append(f"| {r.get('module','')} | {int(r.get('review_rows',0))} |")
        lines.append("")
    lines += ["## Interpretation", "", "This aggregation supports face-validity and transparency reporting. It is not clinical validation."]
    outpath.write_text("\n".join(lines))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default="outputs/expert_review_v1.11/completed_reviews")
    ap.add_argument("--outdir", default="outputs/expert_review_v1.11/aggregation")
    args = ap.parse_args()
    input_dir = Path(args.input_dir)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    scen_raw = load_csvs(input_dir, "scenario")
    mod_raw = load_csvs(input_dir, "module")
    reviewer_raw = load_csvs(input_dir, "reviewer")
    if not scen_raw.empty:
        scen_raw.to_csv(outdir / "scenario_reviews_raw.csv", index=False)
    if not mod_raw.empty:
        mod_raw.to_csv(outdir / "module_reviews_raw.csv", index=False)
    if not reviewer_raw.empty:
        reviewer_raw.to_csv(outdir / "reviewer_metadata_raw.csv", index=False)

    scen_summary = summarize_scenarios(scen_raw)
    mod_summary = summarize_modules(mod_raw)
    scen_summary.to_csv(outdir / "scenario_review_summary.csv", index=False)
    mod_summary.to_csv(outdir / "module_review_summary.csv", index=False)

    summary = {
        "scenario_review_rows": int(len(scen_raw)),
        "module_review_rows": int(len(mod_raw)),
        "reviewer_metadata_rows": int(len(reviewer_raw)),
        "scenario_count": int(scen_summary["scenario"].nunique()) if not scen_summary.empty and "scenario" in scen_summary else 0,
        "module_count": int(mod_summary["module"].nunique()) if not mod_summary.empty and "module" in mod_summary else 0,
        "scenario_review_flags": int((scen_summary.get("triage_status", pd.Series(dtype=str)) == "REVIEW").sum()) if not scen_summary.empty else 0,
        "status": "PASS",
    }
    (outdir / "expert_review_aggregation_summary.json").write_text(json.dumps(summary, indent=2))
    write_decision_matrix(scen_summary, mod_summary, outdir / "expert_review_decision_matrix.md")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

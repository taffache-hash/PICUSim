#!/usr/bin/env python3
"""
v0.47 Output profile exporter.

Separates clinical/educational, validation and research/debug views of the same
simulation dataframe. This is an output governance layer only: it does not
modify physiology or scenario execution.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.simtools import run_scenario, scenario_path  # noqa: E402

DEFAULT_SPEC = ROOT / "data" / "output_profiles_v0.47.yaml"
DEFAULT_OUTDIR = ROOT / "outputs" / "validation_pack"


def load_spec(path: Path = DEFAULT_SPEC) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def patient_weight_from_config(config: Dict[str, Any]) -> float:
    return max(0.1, safe_float((config.get("patient") or {}).get("weight_kg", 20.0), 20.0))


def add_derived_columns(df: pd.DataFrame, config: Dict[str, Any], derived: Iterable[str]) -> pd.DataFrame:
    out = df.copy()
    weight = patient_weight_from_config(config)
    derived_set = set(derived or [])
    if "Vt_mL_kg" in derived_set and "Vt" in out.columns:
        out["Vt_mL_kg"] = out["Vt"].astype(float) / weight
    if "urine_output_mL_kg_h" in derived_set and "urine_rate_mL_h" in out.columns:
        out["urine_output_mL_kg_h"] = out["urine_rate_mL_h"].astype(float) / weight
    if "shock_index_proxy" in derived_set and "HR" in out.columns and "MAP" in out.columns:
        denom = out["MAP"].astype(float).clip(lower=1.0)
        out["shock_index_proxy"] = out["HR"].astype(float) / denom
    return out


def select_columns(df: pd.DataFrame, profile_spec: Dict[str, Any]) -> Tuple[pd.DataFrame, List[str], List[str]]:
    required = list(profile_spec.get("include_required") or [])
    optional = list(profile_spec.get("include_optional") or [])
    include_all = bool(profile_spec.get("include_all", False))
    if include_all:
        cols = list(df.columns)
    else:
        requested = []
        for c in required + optional:
            if c not in requested:
                requested.append(c)
        cols = [c for c in requested if c in df.columns]
    missing_required = [c for c in required if c not in df.columns]
    missing_optional = [c for c in optional if c not in df.columns]
    # Always keep time first when available.
    if "t" in df.columns and "t" not in cols:
        cols = ["t"] + cols
    return df[cols].copy(), missing_required, missing_optional


def sanitize_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_")


def final_value(row: pd.Series, col: str) -> str:
    try:
        val = row[col]
    except Exception:
        return ""
    if isinstance(val, float):
        return f"{val:.4g}"
    return str(val)


def write_profile_outputs(
    scenario: str,
    profile: str,
    filtered: pd.DataFrame,
    config: Dict[str, Any],
    outdir: Path,
    units: Dict[str, str],
    missing_required: List[str],
    missing_optional: List[str],
) -> Dict[str, Any]:
    outdir.mkdir(parents=True, exist_ok=True)
    stem = f"output_profile_v047_{sanitize_name(profile)}_{sanitize_name(scenario)}"
    csv_path = outdir / f"{stem}.csv"
    md_path = outdir / f"{stem}.md"
    filtered.to_csv(csv_path, index=False)

    final = filtered.iloc[-1] if len(filtered) else pd.Series(dtype=object)
    lines = [
        f"# v0.47 output profile export: `{profile}` / `{scenario}`",
        "",
        "This report is a filtered view of the simulation dataframe. It does not change model physiology.",
        "",
        "## Scenario",
        f"- name: {config.get('name', scenario)}",
        f"- weight_kg: {(config.get('patient') or {}).get('weight_kg', '')}",
        f"- age_y: {(config.get('patient') or {}).get('age_y', '')}",
        "",
        "## Final values",
        "| variable | final | unit |",
        "|---|---:|---|",
    ]
    for col in filtered.columns:
        if col == "t":
            continue
        lines.append(f"| `{col}` | {final_value(final, col)} | {units.get(col, '')} |")
    lines += ["", "## Missing requested variables"]
    if missing_required:
        lines.append("- Missing required: " + ", ".join(f"`{c}`" for c in missing_required))
    else:
        lines.append("- Missing required: none")
    if missing_optional:
        lines.append("- Missing optional: " + ", ".join(f"`{c}`" for c in missing_optional))
    else:
        lines.append("- Missing optional: none")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "scenario": scenario,
        "profile": profile,
        "columns_exported": int(len(filtered.columns)),
        "rows_exported": int(len(filtered)),
        "csv": str(csv_path),
        "report": str(md_path),
        "missing_required": missing_required,
        "missing_optional": missing_optional,
        "status": "REVIEW" if missing_required else "PASS",
    }


def combined_report(rows: List[Dict[str, Any]], outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    csv_path = outdir / "output_profile_v047_summary.csv"
    json_path = outdir / "output_profile_v047_summary.json"
    md_path = outdir / "output_profile_v047_report.md"
    if rows:
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            fieldnames = ["scenario", "profile", "status", "columns_exported", "rows_exported", "missing_required", "missing_optional", "csv", "report"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in rows:
                rr = dict(r)
                rr["missing_required"] = ";".join(rr.get("missing_required") or [])
                rr["missing_optional"] = ";".join(rr.get("missing_optional") or [])
                writer.writerow({k: rr.get(k, "") for k in fieldnames})
    status = "PASS" if all(r.get("status") == "PASS" for r in rows) else "REVIEW"
    payload = {
        "version": "v0.47",
        "status": status,
        "exports": rows,
        "n_exports": len(rows),
        "n_review": sum(1 for r in rows if r.get("status") != "PASS"),
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    lines = [
        "# v0.47 clinical/research output profile exports",
        "",
        f"Overall status: **{status}**",
        "",
        "| scenario | profile | status | columns | missing required |",
        "|---|---|---:|---:|---|",
    ]
    for r in rows:
        missing = ", ".join(f"`{m}`" for m in (r.get("missing_required") or [])) or "none"
        lines.append(f"| `{r['scenario']}` | `{r['profile']}` | {r['status']} | {r['columns_exported']} | {missing} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Export filtered v0.47 output profiles.")
    p.add_argument("--profiles", nargs="+", default=["clinical_educational"], help="Profile name(s) to export")
    p.add_argument("--scenarios", nargs="+", default=["healthy_child_20kg"], help="Scenario names or paths")
    p.add_argument("--dt", type=float, default=1.0)
    p.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    p.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    p.add_argument("--list-profiles", action="store_true")
    p.add_argument("--fail-on-missing-required", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    spec = load_spec(args.spec)
    profiles = spec.get("profiles") or {}
    units = spec.get("units") or {}
    if args.list_profiles:
        for name, pspec in profiles.items():
            print(f"{name}: {pspec.get('description', '')}")
        return 0
    rows: List[Dict[str, Any]] = []
    had_review = False
    for profile in args.profiles:
        if profile not in profiles:
            raise SystemExit(f"Unknown profile: {profile}. Available: {', '.join(sorted(profiles))}")
        pspec = profiles[profile]
        for scen in args.scenarios:
            config, df = run_scenario(scen, dt=args.dt, quiet=True)
            if df.index.name == "t":
                df = df.reset_index()
            elif "t" not in df.columns:
                df = df.copy()
                df.insert(0, "t", range(len(df)))
            df = add_derived_columns(df, config, pspec.get("derived") or [])
            filtered, missing_required, missing_optional = select_columns(df, pspec)
            scen_name = Path(scenario_path(scen)).stem
            row = write_profile_outputs(
                scen_name, profile, filtered, config, args.outdir, units, missing_required, missing_optional
            )
            rows.append(row)
            if missing_required:
                had_review = True
    combined_report(rows, args.outdir)
    if args.fail_on_missing_required and had_review:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

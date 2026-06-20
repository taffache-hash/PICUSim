#!/usr/bin/env python3
"""Generate heuristic causal traceability reports for key PDT outputs (v0.40).

The trace is intentionally explicit and auditable. It is not a formal causal
inference model and not a mechanistic proof of mass/energy balance; it exposes
which internal modifiers and state variables materially contributed to a final
bedside value.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, Mapping

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.simtools import run_scenario  # noqa: E402

DEFAULT_SPEC = ROOT / "data" / "causal_trace_specs_v0.40.yaml"
DEFAULT_OUT = ROOT / "outputs" / "validation_pack"


def _safe_env(row: Mapping[str, Any]) -> Dict[str, float]:
    env: Dict[str, float] = {}
    for k, v in row.items():
        try:
            val = float(v)
            if math.isfinite(val):
                env[k] = val
        except Exception:
            continue
    # Defaults for common optional fields so expressions stay robust across scenarios.
    defaults = {
        "RR_total": env.get("RR", 20.0), "CRRT_active_effective": 0.0,
        "CRRT_lactate_target_mmol_L": env.get("lactate", 1.0),
        "CRRT_HCO3_target_mmol_L": env.get("HCO3_mmol_L", 24.0),
        "CRRT_K_target_mmol_L": env.get("K_mmol_L", 4.0),
        "external_fluid_input_mL": 0.0, "cumulative_fluid_input_mL": 0.0,
        "cumulative_urine_output_mL": 0.0, "cumulative_crrt_UF_mL": 0.0,
        "cumulative_insensible_loss_mL": 0.0, "weight_kg": 20.0,
        "Pplat": env.get("Ppeak", env.get("Paw", 20.0)),
        "norad_mcg_kg_min": 0.0, "adrenaline_mcg_kg_min": 0.0,
        "vasopressin_mU_kg_min": 0.0, "RASS_proxy": 0.0,
    }
    for k, v in defaults.items():
        env.setdefault(k, float(v))
    return env


def _eval_expr(expr: str, env: Mapping[str, float]) -> float:
    safe_globals = {"__builtins__": {}, "max": max, "min": min, "abs": abs, "math": math}
    try:
        val = eval(expr, safe_globals, dict(env))  # noqa: S307 - internal controlled YAML expressions
        val = float(val)
        if not math.isfinite(val):
            return 0.0
        return val
    except Exception:
        return 0.0


def trace_dataframe(df: pd.DataFrame, spec: Mapping[str, Any], scenario: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()
    first = _safe_env(df.iloc[0].to_dict())
    final = _safe_env(df.iloc[-1].to_dict())
    rows = []
    summary = []
    for target, tspec in spec.get("targets", {}).items():
        value_key = tspec.get("value_key", target)
        initial_value = first.get(value_key, None)
        final_value = final.get(value_key, None)
        if final_value is None:
            continue
        signed_scores = []
        for c in tspec.get("contributors", []):
            raw = _eval_expr(str(c.get("expr", "0")), final)
            sign = str(c.get("sign", "positive"))
            signed = -abs(raw) if sign == "negative" else abs(raw)
            signed_scores.append(signed)
            rows.append({
                "scenario": scenario,
                "target": target,
                "value_key": value_key,
                "initial_value": initial_value,
                "final_value": final_value,
                "unit": tspec.get("unit", ""),
                "contributor": c.get("name", "unknown"),
                "sign": sign,
                "raw_score": raw,
                "signed_score": signed,
                "rationale": c.get("rationale", ""),
                "interpretation": tspec.get("interpretation", ""),
            })
        denom = sum(abs(x) for x in signed_scores) or 1.0
        # fill normalized share after rows are appended
        for r in rows[-len(signed_scores):]:
            r["absolute_share"] = abs(r["signed_score"]) / denom
        summary.append({
            "scenario": scenario,
            "target": target,
            "value_key": value_key,
            "initial_value": initial_value,
            "final_value": final_value,
            "delta": None if initial_value is None else final_value - initial_value,
            "unit": tspec.get("unit", ""),
            "n_contributors": len(signed_scores),
            "positive_pressure": sum(x for x in signed_scores if x > 0),
            "negative_pressure": sum(x for x in signed_scores if x < 0),
            "interpretation": tspec.get("interpretation", ""),
        })
    return pd.DataFrame(rows), pd.DataFrame(summary)


def write_markdown(rows: pd.DataFrame, summary: pd.DataFrame, path: Path) -> None:
    lines = [
        "# PDT v0.40 causal traceability report",
        "",
        "This report is a heuristic trace of model contributors. It is not formal causal inference, not external validation, and not a clinical explanation tool.",
        "",
    ]
    if summary.empty:
        lines.append("No trace rows generated.")
        path.write_text("\n".join(lines))
        return
    for scenario in summary["scenario"].drop_duplicates():
        lines += [f"## {scenario}", ""]
        ssum = summary[summary["scenario"] == scenario]
        for _, s in ssum.iterrows():
            lines.append(f"### {s['target']} = {s['final_value']:.3g} {s['unit']}")
            if pd.notna(s.get("initial_value")):
                lines.append(f"Initial: {s['initial_value']:.3g}; delta: {s['delta']:.3g}.")
            lines.append(str(s.get("interpretation", "")))
            sub = rows[(rows["scenario"] == scenario) & (rows["target"] == s["target"])].copy()
            sub = sub.sort_values("absolute_share", ascending=False)
            lines += ["", "| Contributor | Sign | Raw score | Share | Rationale |", "|---|---:|---:|---:|---|"]
            for _, r in sub.iterrows():
                lines.append(f"| {r['contributor']} | {r['sign']} | {r['raw_score']:.3g} | {100*r['absolute_share']:.1f}% | {r['rationale']} |")
            lines.append("")
    path.write_text("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default=str(DEFAULT_SPEC))
    ap.add_argument("--scenarios", nargs="+", default=["septic_shock", "ards_mild", "tbi_icp", "aki_crrt_lite"])
    ap.add_argument("--targets", nargs="*", default=None)
    ap.add_argument("--dt", type=float, default=1.0)
    ap.add_argument("--outdir", default=str(DEFAULT_OUT))
    args = ap.parse_args(argv)

    spec = yaml.safe_load(Path(args.spec).read_text())
    if args.targets:
        spec = dict(spec)
        spec["targets"] = {k: v for k, v in spec.get("targets", {}).items() if k in set(args.targets)}
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    all_rows = []
    all_summary = []
    failures = []
    for scenario in args.scenarios:
        try:
            _, df = run_scenario(scenario, dt=args.dt, quiet=True)
            rows, summary = trace_dataframe(df, spec, scenario)
            all_rows.append(rows)
            all_summary.append(summary)
        except Exception as exc:  # keep report generation robust
            failures.append({"scenario": scenario, "error": str(exc)})
    rows_df = pd.concat(all_rows, ignore_index=True) if all_rows else pd.DataFrame()
    summary_df = pd.concat(all_summary, ignore_index=True) if all_summary else pd.DataFrame()

    rows_path = outdir / "causal_trace_v040_rows.csv"
    summary_path = outdir / "causal_trace_v040_summary.csv"
    md_path = outdir / "causal_trace_v040_report.md"
    json_path = outdir / "causal_trace_v040_summary.json"
    rows_df.to_csv(rows_path, index=False)
    summary_df.to_csv(summary_path, index=False)
    write_markdown(rows_df, summary_df, md_path)
    payload = {
        "version": spec.get("version", "0.40"),
        "scenarios": args.scenarios,
        "dt": args.dt,
        "targets": list(spec.get("targets", {}).keys()),
        "n_rows": int(len(rows_df)),
        "n_target_summaries": int(len(summary_df)),
        "failures": failures,
    }
    json_path.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {rows_path}")
    print(f"Wrote {summary_path}")
    print(f"Wrote {md_path}")
    if failures:
        print(f"WARNING: {len(failures)} scenario(s) failed; see JSON summary")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

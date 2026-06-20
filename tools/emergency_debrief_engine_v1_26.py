#!/usr/bin/env python3
"""Airway/emergency debrief engine v1.26.

This tool runs airway decision scenarios and produces instructor-facing debrief
artifacts.  It computes timing and burden metrics such as SpO2 nadir, time below
thresholds, rescue ventilation timing, intubation timing, failed attempts and
reoxygenation timing.

Educational/research alpha only.  Not for clinical use.  Not a medical device.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
AIRWAY_PACK = ROOT / "data" / "airway_decision_scenario_pack_v1.25.yaml"
EPALS_PACKS = [
    ROOT / "data" / "epals_5h_scenario_pack_v1.22.1.yaml",
    ROOT / "data" / "epals_5t_scenario_pack_v1.22.2.yaml",
]


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text()) or {}


def _boolish(x: Any) -> bool:
    return str(x).strip().lower() in {"true", "1", "yes"}


def _safe_float(x: Any, default: float = math.nan) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _col(df: pd.DataFrame, name: str, default: float = math.nan) -> pd.Series:
    if name in df.columns:
        return pd.to_numeric(df[name], errors="coerce")
    return pd.Series([default] * len(df), index=df.index)


def _time_deltas(df: pd.DataFrame) -> pd.Series:
    t = _col(df, "t").astype(float)
    if len(t) <= 1:
        return pd.Series([0.0] * len(df), index=df.index)
    next_t = t.shift(-1)
    deltas = (next_t - t).fillna(0.0)
    return deltas.clip(lower=0.0)


def _time_below(df: pd.DataFrame, var: str, thr: float) -> float:
    if var not in df.columns:
        return math.nan
    return float((_time_deltas(df) * (_col(df, var) < thr)).sum())


def _time_above(df: pd.DataFrame, var: str, thr: float) -> float:
    if var not in df.columns:
        return math.nan
    return float((_time_deltas(df) * (_col(df, var) > thr)).sum())


def _time_at_min(df: pd.DataFrame, var: str) -> float:
    if var not in df.columns or df.empty:
        return math.nan
    y = _col(df, var)
    if y.dropna().empty:
        return math.nan
    idx = int(y.idxmin())
    return float(df.loc[idx, "t"])


def _time_at_max(df: pd.DataFrame, var: str) -> float:
    if var not in df.columns or df.empty:
        return math.nan
    y = _col(df, var)
    if y.dropna().empty:
        return math.nan
    idx = int(y.idxmax())
    return float(df.loc[idx, "t"])


def _first_time(df: pd.DataFrame, mask: Iterable[bool]) -> float:
    m = pd.Series(list(mask), index=df.index).fillna(False)
    if not bool(m.any()):
        return -1.0
    idx = int(m[m].index[0])
    return float(df.loc[idx, "t"])


def _first_time_col_equals(df: pd.DataFrame, col: str, value: str) -> float:
    if col not in df.columns:
        return -1.0
    return _first_time(df, df[col].astype(str) == value)


def _first_time_col_bool(df: pd.DataFrame, col: str) -> float:
    if col not in df.columns:
        return -1.0
    return _first_time(df, df[col].map(_boolish))


def _first_reoxygenation_after(df: pd.DataFrame, start_time: float, threshold: float = 0.90) -> float:
    if start_time < 0 or "SaO2" not in df.columns:
        return -1.0
    subset = df[df["t"] >= start_time]
    if subset.empty:
        return -1.0
    mask = pd.to_numeric(subset["SaO2"], errors="coerce") >= threshold
    if not bool(mask.any()):
        return -1.0
    idx = int(mask[mask].index[0])
    return float(df.loc[idx, "t"])


def _collect_airway_scenarios(selected: set[str] | None = None) -> list[dict[str, Any]]:
    pack = _load_yaml(AIRWAY_PACK)
    rows: list[dict[str, Any]] = []
    for item in pack.get("scenarios", []):
        sid = str(item["id"])
        if selected and sid not in selected:
            continue
        path = ROOT / str(item["path"])
        rows.append({
            "id": sid,
            "path": str(path.relative_to(ROOT)),
            "group": "airway_decision",
            "focus": item.get("decision_focus", []),
            "critical_events": item.get("critical_events", []),
            "debrief_questions": item.get("debrief_questions", []),
            "expected_final_state": item.get("expected_final_state", ""),
        })
    return rows


def _collect_epals_scenarios(selected: set[str] | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pack_path in EPALS_PACKS:
        pack = _load_yaml(pack_path)
        for item in pack.get("scenarios", []):
            sid = str(item["id"])
            if selected and sid not in selected:
                continue
            scenario_file = item.get("file") or item.get("path")
            if not scenario_file:
                continue
            path = ROOT / str(scenario_file)
            rows.append({
                "id": sid,
                "path": str(path.relative_to(ROOT)),
                "group": f"EPALS_{item.get('group', '')}",
                "focus": [item.get("reversible_cause", item.get("cause", ""))],
                "critical_events": [],
                "debrief_questions": item.get("debrief_questions", []),
                "expected_final_state": "reversible_cause_response",
            })
    return rows


def _run_scenario(path: str, dt: float, outcsv: Path, timeout_s: int = 180) -> pd.DataFrame:
    cmd = [sys.executable, str(ROOT / "run_simulation.py"), "--scenario", path, "--dt", str(dt), "--no-plot", "--save-csv", str(outcsv)]
    subprocess.run(cmd, cwd=ROOT, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout_s)
    return pd.read_csv(outcsv)


def _metric_summary(df: pd.DataFrame, scenario_id: str) -> dict[str, Any]:
    spo2 = _col(df, "SaO2")
    pao2 = _col(df, "PaO2")
    paco2 = _col(df, "PaCO2")
    hr = _col(df, "HR")
    map_ = _col(df, "MAP")

    first_failed = _first_time_col_equals(df, "airway_event_type", "failed_intubation_attempt")
    first_bvm = _first_time_col_bool(df, "bag_mask_ventilation_active")
    if first_bvm < 0:
        first_bvm = _first_time_col_equals(df, "airway_event_type", "start_bag_mask_ventilation")

    final = df.iloc[-1] if not df.empty else {}
    intubation_success = _safe_float(final.get("intubation_success_time_s", -1.0), -1.0)
    if intubation_success < 0:
        intubation_success = _first_time(df, df.get("intubated", pd.Series([False] * len(df))).map(_boolish)) if len(df) else -1.0
    extubation_time = _safe_float(final.get("extubation_time_s", -1.0), -1.0)

    reox_time = _first_reoxygenation_after(df, intubation_success, 0.90)
    if reox_time >= 0 and intubation_success >= 0:
        time_to_reox = max(0.0, reox_time - intubation_success)
    else:
        time_to_reox = -1.0

    return {
        "scenario": scenario_id,
        "SpO2_nadir": float(spo2.min()) if not spo2.dropna().empty else math.nan,
        "SpO2_nadir_time_s": _time_at_min(df, "SaO2"),
        "PaO2_nadir": float(pao2.min()) if not pao2.dropna().empty else math.nan,
        "PaCO2_peak": float(paco2.max()) if not paco2.dropna().empty else math.nan,
        "PaCO2_peak_time_s": _time_at_max(df, "PaCO2"),
        "HR_min": float(hr.min()) if not hr.dropna().empty else math.nan,
        "MAP_min": float(map_.min()) if not map_.dropna().empty else math.nan,
        "time_below_SpO2_90_s": _time_below(df, "SaO2", 0.90),
        "time_below_SpO2_80_s": _time_below(df, "SaO2", 0.80),
        "time_below_SpO2_70_s": _time_below(df, "SaO2", 0.70),
        "time_above_PaCO2_70_s": _time_above(df, "PaCO2", 70.0),
        "time_above_PaCO2_90_s": _time_above(df, "PaCO2", 90.0),
        "time_below_MAP_50_s": _time_below(df, "MAP", 50.0),
        "first_failed_attempt_time_s": first_failed,
        "first_rescue_ventilation_time_s": first_bvm,
        "intubation_success_time_s": intubation_success,
        "extubation_time_s": extubation_time,
        "time_to_reoxygenation_after_intubation_s": time_to_reox,
        "failed_intubation_count": int(_safe_float(final.get("failed_intubation_count", 0), 0)),
        "intubation_attempt_count": int(_safe_float(final.get("intubation_attempt_count", 0), 0)),
        "final_airway_interface": str(final.get("airway_interface", "")),
        "final_intubated": bool(_boolish(final.get("intubated", False))),
        "final_rescue_state": str(final.get("airway_rescue_state", "")),
        "airway_event_hypoxia_burden": _safe_float(final.get("airway_event_hypoxia_burden", math.nan)),
    }


def _threshold_rows(df: pd.DataFrame, scenario_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    thresholds = {
        "SaO2": [(0.90, "below"), (0.80, "below"), (0.70, "below")],
        "PaCO2": [(60.0, "above"), (70.0, "above"), (90.0, "above")],
        "MAP": [(55.0, "below"), (50.0, "below"), (45.0, "below")],
        "HR": [(80.0, "below"), (60.0, "below")],
    }
    for var, thrs in thresholds.items():
        if var not in df.columns:
            continue
        vals = _col(df, var)
        for thr, direction in thrs:
            if direction == "below":
                mask = vals < thr
                burden = _time_below(df, var, thr)
            else:
                mask = vals > thr
                burden = _time_above(df, var, thr)
            first_t = _first_time(df, mask)
            rows.append({
                "scenario": scenario_id,
                "variable": var,
                "threshold": thr,
                "direction": direction,
                "first_time_s": first_t,
                "duration_s": burden,
                "crossed": first_t >= 0,
            })
    return rows


def _flag_rows(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    sid = metrics["scenario"]
    failed = int(metrics.get("failed_intubation_count", 0))
    first_failed = float(metrics.get("first_failed_attempt_time_s", -1))
    first_rescue = float(metrics.get("first_rescue_ventilation_time_s", -1))
    intubation = float(metrics.get("intubation_success_time_s", -1))
    delay_rescue = (first_rescue - first_failed) if first_failed >= 0 and first_rescue >= 0 else math.nan
    flags = [
        ("severe_hypoxia", float(metrics.get("SpO2_nadir", 1.0)) < 0.80, metrics.get("SpO2_nadir")),
        ("profound_hypoxia", float(metrics.get("SpO2_nadir", 1.0)) < 0.70, metrics.get("SpO2_nadir")),
        ("prolonged_hypoxia", float(metrics.get("time_below_SpO2_90_s", 0.0)) >= 60.0, metrics.get("time_below_SpO2_90_s")),
        ("severe_hypercapnia", float(metrics.get("PaCO2_peak", 0.0)) >= 70.0, metrics.get("PaCO2_peak")),
        ("repeated_failed_attempts", failed >= 2, failed),
        ("delayed_rescue_after_failed_attempt", (delay_rescue == delay_rescue and delay_rescue > 60.0), delay_rescue),
        ("no_rescue_before_intubation_after_failure", (first_failed >= 0 and intubation >= 0 and not (first_rescue >= 0 and first_rescue < intubation)), {"first_failed": first_failed, "first_rescue": first_rescue, "intubation": intubation}),
        ("delayed_reoxygenation_after_intubation", float(metrics.get("time_to_reoxygenation_after_intubation_s", -1.0)) > 120.0, metrics.get("time_to_reoxygenation_after_intubation_s")),
    ]
    return [{"scenario": sid, "flag": name, "triggered": bool(on), "value": json.dumps(value) if isinstance(value, dict) else value} for name, on, value in flags]


def _timing_rows(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    sid = metrics["scenario"]
    timing_keys = [
        "SpO2_nadir_time_s",
        "PaCO2_peak_time_s",
        "first_failed_attempt_time_s",
        "first_rescue_ventilation_time_s",
        "intubation_success_time_s",
        "extubation_time_s",
        "time_to_reoxygenation_after_intubation_s",
    ]
    return [{"scenario": sid, "timing_metric": k, "value_s": metrics.get(k, math.nan)} for k in timing_keys]


def _write_scenario_report(outdir: Path, meta: dict[str, Any], metrics: dict[str, Any], flags: list[dict[str, Any]], thresholds: list[dict[str, Any]]) -> None:
    repodir = outdir / "scenario_reports"
    repodir.mkdir(parents=True, exist_ok=True)
    triggered = [f for f in flags if f["triggered"]]
    threshold_hits = [r for r in thresholds if r["crossed"]]
    lines = [
        f"# Emergency debrief — {meta['id']}",
        "",
        f"Group: `{meta.get('group','')}`",
        f"Scenario file: `{meta.get('path','')}`",
        "",
        "## Core metrics",
        "",
        f"- SpO2 nadir: {metrics.get('SpO2_nadir', math.nan):.3f} at t={metrics.get('SpO2_nadir_time_s', math.nan):.1f}s",
        f"- Time below SpO2 90%: {metrics.get('time_below_SpO2_90_s', math.nan):.1f}s",
        f"- Time below SpO2 80%: {metrics.get('time_below_SpO2_80_s', math.nan):.1f}s",
        f"- PaCO2 peak: {metrics.get('PaCO2_peak', math.nan):.1f} mmHg",
        f"- MAP minimum: {metrics.get('MAP_min', math.nan):.1f} mmHg",
        f"- Failed intubation count: {metrics.get('failed_intubation_count', 0)}",
        f"- Rescue ventilation first time: {metrics.get('first_rescue_ventilation_time_s', -1):.1f}s",
        f"- Intubation success time: {metrics.get('intubation_success_time_s', -1):.1f}s",
        f"- Time to reoxygenation after intubation: {metrics.get('time_to_reoxygenation_after_intubation_s', -1):.1f}s",
        "",
        "## Decision flags",
        "",
    ]
    if triggered:
        for f in triggered:
            lines.append(f"- `{f['flag']}` triggered; value={f['value']}")
    else:
        lines.append("- No educational flags triggered.")
    lines += ["", "## Threshold events", ""]
    if threshold_hits:
        for r in threshold_hits:
            lines.append(f"- {r['variable']} {r['direction']} {r['threshold']}: first t={r['first_time_s']:.1f}s; duration={r['duration_s']:.1f}s")
    else:
        lines.append("- No configured threshold crossed.")
    questions = meta.get("debrief_questions", []) or []
    lines += ["", "## Debrief questions", ""]
    for q in questions:
        lines.append(f"- {q}")
    lines += ["", "## Safety note", "", "Educational/research alpha only. Not for clinical use. Not a medical device.", ""]
    (repodir / f"{meta['id']}.md").write_text("\n".join(lines))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dt", type=float, default=10.0)
    ap.add_argument("--scenarios", nargs="*", default=None, help="Optional scenario IDs to run")
    ap.add_argument("--include-epals", action="store_true", help="Also run EPALS 5H/5T scenarios")
    ap.add_argument("--outdir", default=str(ROOT / "outputs" / "emergency_debrief_v1.26"))
    ap.add_argument("--fail-on-review", action="store_true")
    args = ap.parse_args()

    selected = set(args.scenarios) if args.scenarios else None
    scenarios = _collect_airway_scenarios(selected)
    if args.include_epals:
        scenarios.extend(_collect_epals_scenarios(selected))
    if not scenarios:
        print(json.dumps({"release": "v1.26-alpha", "status": "FAIL", "error": "no scenarios selected"}, indent=2))
        return 1

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    ts_dir = outdir / "timeseries"
    ts_dir.mkdir(parents=True, exist_ok=True)

    metrics_rows: list[dict[str, Any]] = []
    timing_rows: list[dict[str, Any]] = []
    flag_rows: list[dict[str, Any]] = []
    threshold_rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for meta in scenarios:
        try:
            csv_path = ts_dir / f"{meta['id']}_timeseries.csv"
            df = _run_scenario(meta["path"], args.dt, csv_path)
            metrics = _metric_summary(df, meta["id"])
            thresholds = _threshold_rows(df, meta["id"])
            flags = _flag_rows(metrics)
            metrics_rows.append(metrics)
            timing_rows.extend(_timing_rows(metrics))
            flag_rows.extend(flags)
            threshold_rows.extend(thresholds)
            _write_scenario_report(outdir, meta, metrics, flags, thresholds)
        except Exception as e:
            errors.append({"scenario": meta["id"], "error": str(e)})

    pd.DataFrame(metrics_rows).to_csv(outdir / "emergency_debrief_scenario_metrics_v126.csv", index=False)
    pd.DataFrame(timing_rows).to_csv(outdir / "emergency_debrief_timing_v126.csv", index=False)
    pd.DataFrame(flag_rows).to_csv(outdir / "emergency_debrief_decision_flags_v126.csv", index=False)
    pd.DataFrame(threshold_rows).to_csv(outdir / "emergency_debrief_threshold_events_v126.csv", index=False)

    triggered_flags = sum(1 for r in flag_rows if bool(r.get("triggered")))
    summary = {
        "release": "v1.26-alpha",
        "scenario_count": len(scenarios),
        "completed_scenarios": len(metrics_rows),
        "metric_rows": len(metrics_rows),
        "timing_rows": len(timing_rows),
        "threshold_rows": len(threshold_rows),
        "decision_flag_rows": len(flag_rows),
        "triggered_flags": triggered_flags,
        "errors": len(errors),
        "status": "PASS" if not errors and metrics_rows else "FAIL",
    }
    (outdir / "emergency_debrief_summary_v126.json").write_text(json.dumps({**summary, "error_rows": errors}, indent=2))

    index = [
        "# Emergency debrief index v1.26",
        "",
        f"Status: **{summary['status']}**",
        f"Scenarios: {summary['completed_scenarios']} / {summary['scenario_count']}",
        f"Decision flag rows: {summary['decision_flag_rows']}; triggered: {summary['triggered_flags']}",
        "",
        "## Scenario reports",
        "",
    ]
    for meta in scenarios:
        index.append(f"- [{meta['id']}](scenario_reports/{meta['id']}.md)")
    index += ["", "## Safety note", "", "Educational/research alpha only. Not for clinical use. Not a medical device.", ""]
    (outdir / "emergency_debrief_index_v126.md").write_text("\n".join(index))

    print(json.dumps(summary, indent=2))
    if args.fail_on_review and summary["status"] != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

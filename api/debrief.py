"""Lightweight emergency debrief utilities for PDT v2.2 API.

This module intentionally avoids pandas and heavy offline execution.  It works
on compact bedside snapshots already stored in a running API session.
Educational/research alpha only. Not for clinical use.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List


def _num(x: Any, default: float = math.nan) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _boolish(x: Any) -> bool:
    return str(x).strip().lower() in {"true", "1", "yes"}


def _json_safe(obj: Any) -> Any:
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    return obj


def _t(row: Dict[str, Any]) -> float:
    return _num(row.get("time_s", row.get("t", 0.0)), 0.0)


def _deltas(rows: List[Dict[str, Any]]) -> List[float]:
    if len(rows) < 2:
        return [0.0] * len(rows)
    out = []
    for i, row in enumerate(rows):
        if i + 1 < len(rows):
            out.append(max(0.0, _t(rows[i + 1]) - _t(row)))
        else:
            out.append(0.0)
    return out


def _values(rows: List[Dict[str, Any]], key: str) -> List[float]:
    return [_num(r.get(key)) for r in rows]


def _min_value(rows: List[Dict[str, Any]], key: str) -> float:
    vals = [v for v in _values(rows, key) if math.isfinite(v)]
    return float(min(vals)) if vals else math.nan


def _max_value(rows: List[Dict[str, Any]], key: str) -> float:
    vals = [v for v in _values(rows, key) if math.isfinite(v)]
    return float(max(vals)) if vals else math.nan


def _time_at_extreme(rows: List[Dict[str, Any]], key: str, mode: str) -> float:
    best_t = -1.0
    best_v = None
    for row in rows:
        v = _num(row.get(key))
        if not math.isfinite(v):
            continue
        if best_v is None or (mode == "min" and v < best_v) or (mode == "max" and v > best_v):
            best_v = v
            best_t = _t(row)
    return best_t


def _time_below(rows: List[Dict[str, Any]], key: str, threshold: float) -> float:
    total = 0.0
    for row, dt in zip(rows, _deltas(rows)):
        v = _num(row.get(key))
        if math.isfinite(v) and v < threshold:
            total += dt
    return float(total)


def _time_above(rows: List[Dict[str, Any]], key: str, threshold: float) -> float:
    total = 0.0
    for row, dt in zip(rows, _deltas(rows)):
        v = _num(row.get(key))
        if math.isfinite(v) and v > threshold:
            total += dt
    return float(total)


def _first_time(rows: List[Dict[str, Any]], predicate) -> float:
    for row in rows:
        try:
            if predicate(row):
                return _t(row)
        except Exception:
            continue
    return -1.0


def _first_reoxygenation_after(rows: List[Dict[str, Any]], start_time: float, threshold: float = 0.90) -> float:
    if start_time < 0:
        return -1.0
    for row in rows:
        if _t(row) >= start_time and _num(row.get("SaO2"), -1.0) >= threshold:
            return _t(row)
    return -1.0


def emergency_metrics(rows: Iterable[Dict[str, Any]], events: Iterable[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    rows = list(rows)
    events = list(events or [])
    if not rows:
        return {"status": "empty", "metrics": {}, "flags": [], "threshold_events": [], "events": events}

    first_failed = _first_time(rows, lambda r: str(r.get("airway_event_type", "")) == "failed_intubation_attempt")
    first_bvm = _first_time(rows, lambda r: _boolish(r.get("bag_mask_ventilation_active")) or str(r.get("airway_event_type", "")) == "start_bag_mask_ventilation")
    intub_success = _num(rows[-1].get("intubation_success_time_s"), -1.0)
    if intub_success < 0:
        intub_success = _first_time(rows, lambda r: _boolish(r.get("intubated")))
    extub_time = _num(rows[-1].get("extubation_time_s"), -1.0)
    if extub_time < 0:
        extub_time = _first_time(rows, lambda r: str(r.get("airway_event_type", "")) in {"accidental_extubation", "planned_extubation"})
    reox = _first_reoxygenation_after(rows, intub_success, 0.90)

    metrics = {
        "sample_count": len(rows),
        "duration_observed_s": max(0.0, _t(rows[-1]) - _t(rows[0])),
        "SpO2_nadir": _min_value(rows, "SaO2"),
        "SpO2_nadir_time_s": _time_at_extreme(rows, "SaO2", "min"),
        "time_below_SpO2_90_s": _time_below(rows, "SaO2", 0.90),
        "time_below_SpO2_80_s": _time_below(rows, "SaO2", 0.80),
        "time_below_SpO2_70_s": _time_below(rows, "SaO2", 0.70),
        "PaCO2_peak": _max_value(rows, "PaCO2"),
        "PaCO2_peak_time_s": _time_at_extreme(rows, "PaCO2", "max"),
        "time_above_PaCO2_70_s": _time_above(rows, "PaCO2", 70.0),
        "MAP_min": _min_value(rows, "MAP"),
        "time_below_MAP_50_s": _time_below(rows, "MAP", 50.0),
        "first_failed_attempt_time_s": first_failed,
        "first_rescue_ventilation_time_s": first_bvm,
        "intubation_success_time_s": intub_success,
        "extubation_time_s": extub_time,
        "time_to_reoxygenation_after_intubation_s": (reox - intub_success) if reox >= 0 and intub_success >= 0 else -1.0,
        "failed_intubation_count": int(_num(rows[-1].get("failed_intubation_count"), 0.0)),
        "intubation_attempt_count": int(_num(rows[-1].get("intubation_attempt_count"), 0.0)),
        "final_airway_interface": str(rows[-1].get("airway_interface", "")),
        "final_intubated": _boolish(rows[-1].get("intubated")),
        "final_rescue_state": str(rows[-1].get("airway_rescue_state", "")),
    }

    flags = _flag_rows(metrics)
    thresholds = _threshold_rows(rows)
    return _json_safe({
        "status": "ok",
        "metrics": metrics,
        "flags": flags,
        "threshold_events": thresholds,
        "events": events,
        "safety_note": "Educational/research alpha only. Not for clinical use. Not a medical device.",
    })


def _threshold_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    specs = [
        ("SaO2", "below", 0.90), ("SaO2", "below", 0.80), ("SaO2", "below", 0.70),
        ("PaCO2", "above", 60.0), ("PaCO2", "above", 70.0), ("PaCO2", "above", 90.0),
        ("MAP", "below", 55.0), ("MAP", "below", 50.0), ("MAP", "below", 45.0),
    ]
    for key, direction, thr in specs:
        if direction == "below":
            first = _first_time(rows, lambda r, k=key, t=thr: _num(r.get(k)) < t)
            duration = _time_below(rows, key, thr)
        else:
            first = _first_time(rows, lambda r, k=key, t=thr: _num(r.get(k)) > t)
            duration = _time_above(rows, key, thr)
        out.append({"variable": key, "direction": direction, "threshold": thr, "first_time_s": first, "duration_s": duration, "crossed": first >= 0})
    return out


def _flag_rows(metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    failed = int(metrics.get("failed_intubation_count", 0) or 0)
    first_failed = float(metrics.get("first_failed_attempt_time_s", -1.0) or -1.0)
    first_rescue = float(metrics.get("first_rescue_ventilation_time_s", -1.0) or -1.0)
    intubation = float(metrics.get("intubation_success_time_s", -1.0) or -1.0)
    delay_rescue = first_rescue - first_failed if first_failed >= 0 and first_rescue >= 0 else math.nan
    rows = [
        ("severe_hypoxia", _num(metrics.get("SpO2_nadir"), 1.0) < 0.80, metrics.get("SpO2_nadir")),
        ("profound_hypoxia", _num(metrics.get("SpO2_nadir"), 1.0) < 0.70, metrics.get("SpO2_nadir")),
        ("prolonged_hypoxia", _num(metrics.get("time_below_SpO2_90_s"), 0.0) >= 60.0, metrics.get("time_below_SpO2_90_s")),
        ("severe_hypercapnia", _num(metrics.get("PaCO2_peak"), 0.0) >= 70.0, metrics.get("PaCO2_peak")),
        ("repeated_failed_attempts", failed >= 2, failed),
        ("delayed_rescue_after_failed_attempt", math.isfinite(delay_rescue) and delay_rescue > 60.0, delay_rescue),
        ("no_rescue_before_intubation_after_failure", first_failed >= 0 and intubation >= 0 and not (first_rescue >= 0 and first_rescue < intubation), {"first_failed": first_failed, "first_rescue": first_rescue, "intubation": intubation}),
        ("delayed_reoxygenation_after_intubation", _num(metrics.get("time_to_reoxygenation_after_intubation_s"), -1.0) > 120.0, metrics.get("time_to_reoxygenation_after_intubation_s")),
    ]
    return [{"flag": name, "triggered": bool(triggered), "value": value} for name, triggered, value in rows]


"""Performance helpers for the PDT Clinical Training Console v2.4.

This module centralizes conservative defaults for the local web monitor.
It intentionally keeps high-rate UI streams compact and stores only
decimated history snapshots for debriefing and instructor review.
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict

DEFAULT_BEDSIDE_HZ = 4.0
DEFAULT_WAVEFORM_HZ = 24.0
MAX_BEDSIDE_HZ = 10.0
MAX_WAVEFORM_HZ = 30.0
DEFAULT_HISTORY_POINTS = 1800
DEFAULT_HISTORY_WINDOW_S = 1800.0
DEFAULT_HISTORY_DECIMATION_S = 1.0


def clamp_hz(value: float, *, default: float, max_hz: float) -> float:
    try:
        v = float(value)
    except Exception:
        v = default
    return max(0.5, min(v, max_hz))


def json_size_bytes(obj: Any) -> int:
    try:
        return len(json.dumps(obj, separators=(",", ":"), default=str).encode("utf-8"))
    except Exception:
        return -1


def now_ms() -> float:
    return time.perf_counter() * 1000.0


def payload_summary(name: str, obj: Any) -> Dict[str, Any]:
    return {"profile": name, "bytes": json_size_bytes(obj)}

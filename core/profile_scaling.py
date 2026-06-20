"""
v0.45 pediatric profile scaling helpers.

Small, conservative helpers used by modules that previously relied mainly on
20 kg defaults. These functions do not claim external validation; they make
profile-derived anchors explicit and auditable.
"""
from __future__ import annotations

from typing import Any, Mapping

from core.profiles import get_profile


def bus_patient_scalars(bus: Any, params: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return patient/profile scalars from BusState with safe fallbacks."""
    params = params or {}
    st = bus.state
    weight = float(getattr(st, "weight_kg", params.get("weight_kg", 20.0)) or 20.0)
    age_y = float(getattr(st, "age_y", params.get("age_y", 6.0)) or 6.0)
    profile_name = str(getattr(st, "patient_profile", params.get("patient_profile", "")) or "")
    if profile_name:
        resolved, profile = get_profile(profile_name, weight)
    else:
        resolved, profile = get_profile(None, weight)
    return {
        "weight_kg": max(weight, 0.5),
        "age_y": max(age_y, 0.0),
        "age_group": str(getattr(st, "age_group", profile.get("age_group", "child"))),
        "patient_profile": resolved,
        "profile": profile,
    }


def bsa_m2(weight_kg: float, age_y: float | None = None) -> float:
    """Approximate pediatric BSA from weight using a pragmatic height estimate."""
    wt = max(float(weight_kg), 0.5)
    age = max(float(age_y or 6.0), 0.0)
    # rough height anchors; adequate for scaling simulation parameters, not dosing.
    if age < 0.1:
        height_cm = 50.0
    elif age < 1.0:
        height_cm = 68.0
    elif age < 3.0:
        height_cm = 88.0
    elif age < 10.0:
        height_cm = 115.0 + 5.0 * (age - 5.0)
    else:
        height_cm = 150.0 + 2.0 * min(age - 12.0, 4.0)
    height_cm = max(height_cm, 45.0)
    return float(((height_cm * wt) / 3600.0) ** 0.5)


def profile_value(bus: Any, key: str, default: float, params: Mapping[str, Any] | None = None) -> float:
    info = bus_patient_scalars(bus, params)
    return float(info["profile"].get(key, default))

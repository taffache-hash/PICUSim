"""
Quality guards for PDT simulations (v0.27).

This module provides lightweight runtime checks: finite-value guard,
physiologic hard bounds, and structured SimulationError messages.
The goal is not clinical validation; it is failure transparency.
"""
from __future__ import annotations

from dataclasses import fields
import math
from typing import Any, Dict


class SimulationError(RuntimeError):
    """Raised when the engine detects an invalid numerical/physiologic state."""


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


# Intentionally broad hard bounds. These should catch numerical errors without
# rejecting severe but possible critical illness states.
HARD_BOUNDS: Dict[str, tuple[float, float]] = {
    "SaO2": (0.0, 1.02),
    "PaO2": (0.0, 760.0),
    "PaCO2": (5.0, 200.0),
    "pH_a": (6.50, 8.00),
    "MAP": (0.0, 220.0),
    "HR": (0.0, 300.0),
    "CO": (0.0, 20.0),
    "SV": (0.0, 250.0),
    "Vt": (0.0, 2500.0),
    "V_lung": (-500.0, 3000.0),
    "Paw": (-20.0, 120.0),
    "PEEP": (0.0, 40.0),
    "Pdriving": (-5.0, 80.0),
    "MP": (0.0, 200.0),
    "Hb": (1.0, 25.0),
    "Na_mmol_L": (90.0, 190.0),
    "K_mmol_L": (1.5, 10.0),
    "Cl_mmol_L": (60.0, 160.0),
    "HCO3_mmol_L": (3.0, 60.0),
    "glucose_mmol_L": (0.1, 60.0),
    "lactate": (0.0, 30.0),
    "T_core": (25.0, 43.5),
    "creatinine_mg_dL": (0.0, 15.0),
    "urea_mmol_L": (0.0, 80.0),
    "bilirubin_total_mg_dL": (0.0, 40.0),
    "INR": (0.4, 12.0),
    "PLT_count": (0.0, 1500.0),
    "ICP_mmHg": (-5.0, 80.0),
    "CPP_mmHg": (-30.0, 200.0),
    "GCS_proxy": (3.0, 15.5),
}


def check_state(bus, *, t: float | None = None, module_name: str = "") -> None:
    """Raise SimulationError if any numeric BusState value is NaN/Inf or out of hard bounds."""
    s = bus.state
    when = f"t={t:.3f}s" if t is not None else f"t={getattr(s, 't', float('nan')):.3f}s"
    where = f" after module {module_name!r}" if module_name else ""
    for f in fields(s):
        key = f.name
        val = getattr(s, key)
        if _is_number(val):
            if not math.isfinite(float(val)):
                snapshot = {k: getattr(s, k, None) for k in ("t", "MAP", "HR", "SaO2", "PaO2", "PaCO2", "pH_a", "CO", "Vt", "Na_mmol_L", "K_mmol_L", "lactate") if hasattr(s, k)}
                raise SimulationError(f"Non-finite value for {key}={val!r} at {when}{where}. Snapshot={snapshot}")
            if key in HARD_BOUNDS:
                lo, hi = HARD_BOUNDS[key]
                v = float(val)
                if v < lo or v > hi:
                    snapshot = {k: getattr(s, k, None) for k in ("t", "MAP", "HR", "SaO2", "PaO2", "PaCO2", "pH_a", "CO", "Vt", "Na_mmol_L", "K_mmol_L", "lactate") if hasattr(s, k)}
                    raise SimulationError(f"Physiologic hard-bound violation for {key}={v:.4g} outside [{lo}, {hi}] at {when}{where}. Snapshot={snapshot}")

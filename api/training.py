"""Emergency training scenario catalogue for PDT v2.2 API."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def emergency_scenarios() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    airway_pack = _load(ROOT / "data" / "airway_decision_scenario_pack_v1.25.yaml")
    for item in airway_pack.get("scenarios", []):
        path = str(item.get("path", ""))
        sid = str(item.get("id", Path(path).stem))
        rows.append({
            "id": sid,
            "path": path,
            "category": "airway_decision",
            "label": sid.replace("_", " "),
            "focus": item.get("decision_focus", []),
            "critical_events": item.get("critical_events", []),
            "debrief_questions": item.get("debrief_questions", []),
            "expected_final_state": item.get("expected_final_state", ""),
        })

    for pack_name, category, cause_key in [
        ("epals_5h_scenario_pack_v1.22.1.yaml", "EPALS_5H", "H_cause"),
        ("epals_5t_scenario_pack_v1.22.2.yaml", "EPALS_5T", "T_cause"),
    ]:
        pack = _load(ROOT / "data" / pack_name)
        for item in pack.get("scenarios", []):
            path = str(item.get("file") or item.get("path") or "")
            sid = str(item.get("id", Path(path).stem))
            rows.append({
                "id": sid,
                "path": path,
                "category": category,
                "label": sid.replace("_", " "),
                "focus": [item.get(cause_key, "")],
                "critical_events": [],
                "debrief_questions": item.get("debrief_questions", []),
                "primary_marker": item.get("primary_marker", ""),
                "expected_final_state": "reversible_cause_response",
            })

    seen = set()
    unique = []
    for row in rows:
        if row["id"] in seen:
            continue
        seen.add(row["id"])
        unique.append(row)
    return unique

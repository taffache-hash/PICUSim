#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.schemas import ScenarioDraftRequest
from api.scenario_authoring import list_templates, build_scenario_draft, validate_yaml_text


def main() -> int:
    rows = []
    for t in list_templates():
        req = ScenarioDraftRequest(template_id=t['id'], title=f"audit {t['id']}", description="Audit authored scenario. Not for clinical use.")
        draft = build_scenario_draft(req)
        val = validate_yaml_text(draft['yaml_text'])
        rows.append({'template': t['id'], 'status': val['status'], 'errors': val.get('errors', [])})
    summary = {'release': 'v2.7-alpha', 'templates': len(rows), 'pass': sum(r['status']=='pass' for r in rows), 'fail': sum(r['status']!='pass' for r in rows), 'rows': rows}
    out = ROOT / 'outputs' / 'scenario_authoring_v2.7'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'scenario_authoring_audit_summary_v27.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: summary[k] for k in ['release','templates','pass','fail']}, indent=2))
    return 1 if summary['fail'] else 0

if __name__ == '__main__':
    raise SystemExit(main())

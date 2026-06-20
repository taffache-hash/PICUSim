#!/usr/bin/env python3
"""Audit session save/load/export endpoints for PDT v2.5."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from api.server import app


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--fail-on-review', action='store_true')
    args = parser.parse_args()

    client = TestClient(app)
    rows = []
    r = client.post('/session/load', json={'scenario': 'airway_rsi_hypoxic_child_v1_24', 'dt': 1.0})
    ok = r.status_code == 200
    rows.append({'check': 'load_session', 'status': 'PASS' if ok else 'FAIL', 'code': r.status_code})
    if not ok:
        print(json.dumps({'status': 'FAIL', 'rows': rows}, indent=2)); return 1
    sid = r.json()['session_id']
    client.post(f'/session/{sid}/action', json={'action': 'airway_event', 'payload': {'name': 'failed_intubation_attempt', 'severity': 'moderate'}})
    client.post(f'/session/{sid}/step', json={'seconds': 8})
    client.post(f'/session/{sid}/instructor/note', json={'text': 'Audit note', 'kind': 'audit', 'pinned': False})

    exp = client.get(f'/session/{sid}/export?format=json')
    rows.append({'check': 'export_json', 'status': 'PASS' if exp.status_code == 200 and exp.json().get('schema') == 'pdt-session-save-v2.5' else 'FAIL', 'code': exp.status_code})
    md = client.get(f'/session/{sid}/export?format=md')
    rows.append({'check': 'export_markdown', 'status': 'PASS' if md.status_code == 200 and 'PDT Session Report' in md.text else 'FAIL', 'code': md.status_code})
    save = client.post(f'/session/{sid}/save', json={'basename': 'audit_v25_session'})
    save_ok = save.status_code == 200 and (ROOT / save.json().get('saved', {}).get('json_path', '')).exists()
    rows.append({'check': 'save_files', 'status': 'PASS' if save_ok else 'FAIL', 'code': save.status_code})
    if save_ok:
        path = save.json()['saved']['json_path']
        load = client.post('/session/load_saved', json={'path': path, 'replay_actions': True})
        rows.append({'check': 'load_saved', 'status': 'PASS' if load.status_code == 200 and load.json().get('scenario') else 'FAIL', 'code': load.status_code})
        if load.status_code == 200:
            client.delete(f"/session/{load.json()['session_id']}")
    client.delete(f'/session/{sid}')
    summary = {
        'release': 'v2.5-alpha',
        'checks': len(rows),
        'pass': sum(r['status'] == 'PASS' for r in rows),
        'fail': sum(r['status'] == 'FAIL' for r in rows),
        'rows': rows,
    }
    outdir = ROOT / 'outputs' / 'session_export_audit_v2.5'
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / 'session_export_audit_summary_v25.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: summary[k] for k in ['release','checks','pass','fail']}, indent=2))
    if args.fail_on_review and summary['fail']:
        return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

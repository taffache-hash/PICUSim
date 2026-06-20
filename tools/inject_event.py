#!/usr/bin/env python3
"""Inject a v0.43 acute event into a scenario YAML."""
from __future__ import annotations
import argparse, sys
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.simtools import load_yaml, scenario_path
from core.events import load_event_spec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--scenario', required=True)
    ap.add_argument('--event', required=True)
    ap.add_argument('--severity', default='moderate')
    ap.add_argument('--time', type=float, default=180.0)
    ap.add_argument('--out', default=None)
    args = ap.parse_args()
    spec = load_event_spec()
    events = spec.get('events', {})
    if args.event not in events:
        raise SystemExit(f"Unknown event '{args.event}'. Available: {', '.join(sorted(events))}")
    if args.severity not in events[args.event].get('severities', {}):
        raise SystemExit(f"Unknown severity '{args.severity}' for event '{args.event}'.")
    path = scenario_path(args.scenario)
    cfg = load_yaml(path)
    cfg.setdefault('events', []).append({'t': float(args.time), 'name': args.event, 'severity': args.severity})
    cfg['name'] = f"{cfg.get('name', path.stem)}__event_{args.event}_{args.severity}"
    cfg['description'] = str(cfg.get('description', '')).rstrip() + f"\n\nInjected acute event v0.43: {args.event}/{args.severity} at t={args.time}s."
    out = Path(args.out) if args.out else ROOT/'scenarios'/f"acute_event_{args.event}_{args.severity}.yaml"
    with out.open('w') as f:
        yaml.safe_dump(cfg, f, sort_keys=False)
    print(out)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

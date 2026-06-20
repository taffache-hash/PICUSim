#!/usr/bin/env python3
"""Deep dependency/ownership audit for PDT (v0.30).

This extends the v0.27 dependency audit by checking that duplicate writers are
explicitly governed by data/master_variable_policy.yaml. Duplicate writers are
not automatically wrong in a coupled physiological simulator, but ungoverned
duplicates are a high-risk source of silent bugs.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from typing import Any, Dict
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core import ScenarioLoader  # noqa: E402
from run_simulation import build_twin  # noqa: E402
from core.dependencies import audit_module_dependencies  # noqa: E402


def load_policy(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"masters": {}}
    return yaml.safe_load(path.read_text()) or {"masters": {}}


def deep_audit(scenario: str = 'healthy_child_20kg') -> Dict[str, Any]:
    scen = Path(scenario)
    if not scen.is_absolute():
        if scen.suffix != '.yaml':
            scen = scen.with_suffix('.yaml')
        scen = ROOT / 'scenarios' / scen.name
    loader = ScenarioLoader.from_yaml(str(scen))
    bus = loader.build_bus()
    engine = build_twin(bus, loader.config, dt=1.0)
    report = audit_module_dependencies(engine._modules)
    policy = load_policy(ROOT / 'data' / 'master_variable_policy.yaml')
    masters = set((policy.get('masters') or {}).keys())
    duplicate_writers = report.get('duplicate_writers', {})
    ungoverned = {k: v for k, v in duplicate_writers.items() if k not in masters}
    governed = {k: v for k, v in duplicate_writers.items() if k in masters}
    module_records = report.get('records', {})
    modules_missing_io = [name for name, rec in module_records.items() if not rec.get('reads') and not rec.get('writes')]
    return {
        'scenario': scen.name,
        'modules': len(module_records),
        'missing_bus_keys': report.get('missing_bus_keys', []),
        'orphan_reads_documentary': report.get('orphan_reads', []),
        'duplicate_writers': duplicate_writers,
        'duplicate_writers_governed': governed,
        'duplicate_writers_ungoverned': ungoverned,
        'modules_missing_io_declarations': modules_missing_io,
        'pass': len(report.get('missing_bus_keys', [])) == 0 and len(ungoverned) == 0,
    }


def write_md(audit: Dict[str, Any], path: Path) -> None:
    lines = [
        '# PDT v0.30 Deep Dependency Audit', '',
        f"Scenario used to build pipeline: **{audit['scenario']}**", '',
        f"Modules inspected: **{audit['modules']}**", '',
        f"Overall status: **{'PASS' if audit['pass'] else 'REVIEW REQUIRED'}**", '',
        '## Missing BusState keys', '',
    ]
    if audit['missing_bus_keys']:
        for item in audit['missing_bus_keys']:
            lines.append(f'- {item}')
    else:
        lines.append('None.')
    lines += ['', '## Duplicate writers governed by policy', '']
    if audit['duplicate_writers_governed']:
        for key, writers in sorted(audit['duplicate_writers_governed'].items()):
            lines.append(f'- **{key}**: {", ".join(writers)}')
    else:
        lines.append('None.')
    lines += ['', '## Duplicate writers NOT governed by policy', '']
    if audit['duplicate_writers_ungoverned']:
        for key, writers in sorted(audit['duplicate_writers_ungoverned'].items()):
            lines.append(f'- **{key}**: {", ".join(writers)}')
    else:
        lines.append('None.')
    lines += ['', '## Interpretation', '',
              'Duplicate writers are acceptable only when a master-variable policy documents the owner and allowed modifiers.',
              'This audit is an internal software-credibility check, not clinical validation.']
    path.write_text('\n'.join(lines))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--scenario', default='healthy_child_20kg')
    ap.add_argument('--outdir', default=str(ROOT / 'outputs' / 'validation_pack'))
    ap.add_argument('--fail-on-error', action='store_true')
    args = ap.parse_args()
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    audit = deep_audit(args.scenario)
    (outdir / 'dependency_deep_audit.json').write_text(json.dumps(audit, indent=2, ensure_ascii=False, default=str))
    write_md(audit, outdir / 'dependency_deep_audit.md')
    print(f"deep dependency audit written to {outdir}")
    if args.fail_on_error and not audit['pass']:
        return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

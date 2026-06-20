#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import PhysiologicalBus, ScenarioLoader
from run_simulation import build_twin
from core.dependencies import audit_module_dependencies


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--scenario', default='scenarios/healthy_child_20kg.yaml')
    ap.add_argument('--json', action='store_true')
    args=ap.parse_args()
    root=Path(__file__).resolve().parents[1]
    scen=Path(args.scenario)
    if not scen.is_absolute(): scen=root/scen
    loader=ScenarioLoader.from_yaml(str(scen))
    bus=loader.build_bus()
    engine=build_twin(bus, loader.config, dt=1.0)
    engine.verbose=False
    report=audit_module_dependencies(engine._modules)
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print('PDT dependency audit')
        print(f"modules: {len(report['records'])}")
        print(f"missing bus keys: {len(report['missing_bus_keys'])}")
        print(f"duplicate writers: {len(report['duplicate_writers'])}")
        if report['missing_bus_keys']:
            print('FAIL: missing BusState keys')
            for item in report['missing_bus_keys'][:30]: print(' ', item)
            raise SystemExit(1)
        print('PASS: all declared input/output keys exist in BusState')
        if report['duplicate_writers']:
            print('WARN: duplicate writers exist; see data/master_variable_policy.yaml')
            for k, v in sorted(report['duplicate_writers'].items())[:30]:
                print(f'  {k}: {", ".join(v)}')

if __name__=='__main__': main()

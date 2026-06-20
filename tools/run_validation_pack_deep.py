#!/usr/bin/env python3
"""Run the v0.29 deep validation pack tools with conservative defaults."""
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
TOOLS = [
    ['tools/benchmark_report.py', '--dt', '1.0'],
    ['tools/mass_balance_report.py', '--dt', '1.0'],
    ['tools/dt_convergence.py', '--scenarios', 'healthy_child_20kg', 'ards_mild', 'septic_shock', '--dts', '1.0', '0.5', '0.2'],
    ['tools/dose_response_deep_matrix.py', '--dt', '1.0', '--cases', 'iNO_PVR', 'salbutamol_Rrs', 'hypertonic_Na', 'crrt_urea'],
    ['tools/dependency_deep_audit.py'],
    ['tools/scenario_inventory.py'],
    ['tools/aggregate_expert_reviews.py', '--write-template'],
]

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--continue-on-error', action='store_true')
    args = ap.parse_args()
    failed = []
    for cmd in TOOLS:
        print('RUN', ' '.join(cmd))
        res = subprocess.run([sys.executable, *cmd], cwd=ROOT)
        if res.returncode != 0:
            failed.append(cmd[0])
            if not args.continue_on_error:
                return res.returncode
    if failed:
        print('FAILED:', ', '.join(failed))
        return 1
    print('v0.29 deep validation pack completed')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run or refresh the v0.28 validation pack.

This wrapper intentionally uses short per-tool timeouts so it does not hang on
slow machines. If a long simulation times out, the partial command log is still
written and the individual tool can be re-run manually.
"""
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=str(ROOT / "outputs" / "validation_pack"))
    ap.add_argument("--timeout", type=int, default=180)
    args = ap.parse_args()
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)

    commands = [
        [sys.executable, str(ROOT / "tools" / "benchmark_report.py"), "--dt", "2.0", "--outdir", str(outdir)],
        [sys.executable, str(ROOT / "tools" / "generate_expert_review_sheets.py"), "--benchmark-csv", str(outdir / "benchmark_report.csv"), "--outdir", str(outdir / "expert_review_sheets")],
        [sys.executable, str(ROOT / "tools" / "scenario_inventory.py"), "--outdir", str(outdir)],
        [sys.executable, str(ROOT / "tools" / "dt_convergence.py"), "--scenarios", "healthy_child_20kg", "ards_mild", "--dts", "1.0", "0.5", "--outdir", str(outdir)],
        [sys.executable, str(ROOT / "tools" / "dose_response_matrix.py"), "--cases", "iNO_PVR", "salbutamol_Rrs", "--dt", "2.0", "--outdir", str(outdir)],
    ]
    logs = []
    ok = True
    for cmd in commands:
        try:
            proc = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True, timeout=args.timeout)
            rc = proc.returncode
            stdout, stderr = proc.stdout, proc.stderr
        except subprocess.TimeoutExpired as exc:
            rc = 124
            stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
            stderr = f"TIMEOUT after {args.timeout}s"
        logs.append({"cmd": " ".join(cmd), "returncode": rc, "stdout": stdout, "stderr": stderr})
        ok = ok and rc == 0

    lines = ["# PDT v0.28 Validation Pack", "", f"Overall status: {'PASS' if ok else 'CHECK LOGS'}", "", "## Files", "", "- benchmark_report.md / .csv", "- expert_review_sheets/", "- scenario_inventory.md / .csv", "- dt_convergence.csv", "- dose_response_matrix.csv", "", "## Command log", ""]
    for item in logs:
        lines += [f"### `{item['cmd']}`", "", f"Return code: {item['returncode']}", "", "```", str(item['stdout'])[-2000:], str(item['stderr'])[-2000:], "```", ""]
    (outdir / "VALIDATION_PACK_INDEX.md").write_text("\n".join(lines))
    print(f"validation pack written to {outdir} ({'PASS' if ok else 'CHECK LOGS'})")
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())


from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_core_files_present():
    assert (ROOT / "run_simulation.py").exists()
    assert (ROOT / "modules" / "respiratory" / "mechanics.py").exists()
    assert (ROOT / "scenarios" / "healthy_child_20kg.yaml").exists()


def test_healthy_child_smoke():
    cmd = [sys.executable, str(ROOT / "run_simulation.py"), "--scenario", str(ROOT / "scenarios" / "healthy_child_20kg.yaml"), "--dt", "2", "--no-plot"]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr[-1000:]

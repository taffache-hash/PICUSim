
#!/usr/bin/env python3
"""One-command launcher for the Pediatric Critical Care Simulation Console."""
from __future__ import annotations

import argparse
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parent
VERSION = (ROOT / "VERSION").read_text().strip() if (ROOT / "VERSION").exists() else "unknown"


def is_port_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.25)
        return s.connect_ex((host, int(port))) != 0


def find_free_port(host: str, start: int = 8000, attempts: int = 50) -> int:
    port = int(start)
    for p in range(port, port + int(attempts)):
        if is_port_free(host, p):
            return p
    raise RuntimeError(f"No free TCP port found from {start} to {start + attempts - 1}")


def open_browser_later(url: str, delay: float = 1.0) -> None:
    def _open():
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception:
            pass
    threading.Thread(target=_open, daemon=True).start()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Start PDT local API + web monitor")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--reload", action="store_true")
    parser.add_argument("--log-level", default="warning")
    args = parser.parse_args(argv)

    port = args.port if is_port_free(args.host, args.port) else find_free_port(args.host, args.port + 1)
    url = f"http://{args.host}:{port}/monitor"
    print(f"Pediatric Critical Care Simulation Console {VERSION}")
    print(f"API:     http://{args.host}:{port}/docs")
    print(f"Monitor: {url}")
    print("Press Ctrl+C to stop.")
    if not args.no_browser:
        open_browser_later(url)
    uvicorn.run("api.server:app", host=args.host, port=port, reload=args.reload, log_level=args.log_level)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

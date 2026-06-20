#!/usr/bin/env python3
"""Start the local API and web monitor server."""
import argparse
import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Start PDT Clinical Training Console API + Web Monitor")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    parser.add_argument("--log-level", default="warning")
    args = parser.parse_args()
    uvicorn.run("api.server:app", host=args.host, port=args.port, reload=args.reload, log_level=args.log_level)


if __name__ == "__main__":
    main()

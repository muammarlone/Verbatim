from __future__ import annotations

import argparse
import threading
import webbrowser

import uvicorn

from .app import create_app
from .security import require_loopback_host


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Secure Transcription Studio locally.")
    parser.add_argument("--port", type=int, default=8765, help="Local port (default: 8765)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser window")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("--port must be between 1024 and 65535")
    host = "127.0.0.1"
    require_loopback_host(host)
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(f"http://{host}:{args.port}")).start()
    uvicorn.run(
        create_app(),
        host=host,
        port=args.port,
        log_level="warning",
        access_log=False,
    )


if __name__ == "__main__":
    main()

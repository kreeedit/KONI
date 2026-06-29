"""Entrypoint: start the KONI reader web app.

    python scripts/serve.py            # http://127.0.0.1:8000
    python scripts/serve.py --port 8080

Makes the repo root importable (for `app`) and scripts/ (for `common`), then
launches the stdlib HTTP server. Zero external dependencies.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))            # so `import app.server` works
sys.path.insert(0, str(REPO / "scripts"))  # so `import common` works

from app.server import run  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="KONI reader web app")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()
    run(args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
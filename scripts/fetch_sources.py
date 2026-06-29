"""Download and cache the four primary sources into data/raw/.

Usage:
    python scripts/fetch_sources.py            # use cache, fetch missing only
    python scripts/fetch_sources.py --refresh  # re-download all

Sources:
  * TLG classic canon   cd.authors.php
  * TLG post-E canon    post_tlg_e.php
  * Perseus CTS inventory (GetCapabilities XML)
  * bcdavasconcelos main_list.md (GitHub raw, master branch)
"""
from __future__ import annotations

import argparse
import time
import urllib.request
import urllib.error

from common import (
    RAW_BCD, RAW_CD, RAW_CTS, RAW_POST, USER_AGENT, ensure_dirs, log,
)

SOURCES = [
    {
        "name": "TLG classic canon (cd.authors.php)",
        "url": "https://stephanus.tlg.uci.edu/tlgauthors/cd.authors.php",
        "path": RAW_CD,
    },
    {
        "name": "TLG post-E canon (post_tlg_e.php)",
        "url": "https://stephanus.tlg.uci.edu/tlgauthors/post_tlg_e.php",
        "path": RAW_POST,
    },
    {
        "name": "Perseus CTS inventory (GetCapabilities)",
        "url": "https://cts.perseids.org/api/cts?request=GetCapabilities",
        "path": RAW_CTS,
    },
    {
        "name": "bcdavasconcelos main_list.md",
        "url": "https://raw.githubusercontent.com/bcdavasconcelos/"
               "Greek-Authors-and-Works-in-TLG/master/main_list.md",
        "path": RAW_BCD,
    },
]

HEADERS = {"User-Agent": USER_AGENT}


def fetch(url: str, path, refresh: bool) -> bool:
    """Download url to path. Return True if the file is now present on disk."""
    if path.exists() and not refresh:
        log(f"  cached: {path.name} ({path.stat().st_size:,} bytes)")
        return True
    for attempt in range(1, 4):
        try:
            log(f"  GET {url}")
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=120) as resp:
                content = resp.read()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            log(f"  ok: {path.name} ({len(content):,} bytes)")
            return True
        except urllib.error.HTTPError as exc:
            log(f"  attempt {attempt} HTTP {exc.code}: {exc.reason}")
        except Exception as exc:  # noqa: BLE001
            log(f"  attempt {attempt} failed: {exc}")
            if attempt < 3:
                time.sleep(2 * attempt)
    log(f"  ERROR: could not fetch {url}")
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--refresh", action="store_true",
                    help="re-download all sources even if cached")
    args = ap.parse_args()

    ensure_dirs()
    log("Fetching KONI sources:")
    rc = 0
    for src in SOURCES:
        log(f"- {src['name']}")
        if not fetch(src["url"], src["path"], args.refresh):
            rc = 1
    if rc:
        log("WARNING: one or more sources failed; pipeline may be incomplete.")
    else:
        log("All sources ready.")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
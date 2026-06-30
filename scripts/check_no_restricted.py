"""Firewall self-test.

Assert that no restricted-tier content leaks into the published artifacts
(data/canon-links.nt, data/canon-editions.nt). Computes the restricted work
URIs and edition strings from canon.json, then scans the published files and
fails (exit 1) if any restricted URI or edition string is present.

Run after build_jsonld.py --links, e.g. in CI before a Zenodo deposit.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common

KONI = "https://w3id.org/koni/tlg/"
PUBLISHED = [common.DATA / "canon-links.nt", common.DATA / "canon-editions.nt"]


def restricted_keys(canon):
    uris, editions = set(), set()
    for aid, a in canon.items():
        for wid, w in (a.get("works") or {}).items():
            src = w.get("source")
            if isinstance(src, str) and src.startswith("restricted:"):
                uris.add(f"{KONI}{aid}.{wid}")
                if w.get("edition"):
                    editions.add(w["edition"])
    return uris, editions


def main() -> int:
    if not common.CANON_JSON.exists():
        sys.exit("[ABORT] canon.json not found.")
    canon = common.read_json(common.CANON_JSON)
    uris, editions = restricted_keys(canon)
    common.log(f"Restricted works to guard: {len(uris)}")

    leaks = 0
    for p in PUBLISHED:
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        for u in sorted(uris):
            if u in text:
                print(f"  LEAK: {u} in {p.name}", file=sys.stderr)
                leaks += 1
        for e in editions:
            if e and e in text:
                print(f"  LEAK: a restricted edition string in {p.name}", file=sys.stderr)
                leaks += 1

    if leaks:
        print(f"FAIL: {leaks} restricted leak(s) in published artifacts.", file=sys.stderr)
        return 1
    print("OK: no restricted-tier content in published artifacts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

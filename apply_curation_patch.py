#!/usr/bin/env python3
"""KONI — add the curation overlay + provenance tiers + firewall self-test.

Run from the PROJECT ROOT:

    python3 apply_curation_patch.py

Creates (additive):

  data/local/supplement.json    Your curation overlay. Adds works / editions the
                                open sources miss (e.g. fragmentary authors whose
                                only "work" is a critical edition). Every entry
                                carries a `source` tier:
                                  local:curated  -> your own scholarship; PUBLISHED
                                  restricted:tlg -> lifted from the TLG canon; kept
                                                    local, firewalled from outputs.
                                Ships with one worked example (Archestratus, 1115).

  scripts/apply_supplement.py   Merges the overlay into data/canon.json. Run it
                                AFTER build_canon.py and BEFORE build_jsonld.py.

  scripts/check_no_restricted.py  Firewall self-test: proves no restricted-tier
                                content leaks into the published artifacts
                                (canon-links.nt, canon-editions.nt). Exit 1 on leak.

Pairs with the firewall in build_jsonld.py (re-run apply_jsonld_patch.py first so
the publishable graphs are tier-aware). Safe to re-run (backs up *.bak.<ts>).
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sys
import time

ROOT = pathlib.Path.cwd()
STAMP = time.strftime("%Y%m%d-%H%M%S")


def _need_root() -> None:
    if not (ROOT / "scripts" / "common.py").exists():
        sys.exit("[ABORT] Futtasd a projekt gyökeréből (ahol a scripts/ van).")


def _write(rel: str, text: str) -> None:
    fp = ROOT / rel
    fp.parent.mkdir(parents=True, exist_ok=True)
    if fp.exists():
        bak = fp.with_name(fp.name + f".bak.{STAMP}")
        shutil.copy2(fp, bak)
        print(f"    backup -> {bak.name}")
    fp.write_text(text, encoding="utf-8")
    print(f"  wrote {rel}")


SUPPLEMENT = {
    "1115": {
        "works": {
            "001": {
                "title_latin": "Fragmenta",
                "edition": ("Snell, B. (ed.), Tragicorum Graecorum fragmenta, "
                            "vol. 1. G\u00f6ttingen: Vandenhoeck & Ruprecht, 1971: 239."),
                "source": "local:curated"
            }
        }
    }
}


APPLY_SUPPLEMENT = r'''"""Merge data/local/supplement.json (your curation overlay) into canon.json.

Run AFTER scripts/build_canon.py (which rewrites canon.json) and BEFORE
scripts/build_jsonld.py. Each supplemented work carries a `source` tier:

  local:curated   your own scholarship  -> published (repo + Zenodo)
  restricted:tlg  lifted from the TLG    -> kept local, firewalled from outputs

Idempotent: re-running yields the same canon.json.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common

SUPPLEMENT = common.DATA / "local" / "supplement.json"


def _mint_urn(aid, wid):
    return f"urn:cts:greekLit:tlg{aid}.tlg{wid}"


def merge(canon, supp):
    added_authors = added_works = patched = 0
    for aid, sa in supp.items():
        a = canon.get(aid)
        if a is None:
            a = {
                "author_id": aid,
                "author_name_latin": sa.get("author_name_latin"),
                "author_name_greek": sa.get("author_name_greek"),
                "author_name_english": sa.get("author_name_english"),
                "epitheton": sa.get("epitheton"),
                "era": sa.get("era"),
                "viaf_id": sa.get("viaf_id"),
                "source": list(sa.get("source") or ["local:curated"]),
                "works": {},
            }
            canon[aid] = a
            added_authors += 1
        a.setdefault("works", {})
        for wid, sw in (sa.get("works") or {}).items():
            w = a["works"].get(wid)
            if w is None:
                a["works"][wid] = {
                    "work_id": wid,
                    "title_latin": sw.get("title_latin"),
                    "title_english": sw.get("title_english"),
                    "title_greek": sw.get("title_greek"),
                    "cts_urn": sw.get("cts_urn") or _mint_urn(aid, wid),
                    "cts_confirmed": bool(sw.get("cts_confirmed", False)),
                    "edition": sw.get("edition"),
                    "source": sw.get("source", "local:curated"),
                }
                added_works += 1
            else:
                for k in ("title_latin", "title_english", "title_greek",
                          "cts_urn", "edition", "source"):
                    if sw.get(k) is not None:
                        w[k] = sw[k]
                w.setdefault("source", sw.get("source", "local:curated"))
                patched += 1
    return added_authors, added_works, patched


def main() -> int:
    if not common.CANON_JSON.exists():
        sys.exit(f"[ABORT] {common.CANON_JSON} not found - run build_canon.py first.")
    if not SUPPLEMENT.exists():
        common.log(f"No supplement at {SUPPLEMENT}; nothing to merge.")
        return 0
    canon = common.read_json(common.CANON_JSON)
    supp = common.read_json(SUPPLEMENT)
    aa, aw, pa = merge(canon, supp)
    common.write_json(common.CANON_JSON, canon)
    common.log(f"Supplement merged: +{aa} authors, +{aw} works, {pa} works patched.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


CHECK_NO_RESTRICTED = r'''"""Firewall self-test.

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
'''


def main() -> None:
    _need_root()
    print(f"KONI curation patch — projekt gyökér: {ROOT}\nidőbélyeg: {STAMP}\n")
    print("[1/3] data/local/supplement.json")
    _write("data/local/supplement.json",
           json.dumps(SUPPLEMENT, ensure_ascii=False, indent=2) + "\n")
    print("[2/3] scripts/apply_supplement.py")
    _write("scripts/apply_supplement.py", APPLY_SUPPLEMENT)
    print("[3/3] scripts/check_no_restricted.py")
    _write("scripts/check_no_restricted.py", CHECK_NO_RESTRICTED)
    print("\nKész. A teljes folyamat (a kánon felépítése után):")
    print("  python3 scripts/apply_supplement.py        # overlay -> canon.json")
    print("  python3 scripts/build_jsonld.py --links     # canon.jsonld + canon-links.nt + canon-editions.nt")
    print("  python3 scripts/check_no_restricted.py      # firewall önteszt")


if __name__ == "__main__":
    main()

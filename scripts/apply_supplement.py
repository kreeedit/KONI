"""Merge data/local/supplement.json (your curation overlay) into canon.json.

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

"""Merge all parsed sources into the final canon.json tree.

Sources merged per author:
  * TLG cd.authors.php      -> Latin name + epitheton (no works)
  * TLG post_tlg_e.php      -> Latin name + epitheton + works (post-E)
  * bcdavasconcelos list    -> classic-canon works + Perseus URNs (broad)
  * Perseus CTS inventory  -> English/Greek titles + confirmed URNs (subset)
  * Wikidata (P3576)        -> Greek author name + era (best-effort)

canon.json is keyed by 4-digit author ID; each author has a `works` map keyed
by 3-digit work ID. `cts_urn` is always present (synthesized if not confirmed);
`cts_confirmed` is True only when the work is in the Perseus CTS inventory.
"""
from __future__ import annotations

import sys

from common import (
    CANON_JSON, INT_BCD, INT_CLASSIC, INT_CTS, INT_POSTE, INT_WIKIDATA,
    SRC_BCD, SRC_CTS, SRC_TLG_CD, SRC_TLG_POST, SRC_WIKIDATA, log, read_json,
    write_json,
)


def _synth_urn(aid: str, wid: str) -> str:
    return f"urn:cts:greekLit:tlg{aid}.tlg{wid}"


def build() -> dict:
    cd = {a["author_id"]: a for a in read_json(INT_CLASSIC)} if INT_CLASSIC.exists() else {}
    post = {a["author_id"]: a for a in read_json(INT_POSTE)} if INT_POSTE.exists() else {}
    bcd = read_json(INT_BCD) if INT_BCD.exists() else {}
    cts = read_json(INT_CTS) if INT_CTS.exists() else {}
    wd = read_json(INT_WIKIDATA) if INT_WIKIDATA.exists() else {}

    all_ids = sorted(set(cd) | set(post) | set(bcd) | set(cts))
    canon: dict[str, dict] = {}
    for aid in all_ids:
        cda = cd.get(aid)
        pa = post.get(aid)
        bcda = bcd.get(aid)
        ctsa = cts.get(aid)
        wda = wd.get(aid)

        # Latin name: prefer TLG display (cd then post), then bcd, then cts.latin.
        latin = None
        if cda and cda.get("author_name_latin"):
            latin = cda["author_name_latin"]
        elif pa and pa.get("author_name_latin"):
            latin = pa["author_name_latin"]
        elif bcda and bcda.get("author_name"):
            latin = bcda["author_name"]
        elif ctsa and ctsa.get("latin"):
            latin = ctsa["latin"]

        # English name: CTS english (authoritative), then bcd (often English form).
        english = None
        if ctsa and ctsa.get("english"):
            english = ctsa["english"]
        elif bcda and bcda.get("author_name"):
            english = bcda["author_name"]

        # Epitheton from TLG (cd preferred, then post).
        epitheton = None
        if cda and cda.get("epitheton"):
            epitheton = cda["epitheton"]
        elif pa and pa.get("epitheton"):
            epitheton = pa["epitheton"]

        # Greek name, era, and VIAF id from Wikidata (P3576 + P214/P2348/P569/P570).
        greek = wda.get("greek") if wda else None
        era = wda.get("era") if wda else None
        viaf_id = wda.get("viaf_id") if wda else None

        # ---- works: union across post, bcd, cts by work_id ----
        works: dict[str, dict] = {}
        # post works (Latin titles, TLG canonical for post-E)
        if pa:
            for w in pa.get("works", []):
                wid = w["work_id"]
                works.setdefault(wid, {"work_id": wid})
                works[wid]["title_latin"] = works[wid].get("title_latin") or w.get("title_latin")
        # bcd works (Latin titles + Perseus URNs)
        if bcda:
            for wid, w in bcda.get("works", {}).items():
                works.setdefault(wid, {"work_id": wid})
                if w.get("title_latin") and not works[wid].get("title_latin"):
                    works[wid]["title_latin"] = w["title_latin"]
                if w.get("cts_urn") and not works[wid].get("cts_urn"):
                    works[wid]["cts_urn"] = w["cts_urn"]
        # cts works (English/Greek titles + confirmed URNs) — highest authority
        if ctsa:
            for wid, w in ctsa.get("works", {}).items():
                works.setdefault(wid, {"work_id": wid})
                if w.get("english"):
                    works[wid]["title_english"] = w["english"]
                if w.get("latin") and not works[wid].get("title_latin"):
                    works[wid]["title_latin"] = w["latin"]
                if w.get("greek"):
                    works[wid]["title_greek"] = w["greek"]
                if w.get("cts_urn"):
                    works[wid]["cts_urn"] = w["cts_urn"]  # confirmed overrides
                if w.get("edition") and not works[wid].get("edition"):
                    works[wid]["edition"] = w["edition"]
        # finalize each work: fill cts_urn (synthesize), title fields, confirmed
        cts_work_ids = set(ctsa.get("works", {})) if ctsa else set()
        for wid, w in works.items():
            w.setdefault("title_latin", None)
            w.setdefault("title_english", None)
            w.setdefault("title_greek", None)
            w.setdefault("edition", None)
            if not w.get("cts_urn"):
                w["cts_urn"] = _synth_urn(aid, wid)
            w["cts_confirmed"] = wid in cts_work_ids
            # stable key order
            works[wid] = {
                "work_id": w["work_id"],
                "title_latin": w["title_latin"],
                "title_english": w["title_english"],
                "title_greek": w["title_greek"],
                "edition": w["edition"],
                "cts_urn": w["cts_urn"],
                "cts_confirmed": w["cts_confirmed"],
            }

        source = []
        if cda:
            source.append(SRC_TLG_CD)
        if pa:
            source.append(SRC_TLG_POST)
        if bcda:
            source.append(SRC_BCD)
        if ctsa:
            source.append(SRC_CTS)
        if wda:
            source.append(SRC_WIKIDATA)

        canon[aid] = {
            "author_id": aid,
            "author_name_latin": latin,
            "author_name_greek": greek,
            "author_name_english": english,
            "epitheton": epitheton,
            "era": era,
            "viaf_id": viaf_id,
            "source": source,
            "works": {k: works[k] for k in sorted(works)},
        }

    log(f"enrich_canon: {len(canon)} authors, "
        f"{sum(len(a['works']) for a in canon.values())} works")
    return canon


def main() -> int:
    canon = build()
    write_json(CANON_JSON, canon)
    log(f"wrote {CANON_JSON.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
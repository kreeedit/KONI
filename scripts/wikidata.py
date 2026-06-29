"""Wikidata enrichment for TLG authors (zero-dependency: urllib only).

Matches Wikidata entities EXACTLY by the **P3576** ("TLG author ID") property
(no fuzzy name search, no direct VIAF API call), and pulls:

  * P214   -> VIAF identifier (stored as viaf_id; bypasses the VIAF API entirely)
  * P2348  -> historical period (label; used as a fallback era string)
  * P569/P570 -> birth/death dates -> century-range era (primary)
  * grc label -> Greek author name

Result cached at data/intermediate/wikidata_era.json:
    {author_id: {wikidata_qid, viaf_id, greek, birth, death, era, period}}

Runs MERGE with the existing cache: a partial/re-failed run never drops prior
data — only successfully (re)queried IDs are overwritten. Wikidata SPARQL is
rate-limited (~1 req/min during wdqs outages); batches wait politely.
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.parse
import urllib.request

from common import (
    INT_BCD, INT_CTS, INT_CLASSIC, INT_POSTE, INT_WIKIDATA, SRC_WIKIDATA,
    USER_AGENT, ensure_dirs, log, read_json, write_json,
)

SPARQL_URL = "https://query.wikidata.org/sparql"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/sparql-results+json",
}
CHUNK = 200          # TLG IDs per query (VALUES size safety)
BATCH_PAUSE = 62     # seconds between batches (Wikidata rate-limit ~1 req/min)
RETRY_429 = 3

QUERY_TPL = """
SELECT ?tlg ?qid ?viaf ?periodLabel ?birth ?death ?grcLabel WHERE {{
  VALUES ?tlg {{ {ids} }}
  ?item wdt:P3576 ?tlg .
  BIND( STR(?item) AS ?qidStr )
  OPTIONAL {{ ?item wdt:P214 ?viaf }}
  OPTIONAL {{ ?item wdt:P2348 ?period . ?period rdfs:label ?periodLabel FILTER(LANG(?periodLabel)="en") }}
  OPTIONAL {{ ?item wdt:P569 ?birth }}
  OPTIONAL {{ ?item wdt:P570 ?death }}
  OPTIONAL {{ ?item rdfs:label ?grcLabel FILTER(LANG(?grcLabel)="grc") }}
}}
"""

YEAR_RE = re.compile(r"^(-?\d{1,4})-\d{2}-\d{2}")


def _year(date):
    if not date:
        return None
    m = YEAR_RE.match(date)
    return int(m.group(1)) if m else None


def _century(year: int) -> int:
    return (abs(year) + 99) // 100


def format_era(birth, death) -> str | None:
    by, dy = _year(birth), _year(death)
    if by is None and dy is None:
        return None

    def seg(y):
        if y is None:
            return None
        era = "B.C." if y < 0 else "A.D."
        c = _century(y)
        suf = "st" if c == 1 else "nd" if c == 2 else "rd" if c == 3 else "th"
        return f"{c}{suf} c. {era}"

    b, d = seg(by), seg(dy)
    if b and d and by < 0 and dy < 0:
        lo, hi = sorted((_century(by), _century(dy)))
        return (f"{lo}th c. B.C." if lo == hi
                else f"{lo}th–{hi}th c. B.C.")
    if b and d and by >= 0 and dy >= 0:
        lo, hi = sorted((_century(by), _century(dy)))
        los = "st" if lo == 1 else "nd" if lo == 2 else "rd" if lo == 3 else "th"
        his = "st" if hi == 1 else "nd" if hi == 2 else "rd" if hi == 3 else "th"
        return f"{lo}{los} c. A.D." if lo == hi else f"{lo}{los}–{hi}{his} c. A.D."
    return b or d


def _chunk(ids):
    return [ids[i:i + CHUNK] for i in range(0, len(ids), CHUNK)]


def _post(url, query, timeout=120):
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode({"query": query}),
                                 headers=HEADERS)
    return urllib.request.urlopen(req, timeout=timeout).read()


def fetch(ids, batches: list | None = None) -> dict:
    """Query Wikidata for the given TLG author IDs. Returns {author_id: {...}}."""
    result: dict[str, dict] = {}
    chunks = batches or _chunk(ids)
    for ci, batch in enumerate(chunks, 1):
        vals = " ".join(f'"{i}"' for i in batch)
        q = QUERY_TPL.format(ids=vals)
        raw = None
        for attempt in range(1, RETRY_429 + 2):
            try:
                raw = _post(SPARQL_URL, q)
                break
            except urllib.error.HTTPError as exc:
                if exc.code == 429:
                    log(f"  batch {ci}: 429 rate-limited, waiting 60s "
                        f"(attempt {attempt}/{RETRY_429})")
                    time.sleep(60)
                    continue
                log(f"  batch {ci}: HTTP {exc.code} — skipping")
                break
            except Exception as exc:  # noqa: BLE001
                log(f"  batch {ci}: {exc} — skipping")
                break
        if raw is None:
            continue
        try:
            rows = json.loads(raw).get("results", {}).get("bindings", [])
        except Exception:
            continue
        for b in rows:
            tlg = b.get("tlg", {}).get("value")
            if not tlg:
                continue
            qid = b.get("qidStr", {}).get("value", "").rsplit("/", 1)[-1]
            viaf = b.get("viaf", {}).get("value")
            birth = b.get("birth", {}).get("value")
            death = b.get("death", {}).get("value")
            grc = b.get("grcLabel", {}).get("value")
            period = b.get("periodLabel", {}).get("value")
            era = format_era(birth, death) or (period or None)
            # keep the richest record if an ID appears twice
            prev = result.get(tlg)
            if prev and not any((era, grc, viaf)):
                continue
            result[tlg] = {
                "wikidata_qid": qid or None,
                "viaf_id": viaf or None,
                "greek": grc or None,
                "birth": birth or None,
                "death": death or None,
                "period": period or None,
                "era": era,
            }
        log(f"  batch {ci}/{len(chunks)}: +{len(rows)} (total {len(result)})")
        if ci < len(chunks):
            time.sleep(BATCH_PAUSE)
    return result


def _all_ids() -> list[str]:
    ids: set[str] = set()
    if INT_CLASSIC.exists():
        ids.update(a["author_id"] for a in read_json(INT_CLASSIC))
    if INT_POSTE.exists():
        ids.update(a["author_id"] for a in read_json(INT_POSTE))
    if INT_BCD.exists():
        ids.update(read_json(INT_BCD).keys())
    if INT_CTS.exists():
        ids.update(read_json(INT_CTS).keys())
    return sorted(ids)


def main() -> int:
    ap = argparse.ArgumentParser(description="Wikidata P3576 enrichment")
    ap.add_argument("--refresh", action="store_true",
                    help="re-query Wikidata (merge with existing cache)")
    ap.add_argument("--only", help="comma-separated TLG IDs to query only")
    args = ap.parse_args()

    ensure_dirs()
    existing = {}
    if INT_WIKIDATA.exists():
        try:
            existing = read_json(INT_WIKIDATA)
        except Exception:
            existing = {}

    if not args.refresh and not args.only:
        log(f"wikidata: cached ({INT_WIKIDATA.name}, {len(existing)} entries); "
            f"use --refresh to re-query")
        return 0

    if args.only:
        ids = [x.strip().zfill(4) for x in args.only.split(",") if x.strip()]
    else:
        ids = _all_ids()
    log(f"wikidata: querying {len(ids)} TLG IDs (P3576 + P214/P2348/P569/P570) ...")
    fresh = fetch(ids)
    # merge: fresh overwrites existing for (re)queried IDs; others preserved
    existing.update(fresh)
    write_json(INT_WIKIDATA, existing)
    log(f"wrote {INT_WIKIDATA.name} ({len(existing)} entries; "
        f"+{len(fresh)} refreshed)")
    viaf = sum(1 for v in existing.values() if v.get("viaf_id"))
    era = sum(1 for v in existing.values() if v.get("era"))
    log(f"  viaf_id coverage: {viaf}; era coverage: {era}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
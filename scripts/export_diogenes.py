"""Diogenes-oriented export of the KONI canon (zero-dependency: csv, sqlite3).

Diogenes (Peter Heslin) is the standard offline tool for classicists. Its
internal canon indexes authors/works by numeric identifiers with names/titles
and a notion of which works have text. This exporter maps the KONI canon to that
shape so a Diogenes loader (or a human) can use it:

Outputs (in data/):
  * diogenes_canon.csv  — one row per (author, work): author_id, work_id,
    latin_name, greek_name, greek_title, latin_title, cts_urn, cts_confirmed,
    exportable, seq
  * diogenes.sqlite     — tables `authors` and `works` with the same fields,
    keyed by author_id / (author_id, work_id).

`exportable = cts_confirmed OR present in the PerseusDL/canonical-greekLit repo`:
only works that actually have a downloadable open Greek text are marked
exportable. `seq` is a stable 1-based ordinal within each author (Diogenes work
numbering).
"""
from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path

from common import CANON_JSON, REPO, read_json, log

CSV_PATH = REPO / "data" / "diogenes_canon.csv"
DB_PATH = REPO / "data" / "diogenes.sqlite"
REPO_MAP_PATH = REPO / "data" / "intermediate" / "greekLit_map.json"


def _repo_keys() -> set[str]:
    """(aid_wid) keys that have a downloadable Greek TEI in the Perseus repo."""
    if not REPO_MAP_PATH.exists():
        return set()
    try:
        import json
        return set(json.loads(REPO_MAP_PATH.read_text(encoding="utf-8")).keys())
    except Exception:
        return set()

AUTHOR_COLS = [
    "author_id", "latin_name", "greek_name", "english_name",
    "epitheton", "era", "viaf_id", "work_count", "readable_count",
]
WORK_COLS = [
    "author_id", "work_id", "seq", "latin_name", "greek_name",
    "latin_title", "greek_title", "english_title", "cts_urn",
    "cts_confirmed", "exportable",
]


def build_rows(canon: dict):
    """Yield (author_row, [work_rows]) pairs in canon (author_id) order."""
    repo_keys = _repo_keys()
    for aid in sorted(canon):
        a = canon[aid]
        works = a.get("works", {})
        author_row = {
            "author_id": aid,
            "latin_name": a.get("author_name_latin"),
            "greek_name": a.get("author_name_greek"),
            "english_name": a.get("author_name_english"),
            "epitheton": a.get("epitheton"),
            "era": a.get("era"),
            "viaf_id": a.get("viaf_id"),
            "work_count": len(works),
            "readable_count": sum(1 for wid in works
                                  if works[wid].get("cts_confirmed")
                                  or f"{aid}_{wid}" in repo_keys),
        }
        work_rows = []
        for seq, wid in enumerate(sorted(works), 1):
            w = works[wid]
            confirmed = bool(w.get("cts_confirmed"))
            in_repo = f"{aid}_{wid}" in repo_keys
            work_rows.append({
                "author_id": aid,
                "work_id": wid,
                "seq": seq,
                "latin_name": a.get("author_name_latin"),
                "greek_name": a.get("author_name_greek"),
                "latin_title": w.get("title_latin"),
                "greek_title": w.get("title_greek"),
                "english_title": w.get("title_english"),
                "cts_urn": w.get("cts_urn"),
                "cts_confirmed": int(confirmed),
                # exportable = there IS a downloadable open Greek text:
                # confirmed in the CTS inventory OR present in the Perseus repo.
                "exportable": int(confirmed or in_repo),
            })
        yield author_row, work_rows


def write_csv(canon: dict) -> int:
    n = 0
    with CSV_PATH.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(WORK_COLS)
        for arow, wrows in build_rows(canon):
            for r in wrows:
                w.writerow([r.get(c, "") for c in WORK_COLS])
                n += 1
    return n


def write_sqlite(canon: dict) -> int:
    if DB_PATH.exists():
        DB_PATH.unlink()
    con = sqlite3.connect(str(DB_PATH))
    cur = con.cursor()
    cur.execute("CREATE TABLE authors ("
                "author_id TEXT PRIMARY KEY, latin_name TEXT, greek_name TEXT, "
                "english_name TEXT, epitheton TEXT, era TEXT, viaf_id TEXT, "
                "work_count INTEGER, readable_count INTEGER)")
    cur.execute("CREATE TABLE works ("
                "author_id TEXT, work_id TEXT, seq INTEGER, latin_name TEXT, "
                "greek_name TEXT, latin_title TEXT, greek_title TEXT, "
                "english_title TEXT, cts_urn TEXT, cts_confirmed INTEGER, "
                "exportable INTEGER, PRIMARY KEY (author_id, work_id))")
    cur.execute("CREATE INDEX idx_works_author ON works(author_id)")
    cur.execute("CREATE INDEX idx_works_exportable ON works(exportable)")
    n_authors = n_works = n_exportable = 0
    for arow, wrows in build_rows(canon):
        cur.execute("INSERT INTO authors VALUES (?,?,?,?,?,?,?,?,?)",
                    [arow.get(c) for c in AUTHOR_COLS])
        n_authors += 1
        for r in wrows:
            cur.execute("INSERT INTO works VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        [r.get(c) for c in WORK_COLS])
            n_works += 1
            if r["exportable"]:
                n_exportable += 1
    con.commit()
    con.close()
    return n_authors, n_works, n_exportable


def export() -> None:
    canon = read_json(CANON_JSON)
    n_rows = write_csv(canon)
    na, nw, ne = write_sqlite(canon)
    log(f"export_diogenes: {CSV_PATH.name} ({n_rows} work rows), "
        f"{DB_PATH.name} ({na} authors, {nw} works, {ne} exportable)")


def main() -> int:
    if not CANON_JSON.exists():
        log("ERROR: canon.json not found; run build_canon.py first.")
        return 1
    export()
    return 0


if __name__ == "__main__":
    sys.exit(main())
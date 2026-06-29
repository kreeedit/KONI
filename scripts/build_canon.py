"""Orchestrator: run the whole KONI pipeline and export canon.json + canon.csv
+ a coverage report. Reads from cache; run fetch_sources.py first to populate
data/raw/ (or it will error on the first stage).
"""
from __future__ import annotations

import csv
import sys

from common import (
    CANON_CSV, CANON_JSON, REPORTS, SRC_CTS, SRC_TLG_CD, SRC_TLG_POST,
    SRC_BCD, SRC_WIKIDATA, ensure_dirs, log, read_json,
)

CSV_FIELDS = [
    "author_id", "author_name_latin", "author_name_greek",
    "author_name_english", "epitheton", "era", "source",
    "work_id", "title_latin", "title_english", "title_greek",
    "cts_urn", "cts_confirmed",
]


def run_stages() -> None:
    import parse_tlg_cd
    import parse_tlg_post
    import parse_cts
    import parse_bcdavasconcelos
    import wikidata
    import enrich_canon
    import export_diogenes

    for stage in (parse_tlg_cd, parse_tlg_post, parse_cts,
                  parse_bcdavasconcelos):
        log(f"--- {stage.__name__} ---")
        stage.main()
    log("--- wikidata (best-effort, cached) ---")
    wikidata.main()
    log("--- enrich_canon ---")
    enrich_canon.main()
    log("--- export_diogenes ---")
    export_diogenes.main()


def write_csv(canon: dict) -> int:
    rows = 0
    with CANON_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(CSV_FIELDS)
        for aid in sorted(canon):
            a = canon[aid]
            src = ";".join(a.get("source", []))
            if not a["works"]:
                w.writerow([aid, a["author_name_latin"], a["author_name_greek"],
                            a["author_name_english"], a["epitheton"], a["era"],
                            src, "", "", "", "", "", ""])
                rows += 1
            for wid in sorted(a["works"]):
                wk = a["works"][wid]
                w.writerow([aid, a["author_name_latin"], a["author_name_greek"],
                            a["author_name_english"], a["epitheton"], a["era"],
                            src, wid, wk["title_latin"], wk["title_english"],
                            wk["title_greek"], wk["cts_urn"], wk["cts_confirmed"]])
                rows += 1
    return rows


def write_report(canon: dict) -> None:
    n = len(canon)
    total_works = sum(len(a["works"]) for a in canon.values())
    authors_with_works = sum(1 for a in canon.values() if a["works"])
    works_confirmed = sum(
        1 for a in canon.values() for w in a["works"].values() if w["cts_confirmed"]
    )
    authors_greek_name = sum(1 for a in canon.values() if a["author_name_greek"])
    authors_era = sum(1 for a in canon.values() if a["era"])
    works_greek_title = sum(
        1 for a in canon.values() for w in a["works"].values() if w["title_greek"]
    )

    def pct(x, y):
        return f"{(100 * x / y):.1f}%" if y else "0%"

    src_counts = {SRC_TLG_CD: 0, SRC_TLG_POST: 0, SRC_BCD: 0, SRC_CTS: 0,
                  SRC_WIKIDATA: 0}
    for a in canon.values():
        for s in a["source"]:
            src_counts[s] = src_counts.get(s, 0) + 1
    authors_viaf = sum(1 for a in canon.values() if a.get("viaf_id"))

    # PerseusDL repo map size (if it has been built)
    import json as _json
    from common import REPO as _REPO
    repo_map_path = _REPO / "data" / "intermediate" / "greekLit_map.json"
    repo_n = 0
    if repo_map_path.exists():
        try:
            repo_n = len(_json.loads(repo_map_path.read_text(encoding="utf-8")))
        except Exception:
            repo_n = 0

    lines = [
        "# KONI build report",
        "",
        "## Summary",
        f"- Authors: **{n}**",
        f"- Works: **{total_works}**",
        f"- Authors with at least one work: {authors_with_works} ({pct(authors_with_works, n)})",
        "",
        "## Coverage",
        f"- Works confirmed in the Perseus CTS inventory (`cts_confirmed=true`): "
        f"{works_confirmed}/{total_works} ({pct(works_confirmed, total_works)})",
        f"- Greek editions indexed in the PerseusDL/canonical-greekLit repo: "
        f"**{repo_n}**",
        f"- Authors with a Greek name (Wikidata P3576): "
        f"{authors_greek_name}/{n} ({pct(authors_greek_name, n)})",
        f"- Authors with an era (Wikidata P569/P570 + P2348): "
        f"{authors_era}/{n} ({pct(authors_era, n)})",
        f"- Authors with a VIAF id (Wikidata P214): "
        f"{authors_viaf}/{n} ({pct(authors_viaf, n)})",
        f"- Works with a Greek title (Perseus CTS): "
        f"{works_greek_title}/{total_works} ({pct(works_greek_title, total_works)})",
        "",
        "## Authors by source",
        f"- TLG classical canon (cd.authors.php): {src_counts.get(SRC_TLG_CD, 0)}",
        f"- TLG post-E canon (post_tlg_e.php): {src_counts.get(SRC_TLG_POST, 0)}",
        f"- bcdavasconcelos work list: {src_counts.get(SRC_BCD, 0)}",
        f"- Perseus CTS inventory: {src_counts.get(SRC_CTS, 0)}",
        f"- Wikidata (P3576): {src_counts.get(SRC_WIKIDATA, 0)}",
        "",
        "## Known limitations",
        "- The classical TLG canon (cd.authors.php) lists only authors, not works. "
        "The classical works are supplied by the bcdavasconcelos list (broad) and the "
        "Perseus CTS inventory (authoritative, with Greek titles).",
        "- `cts_confirmed=false`: the cts_urn is synthesized "
        "(`urn:cts:greekLit:tlg<author>.tlg<work>`); the work is in the canon, but the "
        "Perseus CTS catalog has no published text (the reader then tries the repo map, "
        "CTS, and finally the Hopper).",
        "- The VIAF API cannot be called directly (Cloudflare 403); the VIAF id and "
        "the era come from the Wikidata **P214 / P569 / P570 / P2348** properties "
        "(P3576 exact matching). The era is best-effort: some authors are `null`.",
        "- The post-E author names keep the TLG mixed lower/upper casing "
        "(e.g. `DIONYSIUS HALICARNASSENSIS`) — faithful to the source.",
    ]
    (REPORTS / "build_report.md").write_text("\n".join(lines) + "\n",
                                             encoding="utf-8")
    log(f"wrote {REPORTS/'build_report.md'}")


def main() -> int:
    ensure_dirs()
    run_stages()
    canon = read_json(CANON_JSON)
    n_rows = write_csv(canon)
    log(f"wrote {CANON_CSV.name} ({n_rows} rows)")
    write_report(canon)
    return 0


if __name__ == "__main__":
    sys.exit(main())
"""Parse bcdavasconcelos/Greek-Authors-and-Works-in-TLG main_list.md into
bcd_works.json. Secondary source for classic-canon works (the classic TLG HTML
lists authors only, no works).

The markdown is a table:
  | TLG Code | Author | Work | TLG Online | Diogenes | Perseus Catalog |
where TLG Code is AUTHOR4.WORK3 (e.g. 0001.001) and the Perseus Catalog cell
holds the CTS URN. Output: {author_id: {author_name, works: {work_id:
  {title_latin, cts_urn}}}}.
"""
from __future__ import annotations

import re
import sys

from common import INT_BCD, RAW_BCD, log, write_json

ROW_RE = re.compile(
    r"^\|\s*(\d{4})\.(\d{3})\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|"
    r"[^|]*\|[^|]*\|[^|]*\|\s*$"
)
URN_RE = re.compile(r"urn:cts:greekLit:tlg\d{4}\.tlg\d{3}")


def parse() -> dict:
    text = RAW_BCD.read_text(encoding="utf-8")
    index: dict[str, dict] = {}
    n_rows = 0
    for line in text.splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        aid, wid, author, work = m.group(1), m.group(2), m.group(3).strip(), m.group(4).strip()
        urn = None
        um = URN_RE.search(line)
        if um:
            urn = um.group(0)
        n_rows += 1
        entry = index.setdefault(aid, {"author_name": author, "works": {}})
        # prefer a non-empty author name; keep first seen otherwise
        if not entry["author_name"] and author:
            entry["author_name"] = author
        entry["works"].setdefault(wid, {"title_latin": work, "cts_urn": urn})
    n_authors = len(index)
    n_works = sum(len(v["works"]) for v in index.values())
    log(f"parse_bcdavasconcelos: {n_rows} rows -> {n_authors} authors, {n_works} works")
    return index


def main() -> int:
    if not RAW_BCD.exists():
        log(f"ERROR: {RAW_BCD} not found; run fetch_sources.py first.")
        return 1
    index = parse()
    write_json(INT_BCD, index)
    log(f"wrote {INT_BCD.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
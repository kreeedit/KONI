"""Parse the TLG post-E/Byzantine canon HTML (post_tlg_e.php) into
authors_poste.json. Unlike the classic page, this one lists authors AND works.

The page consists of ~68 tables in REVERSE chronological order (newest update
first), each preceded by an "Updated on: YYYY-MM-DD" marker. An author recurs
across update batches, so the same author_id may appear many times with an
evolving work set. Strategy:

  * Document order = newest update first. The FIRST occurrence of an author_id
    gives its freshest name/epitheton.
  * Works are UNIONED across all occurrences, deduped by work_id; the title is
    taken from the first (newest) occurrence of each work_id. This maximizes
    coverage without inventing data.

Row structure:
    <tr>
      <td>AUTHOR_ID</td>
      <td>NAME epitheton ( <a class="toggle_works">N work</a> )
          <div class="works"><span>WORK_ID <i>WORK_TITLE</i></span><br>...</div>
      </td>
    </tr>

Output: [{author_id, author_name_latin, epitheton, works:[{work_id,title_latin}]}]
"""
from __future__ import annotations

import re
import sys

from htmlutil import Node, Str, parse as parse_html

from common import INT_POSTE, RAW_POST, log, write_json
from parse_tlg_cd import peel_epitheton

ID_RE = re.compile(r"^\d{1,4}$")


def _works_from_div(div) -> list[dict]:
    works: list[dict] = []
    if not div:
        return works
    for sp in div.find_all("span"):
        text = sp.get_text(" ", strip=True)
        m = re.match(r"^(\d{3})\s+(.*)$", text)
        if m:
            works.append({"work_id": m.group(1), "title_latin": m.group(2).strip()})
    return works


def _name_from_td(td) -> str:
    """Text of td up to the first <a>/<div>/<br>, with the works-count '(' dropped."""
    parts: list[str] = []
    for child in td.children:
        if isinstance(child, Node) and child.name in ("a", "div", "br"):
            break
        if isinstance(child, Str):
            parts.append(str(child))
    raw = " ".join(parts).strip()
    return raw.rsplit("(", 1)[0].strip()


def parse() -> list[dict]:
    html = RAW_POST.read_text(encoding="utf-8")
    soup = parse_html(html)

    # author_id -> {"name":..,"epitheton":..,"works": {work_id: title}}
    authors: dict[str, dict] = {}
    for tr in soup.find_all("tr"):  # document order = newest update first
        tds = tr.find_all("td", recursive=False)
        if len(tds) != 2:
            continue
        aid_raw = tds[0].get_text(strip=True)
        if not ID_RE.fullmatch(aid_raw):
            continue
        aid = aid_raw.zfill(4)

        raw_name = _name_from_td(tds[1])
        works = _works_from_div(tds[1].find("div", class_="works"))

        entry = authors.get(aid)
        if entry is None:
            name, epitheton = peel_epitheton(raw_name)
            entry = {
                "author_id": aid,
                "author_name_latin": name,
                "epitheton": epitheton,
                "works": {},
            }
            authors[aid] = entry
        # union works (first occurrence = newest title wins)
        for w in works:
            entry["works"].setdefault(w["work_id"], w["title_latin"])

    out: list[dict] = []
    for aid in sorted(authors):
        e = authors[aid]
        works = [
            {"work_id": wid, "title_latin": title}
            for wid, title in sorted(e["works"].items())
        ]
        out.append({
            "author_id": e["author_id"],
            "author_name_latin": e["author_name_latin"],
            "epitheton": e["epitheton"],
            "works": works,
        })
    total_works = sum(len(a["works"]) for a in out)
    log(f"parse_tlg_post: {len(out)} authors (unioned across update batches), "
        f"{total_works} works")
    return out


def main() -> int:
    if not RAW_POST.exists():
        log(f"ERROR: {RAW_POST} not found; run fetch_sources.py first.")
        return 1
    out = parse()
    write_json(INT_POSTE, out)
    log(f"wrote {INT_POSTE.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
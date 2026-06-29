"""Parse the TLG classic-canon HTML (cd.authors.php) into authors_classic.json.

The public page lists authors only (no works), as `<li>` items of the form
"NNNN Name epitheton" (e.g. "0012 Homerus Epic."). This script extracts every
ID-prefixed entry, splits a trailing genre epitheton where it can be done
confidently, and writes authors_classic.json:
    [{author_id, author_name_latin, epitheton}]
"""
from __future__ import annotations

import re
import sys

from htmlutil import parse as parse_html

from common import INT_CLASSIC, RAW_CD, SRC_TLG_CD, log, write_json

# Genre abbreviation vocabulary used as trailing epitheta by the TLG.
# Compared case-insensitively, with surrounding <>/() stripped.
GENRE = {
    "hist.", "phil.", "comic.", "trag.", "epic.", "gramm.", "lyr.", "rhet.",
    "eccl.", "med.", "soph.", "poeta", "theol.", "eleg.", "alchem.", "epigr.",
    "iamb.", "geogr.", "orat.", "math.", "astrol.", "apol.", "perieg.",
    "astron.", "erot.", "mech.", "paradox.", "biogr.", "tact.", "myth.",
    "chronogr.", "parodius", "geom.", "paroemiogr.", "epist.", "epistulae",
    "epistula", "mus.", "fab.", "lexicogr.", "lex.", "pharmac.", "iatr.",
    "dialect.", "scr.", "poet.", "et",
}


def peel_epitheton(display: str) -> tuple[str, str | None]:
    """Peel a trailing genre epitheton off the TLG display string.

    Returns (name, epitheton). epitheton is None when no confident genre tail
    is found; in that case name keeps the full display (honest fallback for
    anonymous collections like "Acta Alexandrinorum").
    """
    tokens = display.strip().split()
    if not tokens:
        return display, None
    genre_cores = {t.strip("<>()[],").lower() for t in GENRE}
    ep: list[str] = []
    i = len(tokens) - 1
    while i >= 0:
        tok = tokens[i]
        core = tok.lower().strip("<>()[],")
        if core in genre_cores:
            ep.append(tok)
            i -= 1
            continue
        break
    if not ep:
        return display.strip(), None
    epitheton = " ".join(reversed(ep))
    name = " ".join(tokens[: i + 1]).strip()
    return name, epitheton


def parse() -> list[dict]:
    html = RAW_CD.read_text(encoding="utf-8")
    soup = parse_html(html)
    authors: dict[str, dict] = {}
    duplicates = 0
    for li in soup.find_all("li"):
        text = li.get_text(" ", strip=True)
        m = re.match(r"^(\d{4})\s+(.+)$", text)
        if not m:
            continue
        aid = m.group(1)
        display = m.group(2).strip()
        name, epitheton = peel_epitheton(display)
        if aid in authors:
            duplicates += 1
            continue
        authors[aid] = {
            "author_id": aid,
            "author_name_latin": name,
            "epitheton": epitheton,
        }
    out = [authors[k] for k in sorted(authors)]
    log(f"parse_tlg_cd: {len(out)} authors ({duplicates} duplicate IDs skipped)")
    return out


def main() -> int:
    if not RAW_CD.exists():
        log(f"ERROR: {RAW_CD} not found; run fetch_sources.py first.")
        return 1
    out = parse()
    write_json(INT_CLASSIC, out)
    log(f"wrote {INT_CLASSIC.name}")
    # quick coverage note
    with_ep = sum(1 for a in out if a["epitheton"])
    log(f"  with extracted epitheton: {with_ep}/{len(out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
"""Parse the Perseus CTS inventory (GetCapabilities XML) into cts_index.json.

The inventory (cts.perseids.org) lists every textgroup/work in the greekLit
CTS namespace. It is the authoritative source for CTS URNs and for Greek (grc)
author/work titles — neither of which is in the public TLG HTML.

Output: {author_id: {english, latin, greek, works: {work_id:
  {english, latin, greek, cts_urn, cts_confirmed}}}}
where author_id is the 4-digit TLG number embedded in the textgroup URN.
"""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET

from common import INT_CTS, RAW_CTS, log, write_json

NS = "http://chs.harvard.edu/xmlns/cts"
XMLLANG = "{http://www.w3.org/XML/1998/namespace}lang"
TG = f"{{{NS}}}textgroup"
GN = f"{{{NS}}}groupname"
WORK = f"{{{NS}}}work"
TITLE = f"{{{NS}}}title"
ED = f"{{{NS}}}edition"
TR = f"{{{NS}}}translation"
LABEL = f"{{{NS}}}label"
DESC = f"{{{NS}}}description"
_WS = re.compile(r"\s+")

URN_TG_RE = re.compile(r"^urn:cts:greekLit:tlg(\d{4})$")
URN_W_RE = re.compile(r"^urn:cts:greekLit:tlg(\d{4})\.tlg(\d{3})$")


def _text_of(el) -> str:
    return _WS.sub(" ", " ".join(el.itertext())).strip()


def _names_by_lang(parent, tag):
    """Collect {lang: text} for children of `parent` named `tag`."""
    out = {}
    for el in parent.findall(tag):
        lang = el.get(XMLLANG) or ""
        out[lang] = (el.text or "").strip()
    return out


def _greek_label(parent):
    """First grc <ti:label> under editions/translations of a work."""
    for cont in parent.findall(ED) + parent.findall(TR):
        for lab in cont.findall(LABEL):
            if (lab.get(XMLLANG) or "") == "grc":
                txt = (lab.text or "").strip()
                if txt:
                    return txt
    return None


def _greek_edition_el(parent):
    """The Greek edition element (urn contains '-grc'), else the first edition."""
    eds = parent.findall(ED)
    for e in eds:
        if "-grc" in (e.get("urn") or ""):
            return e
    return eds[0] if eds else None


def _edition_description(parent) -> str | None:
    """Print-edition metadata from the Greek edition's <ti:description>."""
    ed = _greek_edition_el(parent)
    if ed is None:
        return None
    for d in ed.findall(DESC):
        txt = _text_of(d)
        if txt:
            return txt
    return None


def parse() -> dict:
    tree = ET.parse(str(RAW_CTS))
    root = tree.getroot()
    index: dict[str, dict] = {}
    n_groups = n_works = 0
    for tg in root.iter(TG):
        urn = tg.get("urn", "")
        mtg = URN_TG_RE.match(urn)
        if not mtg:
            continue
        aid = mtg.group(1)
        n_groups += 1
        gn = _names_by_lang(tg, GN)
        entry = {
            "english": gn.get("eng") or None,
            "latin": gn.get("lat") or None,
            "greek": gn.get("grc") or None,
            "works": {},
        }
        for w in tg.findall(WORK):
            wurn = w.get("urn", "")
            mw = URN_W_RE.match(wurn)
            if not mw:
                continue
            wid = mw.group(2)
            n_works += 1
            titles = _names_by_lang(w, TITLE)
            grk = _greek_label(w)
            edition_desc = _edition_description(w)
            # Collect edition/translation URNs so the backend can fetch real text.
            edition_urns = [
                e.get("urn", "") for e in w.findall(ED)
            ] + [
                t.get("urn", "") for t in w.findall(TR)
            ]
            edition_urns = [u for u in edition_urns if u]
            greek_ed = next(
                (u for u in edition_urns if "-grc" in u), edition_urns[0] if edition_urns else None
            )
            entry["works"][wid] = {
                "english": titles.get("eng") or None,
                "latin": titles.get("lat") or None,
                "greek": titles.get("grc") or grk or None,
                "cts_urn": wurn,
                "cts_confirmed": True,
                "edition_urns": edition_urns,
                "greek_edition_urn": greek_ed,
                "edition": edition_desc,
            }
        # keep last write wins; no textgroup urn should repeat
        index[aid] = entry
    log(f"parse_cts: {n_groups} textgroups, {n_works} works "
        f"({len(index)} unique author IDs)")
    return index


def main() -> int:
    if not RAW_CTS.exists():
        log(f"ERROR: {RAW_CTS} not found; run fetch_sources.py first.")
        return 1
    index = parse()
    write_json(INT_CTS, index)
    log(f"wrote {INT_CTS.name}")
    # quick coverage note
    with_greek_name = sum(1 for v in index.values() if v["greek"])
    with_any_work_greek = sum(
        1 for v in index.values() for w in v["works"].values() if w["greek"]
    )
    log(f"  authors with grc groupname: {with_greek_name}/{len(index)}")
    log(f"  works with grc title: {with_any_work_greek}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
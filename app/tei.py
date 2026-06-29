"""TEI XML -> section/paragraph/line structure for the reader.

Handles Perseus/First1K Greek TEI:
  body > div[type=edition] > div[type=textpart][n=...] > (l | p | head | milestone)

Verses use <l n="...">; prose uses <p>. Section label comes from the textpart
div's @n. Falls back to a single section if the structure is unusual.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

TEI = "http://www.tei-c.org/ns/1.0"
NS = {"tei": TEI}
L = f"{{{TEI}}}l"
P = f"{{{TEI}}}p"
DIV = f"{{{TEI}}}div"
HEAD = f"{{{TEI}}}head"
TITLE_EL = f"{{{TEI}}}title"

_WS = re.compile(r"\s+")


def _text(el) -> str:
    return _WS.sub(" ", " ".join(el.itertext())).strip()


def _collect_blocks(sec) -> list[dict]:
    """Collect <head>/<l>/<p> under `sec` in document order, skipping nested
    textpart divs (which are handled as their own sections)."""
    blocks: list[dict] = []
    for el in sec.iter():
        if el.tag == DIV and el.get("type") == "textpart" and el is not sec:
            # nested section: skip its subtree to avoid duplicating
            continue
        if el.tag == HEAD:
            txt = _text(el)
            if txt:
                blocks.append({"kind": "head", "text": txt})
        elif el.tag == L:
            n = el.get("n")
            txt = _text(el)
            if txt:
                blocks.append({"kind": "line", "n": n, "text": txt})
        elif el.tag == P:
            txt = _text(el)
            if txt:
                blocks.append({"kind": "para", "text": txt})
    return blocks


def parse_tei(xml_path) -> dict:
    tree = ET.parse(str(xml_path))
    root = tree.getroot()
    body = root.find(".//tei:body", NS)
    edition_div = body.find(".//tei:div[@type='edition']", NS) if body is not None else None
    if edition_div is None and body is not None:
        edition_div = body  # fallback: whole body

    title = None
    th = root.find(".//tei:teiHeader//tei:titleStmt/tei:title", NS)
    if th is not None:
        title = _text(th)

    # Printed-edition citation from the TEI header source description.
    edition_info = None
    sd = root.find(".//tei:teiHeader//tei:fileDesc/tei:sourceDesc", NS)
    if sd is None:
        sd = root.find(".//tei:teiHeader//tei:sourceDesc", NS)
    if sd is not None:
        edition_info = _text(sd) or None

    sections: list[dict] = []
    if edition_div is not None:
        sec_divs = [d for d in edition_div.findall(DIV) if d.get("type") == "textpart"]
        if not sec_divs:
            # any direct child div with an n
            sec_divs = [d for d in edition_div.findall(DIV) if d.get("n")]
        if sec_divs:
            for i, sdv in enumerate(sec_divs):
                blocks = _collect_blocks(sdv)
                if blocks:
                    sections.append({
                        "index": i,
                        "label": sdv.get("n") or str(i + 1),
                        "blocks": blocks,
                    })
        else:
            blocks = _collect_blocks(edition_div)
            if blocks:
                sections.append({"index": 0, "label": "1", "blocks": blocks})

    return {"title": title, "edition": edition_info, "sections": sections}


def parse_txt(txt_path) -> dict:
    """Split a plain-text file by blank lines into paragraphs (one section)."""
    text = txt_path.read_text(encoding="utf-8", errors="replace")
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    blocks = [{"kind": "para", "text": p} for p in paras]
    return {"title": None, "sections": [{"index": 0, "label": "1", "blocks": blocks}]}


def leaf_units(xml_path):
    """Citation-level units for text-reuse comparison.

    Returns [{"label", "text"}] for the DEEPEST <div type="textpart"> nodes
    (e.g. book.chapter.section -> "8.6.14"), each with its dotted @n path as
    label. This is the right granularity for finding reused formulae: small,
    localized, and numerous. Falls back to top-level textparts, then to the
    whole edition, for texts without nested textparts (or verse-only).
    """
    root = ET.parse(str(xml_path)).getroot()
    body = root.find(".//tei:body", NS)
    ed = body.find(".//tei:div[@type='edition']", NS) if body is not None else None
    if ed is None:
        ed = body
    if ed is None:
        return []
    units = []

    def walk(el, labels):
        kids = [c for c in el if c.tag == DIV and c.get("type") == "textpart"]
        if kids:
            for c in kids:
                walk(c, labels + [c.get("n") or "?"])
        else:
            txt = _text(el)
            if txt:
                units.append({"label": ".".join(labels), "text": txt})

    tops = [c for c in ed if c.tag == DIV and c.get("type") == "textpart"]
    if tops:
        for c in tops:
            walk(c, [c.get("n") or "?"])
    else:
        txt = _text(ed)
        if txt:
            units.append({"label": "1", "text": txt})
    return units

def parse(path) -> dict:
    if path.suffix == ".xml":
        return parse_tei(path)
    return parse_txt(path)
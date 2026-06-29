"""Perseus Hopper text provider.

Many TLG works are readable on the Perseus Hopper (perseus.tufts.edu/hopper) but
are NOT in the modern First1K CTS inventory (cts.perseids.org), so the repo/CTS
tiers in texts.py cannot read them (e.g. TLG 4029 Procopius). This module makes
those works readable in-app.

Model:
  * Discover: fetch the Hopper page for a candidate CTS URN (work or edition),
    verify it renders Greek text, and parse the statically-present Table of
    Contents for `Perseus:text:<id>:book=N:chapter=M` passage refs.
  * Sections = distinct (book, chapter) pairs.
  * Read one chapter on demand: fetch its Hopper page and extract the Greek
    text from the per-word morph-analysis anchors (<a class="text">WORD</a>).

Hopper pages are large (~1.2 MB, mostly the embedded TOC); results are cached.
"""
from __future__ import annotations

import re
import urllib.parse
import urllib.request

from . import canon

UA = "KONI/0.1 (reader; Hopper integration)"
HOPPER = "https://www.perseus.tufts.edu/hopper/text?doc="

_ANCHOR_RE = re.compile(r'<a [^>]*class="text"[^>]*>([^<]*)</a>')
# URL-encoded TOC passage refs: Perseus%3Atext%3A<id>%3Abook%3D<n>%3Achapter%3D<m>
_REF_RE = re.compile(r"Perseus%3Atext%3A([0-9.]+)%3Abook%3D(\d+)%3Achapter%3D(\d+)")
_GREEK_RE = re.compile(r"[ἀ-῿]")
_WS_RE = re.compile(r"\s+")


def _get(doc: str) -> str | None:
    url = HOPPER + urllib.parse.quote(doc, safe=":.=")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        return urllib.request.urlopen(req, timeout=120).read().decode(
            "utf-8", "replace")
    except Exception:
        return None


def _anchors_text(html: str) -> str:
    words = [w for w in _ANCHOR_RE.findall(html) if w.strip()]
    return _WS_RE.sub(" ", " ".join(words)).strip()


def _greek_edition_urn(aid: str, wid: str) -> str | None:
    w = canon.cts_index().get(aid, {}).get("works", {}).get(wid, {})
    return w.get("greek_edition_urn")


def _candidates(aid: str, wid: str) -> list[str]:
    cands: list[str] = []
    ge = _greek_edition_urn(aid, wid)
    if ge:
        cands.append(ge)
    for suf in ("perseus-grc1", "perseus-grc2", "perseus-grc3"):
        cands.append(f"urn:cts:greekLit:tlg{aid}.tlg{wid}.{suf}")
    cands.append(f"urn:cts:greekLit:tlg{aid}.tlg{wid}")  # work URN fallback
    # de-dup preserving order
    seen = set(); out = []
    for c in cands:
        if c not in seen:
            seen.add(c); out.append(c)
    return out


def discover(aid: str, wid: str) -> dict | None:
    """Find the Hopper Greek edition and its chapter list for a work."""
    for doc in _candidates(aid, wid):
        html = _get(doc)
        if not html:
            continue
        text = _anchors_text(html)
        if len(text) < 30 or not _GREEK_RE.search(text):
            continue
        refs = _REF_RE.findall(html)  # (id, book, chapter)
        if not refs:
            continue
        # pick the Perseus:text id that owns the most passage refs
        from collections import Counter
        ids = Counter(r[0] for r in refs)
        pid = ids.most_common(1)[0][0]
        bc = sorted({(int(b), int(c)) for (i, b, c) in refs if i == pid},
                    key=lambda t: t)
        sections = [{"index": k, "label": f"{b}.{c}", "book": b, "chapter": c}
                    for k, (b, c) in enumerate(bc)]
        if not sections:
            continue
        return {"perseus_id": pid, "sections": sections}
    return None


def read_section(pid: str, book: int, chapter: int) -> list[dict]:
    doc = f"Perseus:text:{pid}:book={book}:chapter={chapter}"
    html = _get(doc)
    if not html:
        return []
    text = _anchors_text(html)
    return [{"kind": "para", "text": text}] if text else []
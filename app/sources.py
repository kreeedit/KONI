"""Multi-source text discovery for a TLG work.

For each (author_id, work_id) we discover where the text / a scan / metadata
exists, in a reliability order, and mark the sources. Three tiers:

  Tier 1 — authoritative, constructable (always present for confirmed works):
    scaife            readable Greek text online (Scaife / Perseus)   rank 1
    perseus-catalog   edition/metadata catalogue page                 rank 2

  Tier 2 — API-discovered real hits (cached, fuzzy — marked "discovered"):
    wikisource        open text pages (often translations)             rank 3
    archive-org       scanned editions (Internet Archive)             rank 4

  Tier 3 — search links (sources whose API is blocked / key-gated from this
  host; the link works in a browser but a hit is not guaranteed):
    bsb               Bayerische Staatsbibliothek digitale Sammlungen rank 5
    google-books      Google Books search                             rank 6
    hathitrust        HathiTrust catalog search                       rank 7
    gallica           BnF Gallica search                              rank 8

Results are cached per work under data/intermediate/sources/<aid>_<wid>.json.
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

from . import canon

UA = "KONI/0.1 (source discovery; local classics browser)"
CACHE_DIR = canon.REPO / "data" / "intermediate" / "sources"


def _cache_path(aid: str, wid: str) -> Path:
    return CACHE_DIR / f"{aid}_{wid}.json"


def _get(url: str, timeout: int = 30) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA,
                                     "Accept": "application/json"})
        return urllib.request.urlopen(req, timeout=timeout).read()
    except Exception:
        return None


def _get_html(url: str, timeout: int = 30):
    """Fetch HTML; return (status, body) so callers can distinguish 404."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA,
                                     "Accept": "text/html"})
        r = urllib.request.urlopen(req, timeout=timeout)
        return r.getcode(), r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception:
        return 0, b""


def _query(author: dict, work: dict) -> str:
    """Best-effort search query string for the work."""
    a = (author.get("author_name_english") or author.get("author_name_latin")
         or "").strip()
    t = (work.get("title_english") or work.get("title_latin")
         or work.get("title_greek") or "").strip()
    return " ".join(p for p in (a, t) if p)


# ---- tier 1: Perseus (Hopper + Scaife + catalog) ----
_HOPPER_RE = re.compile(r"hopper/text(?:\.jsp)?\?doc=(Perseus:text:[0-9.]+)")


def _perseus(aid: str, wid: str, work: dict) -> list[dict]:
    """Perseus coverage for a work. The Perseus Hopper (perseus.tufts.edu)
    accepts the CTS URN and the Perseus catalog page lists the matching
    Hopper text — this covers works (e.g. TLG 4029 Procopius) that are on the
    old Hopper but NOT in the modern CTS GetCapabilities inventory."""
    urn = work.get("cts_urn") or f"urn:cts:greekLit:tlg{aid}.tlg{wid}"
    confirmed = bool(work.get("cts_confirmed"))
    cat_url = f"https://catalog.perseus.org/catalog/{urn}"
    status, body = _get_html(cat_url)
    html = body.decode("utf-8", "replace") if body else ""
    hopper_docs = _HOPPER_RE.findall(html)

    out = []
    # primary readable Perseus text (old Hopper) — confirmed when the catalog
    # lists a Hopper link, even if the work isn't in the modern CTS inventory.
    if hopper_docs:
        doc = hopper_docs[0]
        out.append({
            "id": "perseus-hopper", "label": "Perseus Hopper (Greek text)",
            "rank": 1, "type": "text", "kind": "confirmed",
            "url": f"https://www.perseus.tufts.edu/hopper/text?doc="
                   + urllib.parse.quote(doc, safe=":."),
            "detail": "Readable text on the Perseus Hopper (perseus.tufts.edu).",
        })
    # modern CTS readable text (Scaife)
    if confirmed:
        out.append({
            "id": "scaife", "label": "Scaife / Perseus (Greek text, modern CTS)",
            "rank": 2, "type": "text", "kind": "confirmed",
            "url": f"https://scaife.perseus.org/reader/{urn}/",
            "detail": "Readable Greek text (Scaife / First1K CTS).",
        })
    # catalogue page — only when Perseus actually has an entry (200)
    if status == 200:
        out.append({
            "id": "perseus-catalog", "label": "Perseus catalog (metadata)",
            "rank": 3, "type": "metadata", "kind": "confirmed",
            "url": cat_url,
            "detail": "Edition/metadata in the Perseus catalog.",
        })
    return out


# ---- tier 2: API discovery ----
def _archive_org(q: str) -> list[dict]:
    api = ("https://archive.org/advancedsearch.php?q=" +
           urllib.parse.quote(q) +
           "&fl[]=identifier&fl[]=title&fl[]=creator&fl[]=date"
           "&sort[]=date%20desc&rows=5&output=json")
    raw = _get(api, timeout=30)
    if not raw:
        return []
    try:
        docs = json.loads(raw)["response"]["docs"]
    except Exception:
        return []
    out = []
    for d in docs:
        ident = d.get("identifier")
        if not ident:
            continue
        creator = d.get("creator")
        if isinstance(creator, list):
            creator = ", ".join(creator)
        out.append({
            "id": "archive-org", "label": d.get("title", "Internet Archive")[:120],
            "rank": 5, "type": "scan", "kind": "discovered",
            "url": f"https://archive.org/details/{ident}",
            "detail": f"{creator or ''} {d.get('date', '')}".strip(),
        })
    return out


def _wikisource(q: str) -> list[dict]:
    api = ("https://en.wikisource.org/w/api.php?action=query&list=search"
           "&srsearch=" + urllib.parse.quote(q) + "&format=json&srlimit=4")
    raw = _get(api, timeout=30)
    if not raw:
        return []
    try:
        hits = json.loads(raw)["query"]["search"]
    except Exception:
        return []
    out = []
    for h in hits:
        title = h["title"]
        out.append({
            "id": "wikisource", "label": title,
            "rank": 4, "type": "text", "kind": "discovered",
            "url": "https://en.wikisource.org/wiki/" +
                   urllib.parse.quote(title.replace(" ", "_")),
            "detail": "Wikisource (often a translation).",
        })
    return out


# ---- tier 3: search links ----
def _search_links(q: str) -> list[dict]:
    enc = urllib.parse.quote(q)
    return [
        {"id": "bsb", "label": "Bayerische Staatsbibliothek (digitale Sammlungen)",
         "rank": 6, "type": "scan", "kind": "search",
         "url": f"https://www.digitale-sammlungen.de/de/search?query={enc}",
         "detail": "Search link — a successful hit is not guaranteed."},
        {"id": "google-books", "label": "Google Books",
         "rank": 7, "type": "scan", "kind": "search",
         "url": f"https://www.google.com/search?tbm=bks&q={enc}",
         "detail": "Search link."},
        {"id": "hathitrust", "label": "HathiTrust",
         "rank": 8, "type": "scan", "kind": "search",
         "url": f"https://catalog.hathitrust.org/Search/Results?q={enc}",
         "detail": "Search link."},
        {"id": "gallica", "label": "BnF Gallica",
         "rank": 9, "type": "scan", "kind": "search",
         "url": f"https://gallica.bnf.fr/Search?q={enc}",
         "detail": "Search link."},
    ]


def discover(aid: str, wid: str) -> dict:
    """Return discovered sources for a work, cached on disk."""
    cp = _cache_path(aid, wid)
    if cp.exists():
        try:
            return json.loads(cp.read_text(encoding="utf-8"))
        except Exception:
            pass

    author = canon.canon().get(aid, {})
    work = (canon.canon().get(aid, {}).get("works", {}).get(wid) or {})
    q = _query(author, work)

    sources = _perseus(aid, wid, work)
    # API discovery (rate-limit politely)
    ws = _wikisource(q)
    ia = _archive_org(q)
    sources += ws[:4] + ia[:5] + _search_links(q)
    sources.sort(key=lambda s: (s["rank"], -len(s.get("detail", ""))))

    result = {"aid": aid, "wid": wid, "query": q, "sources": sources}
    cp.parent.mkdir(parents=True, exist_ok=True)
    cp.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return result
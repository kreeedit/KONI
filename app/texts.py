"""Text access for the reader.

Two-tier lazy download + cache, so any `cts_confirmed` work is readable:
  Tier 1: fetch the TEI from PerseusDL/canonical-greekLit via the edition URN
          (fast; covers the Perseus-edited texts).
  Tier 2: CTS GetValidReff + GetPassage via cts.perseids.org (universal; covers
          First1K and any other confirmed work). The assembled text is cached as
          JSON under data/texts/tlg<aid>/tlg<wid>.json.

Parsed texts are cached in memory; local files (xml/txt/json) are reused.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from . import canon
from . import repo
from . import tei
from . import hopper

TEI = "http://www.tei-c.org/ns/1.0"
CTS_API = "https://cts.perseids.org/api/cts"
PERSEUS_RAW = ("https://raw.githubusercontent.com/PerseusDL/canonical-greekLit/"
               "master/data/tlg{aid}/tlg{wid}/{short}.xml")
UA = "KONI/0.1 (reader; local classics browser)"
_CACHE: dict[tuple[str, str], dict] = {}


def _local_paths(aid: str, wid: str) -> dict[str, Path]:
    base = canon.TEXTS_DIR / f"tlg{aid}" / f"tlg{wid}"
    return {"xml": base.with_suffix(".xml"), "txt": base.with_suffix(".txt"),
            "json": base.with_suffix(".json")}


def find_local(aid: str, wid: str) -> tuple[Path, str] | None:
    paths = _local_paths(aid, wid)
    for kind in ("xml", "txt", "json"):
        if paths[kind].exists():
            return paths[kind], kind
    return None


def _edition_urn(aid: str, wid: str) -> str | None:
    w = canon.cts_index().get(aid, {}).get("works", {}).get(wid, {})
    return w.get("greek_edition_urn")


def _urn_work(aid: str, wid: str) -> str:
    return f"urn:cts:greekLit:tlg{aid}.tlg{wid}"


# ---- tier 1: raw GitHub TEI from PerseusDL/canonical-greekLit ----
def _fetch_tier1(aid: str, wid: str) -> Path | None:
    # Primary: resolve the Greek-edition filename from the repo tree (covers
    # works NOT in the CTS inventory too, e.g. TLG 4029 Procopius).
    url = repo.greek_xml_url(aid, wid)
    if not url:
        # Fallback: synthesize from the CTS inventory edition URN if known.
        urn = _edition_urn(aid, wid)
        if not urn:
            return None
        short = urn.split(":")[-1]
        url = PERSEUS_RAW.format(aid=aid, wid=wid, short=short)
    dst = _local_paths(aid, wid)["xml"]
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        data = urllib.request.urlopen(req, timeout=120).read()
        if len(data) < 200:  # bogus/404-txt responses
            return None
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
        return dst
    except Exception:
        return None


# ---- tier 2: CTS GetValidReff + GetPassage ----
def _cts(params: dict) -> bytes:
    url = CTS_API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=120).read()


def _valid_refs(work_urn: str) -> list[str]:
    try:
        x = _cts({"request": "GetValidReff", "urn": work_urn, "level": "1"})
    except Exception:
        return []
    root = ET.fromstring(x)
    ns = {"cts": "http://chs.harvard.edu/xmlns/cts"}
    return [u.text for u in root.findall(".//cts:urn", ns) if u.text]


def _blocks_from_passage(xml: bytes) -> list[dict]:
    root = ET.fromstring(xml)
    L, P, HEAD = f"{{{TEI}}}l", f"{{{TEI}}}p", f"{{{TEI}}}head"
    blocks: list[dict] = []
    for el in root.iter():
        if el.tag == HEAD:
            t = tei._text(el)
            if t:
                blocks.append({"kind": "head", "text": t})
        elif el.tag == L:
            n = el.get("n")
            t = tei._text(el)
            if t:
                blocks.append({"kind": "line", "n": n, "text": t})
        elif el.tag == P:
            t = tei._text(el)
            if t:
                blocks.append({"kind": "para", "text": t})
    return blocks


def _fetch_tier2(aid: str, wid: str) -> dict | None:
    refs = _valid_refs(_urn_work(aid, wid))
    if not refs:
        return None
    sections: list[dict] = []
    for i, ref in enumerate(refs):
        try:
            xml = _cts({"request": "GetPassage", "urn": ref})
        except Exception:
            continue
        blocks = _blocks_from_passage(xml)
        if blocks:
            sections.append({"index": i, "label": ref.rsplit(":", 1)[-1],
                              "blocks": blocks})
    if not sections:
        return None
    parsed = {"title": None, "sections": sections}
    # persist as JSON cache
    dst = _local_paths(aid, wid)["json"]
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(parsed, ensure_ascii=False), encoding="utf-8")
    return parsed


# ---- main entry ----
# Per-work provider: 'tei' (repo/CTS, fully pre-parsed) or 'hopper' (lazy).
_PROVIDER: dict[tuple, str] = {}
_HOPPER: dict[tuple, dict] = {}       # (aid,wid) -> hopper discover result
_HOPPER_BLOCKS: dict[tuple, list] = {}  # (aid,wid,idx) -> blocks
_HCACHE = canon.REPO / "data" / "intermediate" / "hopper"  # disk cache for hopper


def _hcache_disc(aid: str, wid: str) -> Path:
    return _HCACHE / f"{aid}_{wid}.json"


def _hcache_sec(aid: str, wid: str, idx: int) -> Path:
    return _HCACHE / f"{aid}_{wid}_{idx}.json"


def _tei_parsed(aid: str, wid: str) -> dict | None:
    """Local file / tier1 repo / tier2 CTS — fully pre-parsed text."""
    key = (aid, wid)
    if key in _CACHE:
        return _CACHE[key]
    local = find_local(aid, wid)
    if local is not None:
        path, kind = local
        if kind == "json":
            try:
                parsed = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                parsed = None
        else:
            try:
                parsed = tei.parse(path)
            except Exception:
                parsed = None
        if parsed:
            _CACHE[key] = parsed
            return parsed
    path = _fetch_tier1(aid, wid)
    if path is not None:
        try:
            parsed = tei.parse(path)
            if parsed:
                _CACHE[key] = parsed
                return parsed
        except Exception:
            pass
    parsed = _fetch_tier2(aid, wid)
    if parsed:
        _CACHE[key] = parsed
        return parsed
    return None


def _resolve(aid: str, wid: str) -> bool:
    """Determine provider. Return True if the work is readable via any tier."""
    key = (aid, wid)
    if key in _PROVIDER:
        return True
    if _tei_parsed(aid, wid) is not None:
        _PROVIDER[key] = "tei"
        return True
    # Hopper fallback (disk-cached discover).
    disc = None
    cp = _hcache_disc(aid, wid)
    if cp.exists():
        try:
            disc = json.loads(cp.read_text(encoding="utf-8"))
        except Exception:
            disc = None
    if disc is None:
        disc = hopper.discover(aid, wid)
        if disc:
            cp.parent.mkdir(parents=True, exist_ok=True)
            cp.write_text(json.dumps(disc, ensure_ascii=False), encoding="utf-8")
    if disc:
        _HOPPER[key] = disc
        _PROVIDER[key] = "hopper"
        return True
    return False


def sections(aid: str, wid: str) -> dict:
    if not _resolve(aid, wid):
        return {"has_text": False, "readable": False, "title": None, "sections": []}
    if _PROVIDER[(aid, wid)] == "tei":
        parsed = _tei_parsed(aid, wid)
        secs = [{"index": s["index"], "label": s["label"],
                 "block_count": len(s["blocks"])} for s in parsed["sections"]]
        return {"has_text": True, "readable": True, "title": parsed.get("title"),
                "edition": parsed.get("edition"), "sections": secs}
    disc = _HOPPER[(aid, wid)]
    secs = [{"index": s["index"], "label": s["label"], "block_count": 1}
            for s in disc["sections"]]
    return {"has_text": True, "readable": True, "title": None, "edition": None,
            "sections": secs}


def section(aid: str, wid: str, idx: int) -> dict | None:
    if not _resolve(aid, wid):
        return None
    if _PROVIDER[(aid, wid)] == "tei":
        parsed = _tei_parsed(aid, wid)
        for s in parsed["sections"]:
            if s["index"] == idx:
                return {"index": s["index"], "label": s["label"],
                        "blocks": s["blocks"]}
        return None
    # hopper: fetch the chapter on demand, cache the blocks (memory + disk)
    bkey = (aid, wid, idx)
    if bkey in _HOPPER_BLOCKS:
        blocks = _HOPPER_BLOCKS[bkey]
    else:
        cp = _hcache_sec(aid, wid, idx)
        if cp.exists():
            try:
                blocks = json.loads(cp.read_text(encoding="utf-8")).get("blocks", [])
            except Exception:
                blocks = []
        else:
            disc = _HOPPER[(aid, wid)]
            sec = next((s for s in disc["sections"] if s["index"] == idx), None)
            if not sec:
                return None
            blocks = hopper.read_section(disc["perseus_id"], sec["book"], sec["chapter"])
            cp.parent.mkdir(parents=True, exist_ok=True)
            cp.write_text(json.dumps({"blocks": blocks}, ensure_ascii=False),
                          encoding="utf-8")
        _HOPPER_BLOCKS[bkey] = blocks
    disc = _HOPPER[(aid, wid)]
    label = next((s["label"] for s in disc["sections"] if s["index"] == idx), str(idx))
    return {"index": idx, "label": label, "blocks": blocks}


_MILESTONE_RE = re.compile(r"[\(\[][0-9]+[\)\]]")


def _clean_text(t: str) -> str:
    """Strip editorial milestone refs (page/line numbers like (15), [2]) so they
    don't break n-gram sequences in the Flame comparison."""
    return re.sub(r"\s+", " ", _MILESTONE_RE.sub("", t)).strip()


def section_texts(aid: str, wid: str) -> list[dict] | None:
    """Comparison units of a work as [{label, text}] for the Flame text-reuse
    engine. Now emits FINE citation-level units (deepest TEI textpart), not
    whole books, and windows any oversized leaf to <= MAX_UNIT_WORDS so flat /
    verse texts also stay small. Returns None if the work is not readable."""
    if not _resolve(aid, wid):
        return None
    raw: list[dict] = []
    if _PROVIDER[(aid, wid)] == "tei":
        # Prefer fine-grained citation units straight from the TEI XML.
        xml_path = None
        local = find_local(aid, wid)
        if local is not None and local[1] == "xml":
            xml_path = local[0]
        else:
            p = _local_paths(aid, wid)["xml"]   # tier1 caches to this path
            if p.exists():
                xml_path = p
        if xml_path is not None:
            try:
                units = tei.leaf_units(xml_path)
            except Exception:
                units = None
            if units:
                raw = [{"label": u["label"], "text": _clean_text(u["text"])}
                       for u in units]
        if not raw:
            # tier2 (CTS JSON) or unusual TEI: fall back to parsed sections.
            parsed = _tei_parsed(aid, wid)
            for s in parsed["sections"]:
                raw.append({"label": s["label"],
                            "text": _clean_text(
                                " ".join(b.get("text", "") for b in s["blocks"]))})
    else:
        disc = _HOPPER[(aid, wid)]
        for s in disc["sections"]:
            sec = section(aid, wid, s["index"])
            if sec:
                raw.append({"label": s["label"],
                            "text": _clean_text(
                                " ".join(b.get("text", "") for b in sec["blocks"]))})
    return _window_units(raw)


# ---- comparison-unit windowing (keeps each Flame unit small & local) -------
MAX_UNIT_WORDS = 140    # split any unit longer than this into windows
UNIT_OVERLAP = 25       # window overlap so a formula on a boundary survives


def _window_units(units: list[dict]) -> list[dict]:
    """Split oversized units into overlapping word-windows; small units pass
    through unchanged. Window labels get a #k suffix (e.g. '1.2#3')."""
    out: list[dict] = []
    step = max(1, MAX_UNIT_WORDS - UNIT_OVERLAP)
    for u in units:
        words = u["text"].split()
        if len(words) <= MAX_UNIT_WORDS:
            out.append(u)
            continue
        part = 1
        for k in range(0, len(words), step):
            chunk = words[k:k + MAX_UNIT_WORDS]
            if not chunk:
                break
            out.append({"label": f'{u["label"]}#{part}', "text": " ".join(chunk)})
            part += 1
            if k + MAX_UNIT_WORDS >= len(words):
                break
    return out

"""Load the canon and provide search/filter for the API.

Holds canon.json (display metadata) and cts_index.json (edition URNs for text
fetching) in memory. Search matches author Latin/Greek/English names, the TLG
author ID, epitheton, and any work title.
"""
from __future__ import annotations

import re
from pathlib import Path

import json as _json

from common import CANON_JSON, INT_CTS, REPO, read_json

TEXTS_DIR = REPO / "data" / "texts"
REPO_MAP_PATH = REPO / "data" / "intermediate" / "greekLit_map.json"

_CTS_INDEX: dict = {}
_CANON: dict = {}
_AUTHORS: list[dict] = []  # slim list for search
_REPO_KEYS: set[str] = set()


def _load_repo_keys() -> set[str]:
    if not REPO_MAP_PATH.exists():
        return set()
    try:
        return set(_json.loads(REPO_MAP_PATH.read_text(encoding="utf-8")).keys())
    except Exception:
        return set()


def is_readable(aid: str, wid: str, work: dict) -> bool:
    """A work is readable if it has a downloadable open Greek text:
    confirmed in the Perseus CTS inventory, OR present in the
    PerseusDL/canonical-greekLit repo map, OR already cached locally."""
    if work.get("cts_confirmed"):
        return True
    if f"{aid}_{wid}" in _REPO_KEYS:
        return True
    if has_local_text(aid, wid):
        return True
    return False


def load() -> None:
    global _CANON, _CTS_INDEX, _AUTHORS, _REPO_KEYS
    _CANON = read_json(CANON_JSON) if CANON_JSON.exists() else {}
    _CTS_INDEX = read_json(INT_CTS) if INT_CTS.exists() else {}
    _REPO_KEYS = _load_repo_keys()
    _AUTHORS = []
    for aid, a in _CANON.items():
        works = a.get("works", {})
        readable = sum(1 for wid, w in works.items() if is_readable(aid, wid, w))
        names = [
            a.get("author_name_latin") or "",
            a.get("author_name_greek") or "",
            a.get("author_name_english") or "",
        ]
        blob = "  ".join(names) + "  " + (a.get("epitheton") or "") + "  " + aid
        _AUTHORS.append({
            "author_id": aid,
            "author_name_latin": a.get("author_name_latin"),
            "author_name_greek": a.get("author_name_greek"),
            "author_name_english": a.get("author_name_english"),
            "epitheton": a.get("epitheton"),
            "era": a.get("era"),
            "work_count": len(works),
            "readable_count": readable,
            "_blob": blob.lower(),
        })


def canon() -> dict:
    return _CANON


def cts_index() -> dict:
    return _CTS_INDEX


def get_author(aid: str) -> dict | None:
    a = _CANON.get(aid)
    if not a:
        return None
    # attach readable / local_text flags per work for the frontend
    works = []
    for wid in sorted(a.get("works", {})):
        w = dict(a["works"][wid])
        w["has_local_text"] = has_local_text(aid, wid)
        w["readable"] = is_readable(aid, wid, a["works"][wid])
        works.append(w)
    out = dict(a)
    out["works"] = works
    return out


def has_local_text(aid: str, wid: str) -> bool:
    return text_path(aid, wid) is not None


def text_path(aid: str, wid: str) -> Path | None:
    for ext in (".xml", ".txt", ".json"):
        p = TEXTS_DIR / f"tlg{aid}" / f"tlg{wid}{ext}"
        if p.exists():
            return p
    return None


def search(q: str, limit: int = 50) -> list[dict]:
    q = q.strip().lower()
    if not q:
        # default: return a representative alphabetical slice
        out = [ {k:v for k,v in a.items() if k!="_blob"} for a in _AUTHORS[:limit] ]
        return out
    # numeric -> exact/prefix ID match first
    if re.fullmatch(r"\d{1,4}", q):
        qid = q.zfill(4)
        exact = [a for a in _AUTHORS if a["author_id"] == qid]
        prefix = [a for a in _AUTHORS if a["author_id"].startswith(qid) and a["author_id"] != qid]
        ordered = exact + prefix
        return [ {k:v for k,v in a.items() if k!="_blob"} for a in ordered[:limit] ]
    matches = [a for a in _AUTHORS if q in a["_blob"]]
    # rank: ID-prefix first, then name-startswith, then substring
    def key(a):
        blob = a["_blob"]
        return (
            0 if a["author_id"].startswith(q) else 1,
            0 if (a.get("author_name_latin") or "").lower().startswith(q) else 1,
            0 if (a.get("author_name_english") or "").lower().startswith(q) else 1,
        )
    matches.sort(key=key)
    return [ {k:v for k,v in a.items() if k!="_blob"} for a in matches[:limit] ]


load()
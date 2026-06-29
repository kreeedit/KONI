"""Perseus canonical-greekLit GitHub repository map.

The PerseusDL/canonical-greekLit repo holds the source TEI for Perseus Greek
texts (the clean, fast source — far better than scraping the Hopper HTML).
Every work lives at:

    data/tlg<aid>/tlg<wid>/<aid>.<wid>.<edition>.xml   e.g. tlg4029.tlg001.perseus-grc2.xml

This module builds a (author_id, work_id) -> Greek-edition filename map from the
repo's recursive tree (one GitHub API call, cached on disk), so texts.py can
fetch the correct Greek TEI WITHOUT depending on the CTS GetCapabilities
inventory (which misses many works that ARE in the repo, e.g. TLG 4029).

The map is built lazily on first use (or by scripts/build_repo_map.py) and
cached at data/intermediate/greekLit_map.json.
"""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

from . import canon

UA = "KONI/0.1 (repo map builder)"
TREE_URL = ("https://api.github.com/repos/PerseusDL/canonical-greekLit/"
            "git/trees/master?recursive=1")
RAW = ("https://raw.githubusercontent.com/PerseusDL/canonical-greekLit/"
       "master/data/tlg{aid}/tlg{wid}/{fname}")
MAP_PATH = canon.REPO / "data" / "intermediate" / "greekLit_map.json"

_PATH_RE = re.compile(r"^data/tlg(\d{4})/tlg(\d{3})/([^/]+\.xml)$")
_map: dict[str, str] | None = None


def _pick_greek(files: list[str]) -> str | None:
    """Choose the Greek edition file (contains 'grc', not an English 'eng')."""
    grc = [f for f in files if "grc" in f and "eng" not in f]
    if grc:
        # prefer 1st1K then perseus editions; else first grc
        for pref in ("1st1K-grc", "perseus-grc", "grc"):
            for f in grc:
                if pref in f:
                    return f
        return grc[0]
    non_eng = [f for f in files if "eng" not in f]
    return non_eng[0] if non_eng else None


def build_map() -> dict[str, str]:
    """Fetch the repo tree and build the (aid_wid -> greek filename) map."""
    req = urllib.request.Request(TREE_URL, headers={"User-Agent": UA,
                                 "Accept": "application/vnd.github+json"})
    data = urllib.request.urlopen(req, timeout=120).read()
    tree = json.loads(data).get("tree", [])
    by_work: dict[str, list[str]] = {}
    for e in tree:
        m = _PATH_RE.match(e.get("path", ""))
        if not m:
            continue
        aid, wid, fname = m.groups()
        by_work.setdefault(f"{aid}_{wid}", []).append(fname)
    gmap = {}
    for key, files in by_work.items():
        g = _pick_greek(files)
        if g:
            gmap[key] = g
    MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    MAP_PATH.write_text(json.dumps(gmap, ensure_ascii=False), encoding="utf-8")
    return gmap


def load() -> dict[str, str]:
    global _map
    if _map is not None:
        return _map
    if MAP_PATH.exists():
        try:
            _map = json.loads(MAP_PATH.read_text(encoding="utf-8"))
            return _map
        except Exception:
            pass
    try:
        _map = build_map()
    except Exception as exc:  # noqa: BLE001
        canon.log(f"repo: WARNING could not build greekLit map: {exc}")
        _map = {}
    return _map


def has_repo_text(aid: str, wid: str) -> bool:
    return f"{aid}_{wid}" in load()


def greek_xml_url(aid: str, wid: str) -> str | None:
    fname = load().get(f"{aid}_{wid}")
    if not fname:
        return None
    return RAW.format(aid=aid, wid=wid, fname=fname)


def greek_xml_filename(aid: str, wid: str) -> str | None:
    return load().get(f"{aid}_{wid}")
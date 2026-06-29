"""Shared paths and helpers for the KONI pipeline."""
from __future__ import annotations

import json
import sys
from pathlib import Path

# scripts/common.py -> repo root is one level up
REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
RAW = DATA / "raw"
INTERMEDIATE = DATA / "intermediate"
REPORTS = REPO / "reports"
SCHEMA = REPO / "schema"

# Source file locations (cached downloads)
RAW_CD = RAW / "cd.authors.html"
RAW_POST = RAW / "post_tlg_e.html"
RAW_CTS = RAW / "cts_capabilities.xml"
RAW_BCD = RAW / "main_list.md"

# Intermediate parsed JSON
INT_CLASSIC = INTERMEDIATE / "authors_classic.json"
INT_POSTE = INTERMEDIATE / "authors_poste.json"
INT_CTS = INTERMEDIATE / "cts_index.json"
INT_BCD = INTERMEDIATE / "bcd_works.json"
INT_WIKIDATA = INTERMEDIATE / "wikidata_era.json"

# Final outputs
CANON_JSON = DATA / "canon.json"
CANON_CSV = DATA / "canon.csv"

USER_AGENT = "KONI/0.1 (digital-classics open canon; https://github.com/opentgl)"

# Source tags used in the per-author `source` audit list
SRC_TLG_CD = "tlg:cd"
SRC_TLG_POST = "tlg:post-e"
SRC_CTS = "cts:perseids"
SRC_BCD = "bcdavasconcelos"
SRC_WIKIDATA = "wikidata"


def ensure_dirs() -> None:
    for d in (RAW, INTERMEDIATE, REPORTS):
        d.mkdir(parents=True, exist_ok=True)


def read_json(path: Path):
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)
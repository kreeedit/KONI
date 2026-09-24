"""The reading aid: LSJ definitions looked up from a form in a text.

WHAT IT IS FOR
--------------
The reader sees `ἔξασμαι` in a text and needs to know it is a form of ξαίνω,
"to card wool". Two halves already exist and this is the join between them:

  * `lemmas_pure.candidates(form)` answers form -> lemma, from a table of
    endings, and knows the grammar ("perfect, 2nd person singular").
  * the LSJ index built by `scripts/build_lexicon.py` answers lemma -> gloss,
    from the real dictionary.

So the lookup is a CHAIN, and it reports which link answered. A word that LSJ
lists as a cited form is answered directly; a word that only the morphological
table can reduce is answered through its lemma, with the reading attached so
the reader can judge it. The chain is never hidden: `match` says which step
produced the entry, and `analysis` carries the grammar when there was any.

WHERE THE DATA LIVES, AND WHY IT IS GENERATED
---------------------------------------------
`data/lexicon/out/` — 27 slice files plus a `lookup.json` that maps a
normalised form to the slice holding it, so a lookup opens one slice and never
the other 26. Neither is in git and neither is fetched at runtime: the build
is a separate, resumable step (`scripts/fetch_lsj.sh`, then
`scripts/build_lexicon.py`), and the app runs offline against whatever was
built. If nothing was built, `available()` says so and the lookup returns None
— the reader keeps working, minus the dictionary panel.

The 330 MB of source XML is never read by this module, only by the builder,
and it is not read as data even there: it is parsed as XML with the headword,
gloss and cited forms taken out, and the rest discarded as it streams past.

LICENCE. LSJ is CC BY-SA 4.0 and the attribution is carried in the manifest
and served with the data, because a share-alike dictionary that does not say
where it came from is a licence violation, not an omission.
"""
from __future__ import annotations

import json
import os

from . import lemmas_pure
from .flame_pure import normalize
from .variants import BY_NAME as _VARIANT_RULES
from .variants import unify as _unify

# The spelling variants the rest of the app pools, applied here for the same
# reason it applies them there: Thucydides writes ξυμμάχων where the dictionary
# has σύμμαχος, and the morphological table returns the lemma in the AUTHOR's
# spelling (ξυμμαχος). Without folding the two, a lookup for ξυμμάχων misses a
# dictionary that has the word — it is filed under the Attic spelling.
_RULES = tuple(_VARIANT_RULES)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "data", "lexicon", "out")

# Slices are 0.1-5 MB each. Four in memory covers a paragraph of reading
# without ever pinning the whole 31 MB index for a single clicked word.
SLICE_CACHE = 4

_index: dict | None = None
_index_forms: dict | None = None
_slices: dict[str, dict] = {}
_missing = object()


def _load_index() -> bool:
    """Read lookup.json once. False if the lexicon was never built."""
    global _index, _index_forms
    if _index is not None:
        return True
    path = os.path.join(OUT, "lookup.json")
    if not os.path.exists(path):
        _index, _index_forms = {}, {}
        return False
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    _index = data.get("index", {})
    _index_forms = data.get("index_forms", {})
    return True


def _slice(nn: str) -> dict | None:
    """One slice, cached, evicted oldest-first."""
    if nn in _slices:
        return _slices[nn]
    path = os.path.join(OUT, f"{nn}.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if len(_slices) >= SLICE_CACHE:
        _slices.pop(next(iter(_slices)))
    _slices[nn] = data
    return data


def _entry(nn: str, pos: int) -> dict | None:
    data = _slice(nn)
    if data is None or not 0 <= pos < len(data["entries"]):
        return None
    return data["entries"][pos]


def manifest() -> dict | None:
    path = os.path.join(OUT, "manifest.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def available() -> dict:
    """What the app can say about the dictionary before looking anything up."""
    man = manifest()
    if man is None:
        return {"ready": False, "how": "python3 scripts/build_lexicon.py"}
    src = man.get("source", {})
    return {
        "ready": True,
        "n_entries": man.get("n_entries", 0),
        "n_index": man.get("n_index", 0),
        "n_slices": len(man.get("slices", [])),
        "source": src.get("name", ""),
        "license": src.get("license", ""),
        "attribution": src.get("attribution", ""),
        "link_pattern": man.get("link_pattern", ""),
    }


def _variants(key: str) -> list[str]:
    """The key itself, then the pooled spelling if it differs."""
    try:
        pooled = _unify(key, _RULES)
    except Exception:                       # noqa: BLE001 — never break a lookup
        return [key]
    return [key] if pooled == key else [key, pooled]


def _find(key: str) -> tuple[dict | None, str | None]:
    """(entry, how) for a normalised key. Headwords before cited forms.

    `lookup.json` gives the slice; the position comes from that slice's own
    index, so a slice and its index can never disagree about which entry is
    meant. Each spelling variant is tried in both tiers before moving on, so
    the author's spelling and the dictionary's never have to be the same one.
    """
    for cand in _variants(key):
        for tier, how in ((_index, "head"), (_index_forms, "form")):
            nn = tier.get(cand)
            if not nn:
                continue
            data = _slice(nn)
            if data is None:
                continue
            local = data["index"] if how == "head" \
                else data.get("index_forms", {})
            pos = local.get(cand)
            if pos is None:
                continue
            entry = _entry(nn, pos)
            if entry:
                return entry, how
    return None, None


def lookup(form: str) -> dict | None:
    """A form from a text -> a dictionary entry, or None.

    Direct hit first (LSJ's own headword or a form it cites); failing that, the
    form is reduced by `lemmas_pure` and each candidate lemma is looked up. The
    result says which route answered:

        match = "head"   the word IS the headword
        match = "form"   LSJ cites it as an inflected form of this entry
        match = "lemma"  reached through the morphological table

    Nothing is guessed: a form the table cannot reduce and LSJ does not list
    returns None, and the caller shows nothing rather than a wrong gloss.
    """
    word = (form or "").strip()
    if not word:
        return None
    key = normalize(word)
    if not key:
        return None
    if not _load_index():
        return None

    entry, how = _find(key)
    if entry:
        return {"form": word, "key": key, "match": how, "entry": entry,
                "analysis": []}

    # Second link: the morphological table. Reported separately because a
    # reduction is a reading, not a fact the dictionary states.
    analyses = []
    fallback = None
    seen = set()
    for a in lemmas_pure.candidates(key):
        lem = normalize(a.lemma)
        if not lem or lem in seen:
            continue
        seen.add(lem)
        # The table returns the AUTHOR's spelling (ξυμμαχος); `_find` folds it
        # to the dictionary's (συμμαχος) itself.
        cand, _ = _find(lem)
        if not cand:
            continue
        analyses.append({"lemma": a.lemma, "pos": a.pos, "infl": a.infl,
                         "source": a.source})
        # The table can offer several readings; the FIRST one that the
        # dictionary actually has an entry for is the one shown, and the rest
        # stay in `analysis` so the reader can see the alternatives.
        if fallback is None:
            fallback = cand
        if len(analyses) >= 4:
            break
    if fallback is None:
        return None
    return {"form": word, "key": key, "match": "lemma", "entry": fallback,
            "analysis": analyses}


def describe() -> dict:
    """The dictionary as the app should present it: facts, not a mapping."""
    man = manifest()
    return {
        "module": "lexicon",
        "source": "Liddell-Scott-Jones, Perseus Digital Library",
        "license": "CC BY-SA 4.0",
        "attribution": (man or {}).get("source", {}).get("attribution", ""),
        "rows": [
            {"name": "entries", "value": (man or {}).get("n_entries", 0),
             "note": "LSJ entries in the built index"},
            {"name": "lookup keys",
             "value": (man or {}).get("n_index", 0),
             "note": "headwords, normalised (accents stripped)"},
            {"name": "cited forms",
             "value": (man or {}).get("n_index_forms", 0),
             "note": "inflected forms LSJ cites; consulted after headwords"},
        ],
        "notes": [
            "A lookup tries the headwords, then the cited forms, then reduces "
            "the form with the morphological table and looks up the lemma.",
            "The dictionary is built, not bundled: scripts/fetch_lsj.sh then "
            "scripts/build_lexicon.py. Nothing is fetched at runtime.",
        ],
    }

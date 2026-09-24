#!/usr/bin/env python3
"""Build the reading-aid lexicon from the Perseus LSJ slices. Stdlib only.

WHAT THIS PRODUCES
------------------
`data/lexicon/out/<nn>.json` — one file per source slice, plus a `manifest.json`
with counts, provenance and the attribution the licence requires. Each slice
file is:

    {"slice": "15", "source": "grc.lsj.perseus-eng15.xml",
     "entries": [{"id": "n71427", "head": "ξαίνω", "gloss": "scratch, comb",
                  "labels": ["fut.", "aor."], "forms": ["ξᾱνῶ", "ἔχνηνα"],
                  "key": "cai/nw", "link": "..."}],
     "index": {"ξαινω": 3, ...},
     "index_forms": {"εξανθην": 3, ...}}

TWO INDEXES, ON PURPOSE. `index` holds headwords and is authoritative;
`index_forms` holds the inflected forms LSJ cites in an entry's morphology
section and is consulted only when `index` misses. That split is not tidiness:
LSJ's entry for ξένη cites ξένος as a related form, and with one flat index
the alias claims `ξενος` before the real ξένος entry is ever read — clicking
ξένος in a text would open "foreign woman". Headwords always win; a cited form
answers only for words that have no entry of their own.

A form is taken only if it is a SINGLE word, because the source material is
running text: an unfiltered pass over ξένη's entry yielded `ἡ` and `γυνή` as
"forms" of ξένη. Hyphens are stripped from headwords and lookup keys alike —
LSJ writes morpheme boundaries into the headword (`ξάνθ-ιον`, `ξέν-η`), and a
key that keeps the hyphen can never match the ξάνθιον it is supposed to find.

IT DOES NOT READ A SLICE INTO MEMORY. iterparse with clearing, so a 43 MB
slice costs a few hundred KB. `.claudesignore` forbids reading the corpora as
data and this obeys that in spirit and in letter: no slice is ever opened by
a tool, only by this parser.

GREEK IS DECIDED BY THE MARKUP, NEVER BY THE LETTERS. English and Beta Code
are both ASCII: `<tr>card,</tr>` is a gloss and `<orth lang="greek">cai/nw
</orth>` is a headword, and nothing in the characters distinguishes them. So
only elements carrying `lang="greek"` are transliterated (`orth`, `quote`,
`foreign`, `gen`, `etym`); everything else is copied as written.

RESUMABLE. A slice whose output already exists is skipped, so an interrupted
build continues rather than restarting; `--force` rebuilds.

The source is PerseusDL/lexica (see data/lexicon/README.md for the fetch and
the licence). Beta Code decoding is app/betacode.py, which is validated
by a round trip over the gold treebank — see that module.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from app import betacode                                    # noqa: E402
from app.flame_pure import normalize                        # noqa: E402

RAW = os.path.join(ROOT, "data", "lexicon", "raw")
OUT = os.path.join(ROOT, "data", "lexicon", "out")

# The Perseus text identifier for LSJ, and how an entry id becomes a link.
# Best-effort: the app falls back to a by-headword search if a link 404s.
PERSEUS_LSJ = "Perseus:text:1999.04.0057"

# Elements whose text is Greek (when they also carry lang="greek").
GREEK_TAGS = ("orth", "quote", "foreign", "gen", "etym")

GLOSS_MAX = 220          # characters of gloss kept per entry
GLOSS_TRS = 6            # ...and at most this many <tr> fields joined
FORMS_MAX = 12           # inflected forms kept per entry


def _text(el) -> str:
    return "".join(el.itertext()).strip()


def _is_greek(el) -> bool:
    return el.get("lang") == "greek"


def _decode_el(el) -> str:
    t = _text(el)
    return betacode.decode(t) if _is_greek(el) else t


_WS = re.compile(r"\s+")
# Hyphens, of every width, plus the hair space LSJ uses inside a headword.
_DASHES = dict.fromkeys(map(ord, "-‐‑‒– ­"), None)
# A form is one word: letters only, no space, no punctuation, no digits.
_ONE_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
# Latin letters carrying diacritics — the fingerprint of a cognate
# transliteration in a <tr> list, as opposed to an English gloss. Matches
# Latin-1 Supplement and Latin Extended, so Greek script does not match.
_LATIN_DIA = re.compile(r"[À-ɏ]")


def _clean(s: str) -> str:
    return _WS.sub(" ", s.strip().translate(_DASHES)).strip()


def _clean_head(s: str) -> str:
    """LSJ headword -> the word a reader would look up.

    Morpheme hyphens come out (`ξάνθ-ιον` -> ξάνθιον, `ξέν-η` -> ξένη), and
    only the first whitespace token is kept: a handful of entries carry a
    second form or a stray letter (`Ξ ξ`, `ξυρμεύεσθαι :`).
    """
    s = _clean(s).split(" ")[0] if _clean(s) else ""
    return s.strip(".,;:·—")


def _trim_gloss(s: str) -> str:
    """Cut to GLOSS_MAX at a word boundary, marking that it was cut."""
    s = _clean(s)
    if len(s) <= GLOSS_MAX:
        return s
    cut = s[:GLOSS_MAX].rsplit(" ", 1)[0].rstrip(",;: ")
    return cut + " …"


def parse_slice(path: str) -> dict:
    """One slice -> {"entries": [...], "index": {...}}.

    Streaming: every element is cleared once handled, so memory stays flat.
    """
    entries: list[dict] = []
    index: dict[str, int] = {}          # headwords — authoritative
    index_forms: dict[str, int] = {}    # cited inflected forms — fallback

    for event, el in ET.iterparse(path, events=("end",)):
        if el.tag != "entryFree":
            continue
        entry = _parse_entry(el)
        el.clear()
        if entry is None:
            continue
        pos = len(entries)
        entries.append(entry)
        # First writer wins within each tier: LSJ is ordered alphabetically,
        # so an earlier homograph is the one a reader meant.
        for key in entry["_keys"]:
            index.setdefault(key, pos)
        for key in entry["_form_keys"]:
            index_forms.setdefault(key, pos)
        del entry["_keys"], entry["_form_keys"]

    return {"entries": entries, "index": index, "index_forms": index_forms}


def _parse_entry(el) -> dict | None:
    """One <entryFree>. Returns None for anything with no headword."""
    key = el.get("key") or ""
    orth = None
    for child in el.iter("orth"):
        if _is_greek(child):
            orth = _decode_el(child)
            break
    head = _clean_head(orth or betacode.decode(key))
    if not head:
        return None

    gloss_parts: list[str] = []
    labels: list[str] = []
    forms: list[str] = []

    # THE GLOSS IS NOT "THE FIRST <tr> IN THE ENTRY". Taking them in document
    # order reaches into the headword's etymology first, and ἔχω came out
    # glossed "check, lon, seĝh, sáhate, sigis" — Sanskrit roots, the
    # dictionary's own etymology of the verb, offered to a reader as its
    # meaning. The definitional <tr> fields are the DIRECT CHILDREN of a
    # <sense>, so that is what is read, from the first sense that has any.
    #
    # EXCEPT THAT THE TRANSCRIPTION WRAPS THE ETYMOLOGY IN A SENSE. ἔχω's
    # level-1 senses are ['A', 'A', 'B', 'C']: the printed etymology paragraph
    # was given n="A" and then the real senses were numbered A, B, C as well.
    # So a first level-1 sense whose n is REPEATED later is not a sense at all,
    # and is skipped. That is a mechanical test on the entry's own structure,
    # not a guess from the words; nothing else in the entry looks like it.
    lvl1 = [s for s in el if s.tag == "sense" and s.get("level") == "1"]
    if len(lvl1) > 1:
        ns = [s.get("n") for s in lvl1]
        if ns[0] is not None and ns[0] in ns[1:]:
            lvl1 = lvl1[1:]

    chosen = None
    for sense in lvl1 or list(el.iter("sense")):
        # Cognate transliterations ("vīginti", "viṃśatis", "seĝh") are Latin
        # words with diacritics sitting in the same <tr> list as the English
        # gloss ("twenty"). They are etymology, not meaning, so they go.
        if any(t.tag == "tr" and not _LATIN_DIA.search(_text(t))
               for t in sense):
            chosen = sense
            break
    gloss_trs = {t for t in chosen if t.tag == "tr"} if chosen is not None \
        else set()

    # ONE document-order pass, because the cutoff for both fields is the same
    # point: the chosen sense's first gloss. `seen_gloss` is set when that <tr>
    # is REACHED, so everything before it — the morphology run — is form
    # material and everything after it is definition and quotation. Getting
    # this wrong is not cosmetic: with the cutoff missing, every <foreign> in
    # the entry was taken as a paradigm form and ἄξιος came back owning
    # `λόγου`, from the idiom "ἄξιος λόγου" quoted deep inside its own senses.
    seen_gloss = chosen is None
    for sub in el.iter():
        if sub.tag == "tr":
            if sub in gloss_trs:
                seen_gloss = True
                s = _text(sub)
                if len(gloss_parts) < GLOSS_TRS \
                        and not _LATIN_DIA.search(s):
                    gloss_parts.append(s)
        elif sub.tag in ("gram", "tns", "itype", "number", "per", "case"):
            lab = _clean(_text(sub))
            if lab and lab not in labels and len(labels) < 6:
                labels.append(lab)
        elif sub.tag in ("foreign", "gen") and _is_greek(sub) \
                and not seen_gloss:
            # ONE WORD IN THE SOURCE, tested before anything is cleaned off
            # it. `_clean_head` keeps only the first whitespace token, so
            # testing afterwards let a five-word quotation through: the
            # Aeschylus line `e)/xousi moi=ran ou)k eu)pe/mpelon`, cited in
            # the intro of εὐπέμπελος, became the form "ἔχουσι" and claimed
            # that word for the wrong entry.
            raw = _text(sub)
            if len(raw.split()) != 1:
                continue
            form = _clean_head(betacode.decode(raw))
            if form and form != head and _ONE_WORD.fullmatch(form) \
                    and len(form) > 2 and form not in forms \
                    and len(forms) < FORMS_MAX:
                forms.append(form)

    # Glosses: the LSJ's <tr> fields are comma-terminated fragments, so the
    # trailing punctuation comes off before they are joined into a sentence.
    parts = []
    for p in gloss_parts:
        p = _clean(p).strip(",;:·").strip()
        if p and p not in parts:
            parts.append(p)
    gloss = _trim_gloss(", ".join(parts))

    # Entries with no gloss are not empty: a fifth of LSJ turns out to define
    # by QUOTING, in Greek, another lexicographer — `a)/aqi: au)to/qi, Cyr.`
    # is "ἄαθι: αὐτόθι" and it is the whole entry. That text mixes scripts
    # inside one field, so it is transliterated token by token, each token
    # decoded only if it carries a diacritic on a vowel (`betacode.looks_greek`
    # measured this: of 37287 <tr> fields, 14 "look Greek" and all 14 are
    # false positives, which is why the gloss path never does this).
    note = ""
    if not gloss:
        note = _trim_gloss(betacode.decode_prose(" ".join(
            t for t in (_clean(x) for x in el.itertext()) if t)[:400]))

    # Lookup keys: headword and beta key are authoritative; cited forms are not.
    keys = {normalize(head)}
    if key:
        keys.add(normalize(_clean_head(betacode.decode(key))))
    form_keys = {normalize(f) for f in forms}
    keys.discard("")
    form_keys.discard("")
    form_keys -= keys

    eid = el.get("id") or ""
    return {
        "id": eid,
        "head": head,
        "gloss": gloss,
        "note": note,
        "labels": labels,
        "forms": forms,
        "key": key,
        "link": (f"https://www.perseus.tufts.edu/hopper/text"
                 f"?doc={PERSEUS_LSJ}:entry={eid}" if eid else ""),
        "_keys": keys,
        "_form_keys": form_keys,
    }


def slice_number(name: str) -> str:
    m = re.search(r"-eng(\d+)\.xml$", name)
    return m.group(1).zfill(2) if m else name


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raw", default=RAW)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--force", action="store_true",
                    help="rebuild slices whose output already exists")
    ap.add_argument("--only", default="",
                    help="comma-separated slice numbers, for a quick run")
    args = ap.parse_args()

    if not os.path.isdir(args.raw):
        print(f"no source slices at {args.raw}\n"
              f"fetch them first: scripts/fetch_lsj.sh", file=sys.stderr)
        return 2
    os.makedirs(args.out, exist_ok=True)

    names = sorted(n for n in os.listdir(args.raw) if n.endswith(".xml"))
    if args.only:
        want = {s.strip().zfill(2) for s in args.only.split(",") if s.strip()}
        names = [n for n in names if slice_number(n) in want]
    if not names:
        print("no slices matched", file=sys.stderr)
        return 2

    manifest_slices = []
    lookup: dict[str, str] = {}          # normalised form -> slice number
    lookup_forms: dict[str, str] = {}
    for name in names:
        nn = slice_number(name)
        dest = os.path.join(args.out, f"{nn}.json")
        if os.path.exists(dest) and not args.force:
            print(f"  {nn}: cached")
            with open(dest, encoding="utf-8") as fh:
                m = json.load(fh)
            manifest_slices.append({k: m[k] for k in
                                    ("slice", "source", "n_entries", "n_index",
                                     "n_index_forms")})
            for k in m["index"]:
                lookup.setdefault(k, nn)
            for k in m["index_forms"]:
                lookup_forms.setdefault(k, nn)
            continue
        src = os.path.join(args.raw, name)
        print(f"  {nn}: parsing {name} ({os.path.getsize(src)//1024} KB) …",
              flush=True)
        got = parse_slice(src)
        payload = {"slice": nn, "source": name, **got,
                   "n_entries": len(got["entries"]),
                   "n_index": len(got["index"]),
                   "n_index_forms": len(got["index_forms"])}
        tmp = dest + ".part"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, dest)
        print(f"  {nn}: {len(got['entries'])} entries, "
              f"{len(got['index'])} keys, "
              f"{len(got['index_forms'])} form keys, "
              f"{os.path.getsize(dest)//1024} KB")
        manifest_slices.append({k: payload[k] for k in
                                ("slice", "source", "n_entries", "n_index",
                                 "n_index_forms")})
        for k in got["index"]:
            lookup.setdefault(k, nn)
        for k in got["index_forms"]:
            lookup_forms.setdefault(k, nn)

    # One global form -> slice number map, so a lookup never has to open a
    # slice it might not need. Values are the slice number as a string: the
    # whole point of this file is to be small enough to load once and keep.
    with open(os.path.join(args.out, "lookup.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"index": lookup, "index_forms": lookup_forms}, fh,
                  ensure_ascii=False, separators=(",", ":"))

    manifest = {
        "generated_by": "scripts/build_lexicon.py",
        "format": 1,
        "decode": "app/betacode.py (Beta Code -> Unicode)",
        "lookup_key": "app.flame_pure.normalize of the headword and of each form",
        "slices": manifest_slices,
        "n_entries": sum(s["n_entries"] for s in manifest_slices),
        "n_index": sum(s["n_index"] for s in manifest_slices),
        "n_index_forms": sum(s["n_index_forms"] for s in manifest_slices),
        "source": {
            "name": "Liddell-Scott-Jones (LSJ), Perseus Digital Library",
            "repo": "PerseusDL/lexica",
            "path": "CTS_XML_TEI/perseus/pdllex/grc/lsj/",
            "files": "grc.lsj.perseus-eng1..27.xml",
            "license": "CC BY-SA 4.0",
            "attribution": ("Liddell, H. G., Scott, R., Jones, H. S., & "
                            "McKenzie, R. (1940). A Greek-English Lexicon. "
                            "Oxford: Clarendon Press. Digitised by the Perseus "
                            "Digital Library, CC BY-SA 4.0."),
            "modifications": ("Beta Code transliterated to Unicode; entries "
                              "reduced to headword, gloss, labels and cited "
                              "forms for a reading aid."),
        },
        "link_pattern": (f"https://www.perseus.tufts.edu/hopper/text"
                         f"?doc={PERSEUS_LSJ}:entry=<id>"),
    }
    with open(os.path.join(args.out, "manifest.json"), "w",
              encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"\nmanifest: {manifest['n_entries']} entries, "
          f"{manifest['n_index']} lookup keys, "
          f"{len(manifest_slices)} slices")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

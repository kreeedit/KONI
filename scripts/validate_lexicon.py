#!/usr/bin/env python3
"""Validate the built lexicon and the lookup chain. Exit 1 on any failure.

    python3 scripts/validate_lexicon.py            # needs data/lexicon/out
    python3 scripts/validate_lexicon.py --builder  # also re-parses a slice

The assertions are the MEASURED facts, not restatements of the code. Each one
is a bug that was actually shipped and then found, so the test exists to keep
it found:

  * `λόγου` resolved to ἄξιος, because LSJ's ἄξιος entry quotes the idiom
    "ἄξιος λόγου" and every <foreign> in the entry was being taken as a form.
  * `ἔχουσι` resolved to εὐπέμπελος, because a five-word Aeschylus quotation
    in that entry's intro was truncated to its first word by the cleaner and
    then passed the one-word test.
  * `ξυμμάχων` found nothing, because the morphological table returns the
    author's spelling (ξυμμαχος) while the dictionary files the Attic one.
  * `ἔχω` was glossed "check, lon, seĝh, sáhate, sigis" — its etymology, read
    as its meaning.
"""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from app import lexicon                                       # noqa: E402

ok = fail = 0


def check(label: str, got, want) -> None:
    global ok, fail
    if got == want:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label}\n         got  {got!r}\n         want {want!r}")


def resolved(word: str):
    """(head, match) for a word, or (None, None)."""
    hit = lexicon.lookup(word)
    if not hit:
        return None, None
    return hit["entry"]["head"], hit["match"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--builder", action="store_true",
                    help="also check the slice parser against the raw XML")
    args = ap.parse_args()

    avail = lexicon.available()
    print("availability:")
    check("the dictionary reports itself built", avail["ready"], True)
    if not avail["ready"]:
        print("build it first: scripts/fetch_lsj.sh && "
              "python3 scripts/build_lexicon.py")
        return 1
    check("it carries the share-alike attribution",
          "CC BY-SA" in avail["license"], True)
    check("attribution names the printed dictionary",
          "Greek-English Lexicon" in avail["attribution"], True)
    check("it is a real lexicon, not a stub",
          avail["n_entries"] > 100000, True)
    print(f"       ({avail['n_entries']} entries, {avail['n_index']} keys)")

    print("\nthe chain (each of these was a bug):")
    check("a headword resolves to itself",
          resolved("ξαίνω"), ("ξαίνω", "head"))
    check("an idiom-quoted word is not stolen by another entry",
          resolved("λόγου")[0], "λόγος")
    check("a quotation fragment does not own a word",
          resolved("ἔχουσι")[0], "ἔχω")
    check("the author's spelling reaches the Attic headword",
          resolved("ξυμμάχων")[0], "σύμμᾱχος")
    check("...and so does the Attic spelling",
          resolved("σύμμαχος")[0], "σύμμᾱχος")
    check("a form LSJ itself cites is answered directly",
          lexicon.lookup("ἐξάνθην")["match"], "form")
    check("an ordinary oblique form goes through the table",
          lexicon.lookup("ἀνθρώπου")["match"], "lemma")
    check("the reading is shown when there was one",
          lexicon.lookup("ἀνθρώπου")["analysis"][0]["infl"], "gen sg")
    check("nonsense finds nothing rather than something",
          lexicon.lookup("zzz"), None)

    print("\nglosses are meanings, not etymology:")
    check("ἔχω is 'have, hold'",
          lexicon.lookup("ἔχω")["entry"]["gloss"].startswith("have, hold"),
          True)
    check("no Sanskrit root reaches the gloss panel",
          "seĝh" in (lexicon.lookup("ἔχω")["entry"]["gloss"] or ""), False)
    check("no cognate transliteration reaches it either",
          "vīginti" in (lexicon.lookup("εἴκοσι")["entry"]["gloss"] or ""),
          False)
    check("a cross-reference entry keeps its text as a note, not a gloss",
          lexicon.lookup("νηῶν")["entry"]["gloss"], "")
    check("...and that note is transliterated, not raw Beta Code",
          lexicon.lookup("νηῶν")["entry"]["note"].startswith("νηῶν"), True)

    if args.builder:
        raw = os.path.join(ROOT, "data", "lexicon", "raw")
        if not os.path.isdir(raw):
            print("\nraw slices absent, skipping the parser checks")
        else:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "build_lexicon", os.path.join(HERE, "build_lexicon.py"))
            bl = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(bl)
            print("\nthe slice parser:")
            got = bl.parse_slice(os.path.join(raw, "grc.lsj.perseus-eng15.xml"))
            check("entries are read", len(got["entries"]) > 400, True)
            heads = {e["head"]: e for e in got["entries"]}
            check("ξαίνω carries its real paradigm",
                  heads["ξαίνω"]["forms"], ["ἐξάνθην", "ἔξασμαι"])
            check("hyphens are not left inside a headword",
                  any("-" in h for h in heads), False)

    print(f"\n{ok}/{ok + fail} assertions pass")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())

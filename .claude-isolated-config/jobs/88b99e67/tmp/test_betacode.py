"""Tests for app/betacode.py — table facts, then the gold round trip.

The table tests are here so the MEASURED facts (which are the ones that can't
be re-derived from the code) are pinned as assertions: if someone later
"tidies" `)` and `(` into the mnemonic order, these fail and the failure text
says which gloss the decision came from.
"""
import json
import os
import sys
import unicodedata

sys.path.insert(0, "/home/tamask/github/KONI")
from app import betacode as b

ok = fail = 0


def check(label, got, want):
    global ok, fail
    if got == want:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label}\n         got  {got!r}\n         want {want!r}")


# --- the measured letter facts -------------------------------------------
check("c = xi, not chi", b.decode("ce/nos"), "ξένος")
check("x = chi, not xi", b.decode("xalepo/s"), "χαλεπός")
check("xai/rw = rejoice", b.decode("xai/rw"), "χαίρω")
check("digamma", b.decode("*v"), "Ϝ")

# --- the measured breathing facts ----------------------------------------
check(") = smooth (aeidw sings)", b.decode("a)ei/dw"), "ἀείδω")
check("( = rough (haliskomai is taken)", b.decode("a(li/skomai"), "ἁλίσκομαι")
check("a)fori/zw = aphorizo", b.decode("a)fori/zw"), "ἀφορίζω")
check("rough rho", b.decode("r("), "ῥ")
check("smooth rho", b.decode("r)"), "ῤ")

# --- attachment: diphthongs, capitals, stacking --------------------------
check("breathing attaches to the letter after *", b.decode("*)ai/+da,"), "Ἀΐδα,")
check("diphthong: both marks on the second element", b.decode("au)="), "αὖ")
check("diphthong with rough breathing", b.decode("au(="), "αὗ")
check("circumflex + iota subscript", b.decode("*qra=|c"), "Θρᾷξ")
check("acute inside a diphthong", b.decode("*ai)/gina"), "Αἴγινα")
check("final sigma", b.decode("lo/gos"), "λόγος")
check("interior sigma stays", b.decode("e)sti/n"), "ἐστίν")

# Diaeresis + accent: the LSJ writes acute-first (`i/+`), Unicode needs the
# diaeresis first. This is the difference between ι+0301+0308 (renders right,
# equals nothing) and U+0390 (the real character).
check("diaeresis takes the canonical position, giving U+0390",
      b.decode("dai/+das"), "δαΐδας")
check("...and it really is the precomposed code point",
      b.decode("dai/+s")[-2], "ΐ")

# --- punctuation is not a diacritic --------------------------------------
# Note the traps here: `st(h)` and `and/or` are NOT valid probes, because
# s,t,h,a,n,d,o,r are all beta letters and transliterate exactly as they
# should. The only way to test the positional rule is with a base that cannot
# take a mark, or with non-letter characters.
check("mark after a consonant that cannot carry it stays literal",
      b.decode("n("), "ν(")
check("...and a dangling one is not swallowed either", b.decode("n/"), "ν/")
check("mark after whitespace stays literal", b.decode("a) )"), "ἀ )")
check("digits and punctuation untouched", b.decode("7.191, ;"), "7.191, ;")

# --- language-blindness is a documented property, not an accident --------
# This is the trap: the decoder CANNOT tell these apart, so the caller must
# only ever hand it markup-tagged Greek.
check("English transliterates as faithfully as Greek",
      b.decode("humming"), "ηυμμινγ")

# --- encode is faithful to NFD order -------------------------------------
check("encode keeps marks after their base",
      b.encode("ἀείδω"), "a)ei/dw")
check("encode marks upper case with *", b.encode("Θρᾷξ"), "*qra=|c")

# --- describe() carries the evidence, not just the mapping ---------------
d = b.describe()
names = {row["name"] for row in d}
check("describe covers every mark", names >= {
    "letters", "psili", "dasia", "acute", "grave", "circumflex",
    "iota_subscript", "diaeresis", "macron", "breve", "capital"}, True)
ev = {row["name"]: row["evidence"] for row in d}
check("psili evidence cites the gloss measurement",
      "ἀείδω" in ev["psili"], True)
check("dasia evidence cites the gloss measurement",
      "ἁλίσκομαι" in ev["dasia"], True)
check("letters evidence cites the c/x measurement",
      "ξένος" in ev["letters"], True)

# --- the gold round trip -------------------------------------------------
GOLD = "/home/tamask/github/KONI/.claude-isolated-config/jobs/88b99e67/tmp/gold_thuc.json"
if os.path.exists(GOLD):
    gold = json.load(open(GOLD))
    lemmas = sorted({t[1] for t in gold})
    bad = [(L, b.encode(L), b.decode(b.encode(L))) for L in lemmas
           if b.decode(b.encode(L)) != L]
    print(f"  --   gold treebank: {len(lemmas)} distinct lemmas, "
          f"{len(bad)} not round-tripping")
    # The only expected failures are the gold data's own Latin `v` typos.
    check("all round-trip failures are the known Latin-v data defect",
          all("v" in L and "ϝ" in r for L, _, r in bad), True)
    check("round trip rate >= 99.9%",
          len(lemmas) - len(bad) >= 0.999 * len(lemmas), True)
else:
    print("  --   gold data not present, skipping the round trip")

print(f"\n{ok}/{ok+fail} assertions pass")
sys.exit(1 if fail else 0)

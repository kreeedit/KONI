"""Regression tests for the three-corpus Koine contrast (requirement #2).

Requirement: archaism = a word that is frequent in the model author, ~absent
from a contemporary NON-archaizing Koine reference, and used MORE by the
archaizer than by his own model.

Almost everything here runs on SYNTHETIC three-corpus counts, and that is
deliberate: the classifier is a function of six numbers per word, so a test
that pinned the real Thucydides/Procopius/Socrates figures would be testing the
corpora, not the code, and would break the day a book is added. The synthetic
corpora state exactly the rate pattern each class is defined by. One test at
the end does run the real three works, because the thing that most needs
guarding is the CLAIM that the literal two-conjunct rule over-fires and the
third conjunct fixes it — and that claim is about the real corpus, not about
the arithmetic.

The house doctrine applies: a class is a CANDIDATE, not a verdict. The tests
below check the classification, and separately check that the report DISCLOSES
what would make a row a false positive (the marked-spelling evidence, the
subject-matter caveat, the three raw counts).
"""
import os
import sys

sys.path.insert(0, os.getcwd())
from app import archaism_pure as A             # noqa: E402

fails = []


def ck(cond, msg):
    print(("  ok   " if cond else " FAIL ") + msg)
    if not cond:
        fails.append(msg)


def freq(pairs, total=None):
    """A minimal `work_freq` result: {word: count} plus a token total."""
    from collections import Counter
    counts = Counter(pairs)
    return {"counts": counts, "total": total or 100000, "display": dict(counts),
            "caps": Counter(), "forms": {}, "n_elided": 0, "variants": (),
            "drop_elided": True}


def cls(ca, cb, cc, na=100000, nb=100000, nc=100000):
    """The class alone, for one word's three counts."""
    return A._classify(ca, cb, cc, na, nb, nc, A.MIN_AC, A.MIN_BC,
                       A.MIN_REVIVAL)[0]


# ---- 1. the three conjuncts, one at a time -------------------------------
# The whole design is that the class needs ALL THREE, so each test removes one
# and the class must fall out of `archaism`.
print("1. the class needs all three conjuncts")
ck(cls(50, 200, 0) == "archaism", "classical-high, Koine-absent, overused in B -> archaism")
ck(cls(50, 50, 0) == "classical",
   "same but B only MATCHES A (not overused) -> classical, not archaism "
   "[the subject-matter case: the frequency just follows the model]")
ck(cls(50, 5000, 0) == "archaism",
   "a large overuse is still archaism, not overused [B/K is high but so is B/A]")
ck(cls(50, 5000, 300) == "overused",
   "overused in B, but the Koine norm has it too -> overused [mannerism]")
ck(cls(50, 0, 0) == "shared",
   "the word never occurs in the archaizer -> 'present in B' is a conjunct too")
# `_classify` reads only the six counts: the `min_a` admission test lives in
# `koine_contrast`'s loop, because it is a fact about which words are IN the
# report, not about how a word in it is labelled. Stated here so the two are not
# confused: this call answers "how would a word seen once in A be classified",
# not "is it in the table" (test 5 checks that).
ck(cls(1, 50, 0) == "archaism",
   "_classify alone labels a 1-in-A word from its rates; admission is the "
   "caller's min_a, applied before it is ever classified")

# ---- 2. the overuse conjunct is what removes the topic words -------------
# MEASURED, from the real works: `σύμμαχοι` is A=159, B=11, C=0. Literally the
# user's rule ("classical-high AND Koine-absent AND present in B") admits it,
# because a church historian has no fleet. It is not an archaism: Procopius
# uses it 14x LESS than Thucydides.
print("2. the topic confound, with the real counts")
ck(cls(159, 11, 0) == "classical",
   "σύμμαχοι (A=159 B=11 C=0): Koine-absent but NOT overused -> classical, "
   "so the literal two-conjunct rule would have called it an archaism")
ck(cls(1804, 4245, 0) == "archaism",
   "ἐς (A=1804 B=4245 C=0): the Ionic/Attic preposition against Koine εἰς -> "
   "archaism, and it is the top row of the real report")
ck(cls(131, 431, 0) == "archaism",
   "σφίσιν against Koine αὐτοῖς -> archaism")

# ---- 3. the avoided direction -------------------------------------------
# The mirror phenomenon, and the one the original view structurally could not
# reach: the Koine word the archaizer SHUNS. Real: ἐκκλησία A=11 B=1 C=97.
print("3. the opposite direction: the Koine word B avoids")
ck(cls(11, 1, 97) == "avoided", "ἐκκλησία (A=11 B=1 C=97) -> avoided")
ck(cls(5, 0, 42) == "avoided", "ξύνοδος (A=5 B=0 C=42) -> avoided")
ck("ξενος" not in {x["norm"] for x in A.koine_contrast(
       freq({"σφισιν": 131}), freq({"σφισιν": 431}), freq({"ξενος": 5000}))["rows"]},
   "a word the model author never uses is not in the report at all, however "
   "prominent it is in the Koine norm — this asks about HIS vocabulary")

# ---- 4. rate, not raw count ---------------------------------------------
# The corpora differ in length, so every test is a ratio. Getting this wrong
# would make the longer work look archaizing across the board.
print("4. the comparison is a RATE")
same = cls(30, 60, 0, na=100000, nb=200000, nc=100000)
ck(same == "classical",
   "A=30/100k and B=60/200k are the SAME rate -> not an overuse -> classical")
ck(cls(30, 120, 0, na=100000, nb=200000) == "archaism",
   "B=120/200k is double A's rate -> archaism")

# ---- 5. the report: shape, census, disclosure ---------------------------
print("5. koine_contrast over synthetic corpora")
fa = freq({"ες": 1804, "συμμαχοι": 159, "σφισιν": 131, "εκκλησια": 11,
           "απαξ": 1, "κοινον": 300, "μεντοι": 5})
fb = freq({"ες": 4245, "συμμαχοι": 11, "σφισιν": 431, "εκκλησια": 1,
           "κοινον": 300, "μεντοι": 400})
fc = freq({"ες": 0, "συμμαχοι": 0, "σφισιν": 0, "εκκλησια": 97,
           "κοινον": 300, "μεντοι": 10})
r = A.koine_contrast(fa, fb, fc)
by = {x["norm"]: x for x in r["rows"]}
ck(by["ες"]["class"] == "archaism" and by["σφισιν"]["class"] == "archaism",
   "the two revivals are classified archaism")
ck(by["συμμαχοι"]["class"] == "classical", "the topic word is classical")
ck(by["εκκλησια"]["class"] == "avoided", "the church word is avoided")
ck(by["μεντοι"]["class"] == "overused", "the mannerism is overused")
ck(by["κοινον"]["class"] == "shared", "a word at parity in all three is shared")
ck("απαξ" not in by, "a word under min_a is not admitted (min_a is A's, only)")
ck([x["norm"] for x in r["rows"]][0] == "ες",
   "class order is fixed: an archaism ranks above an avoided row whatever the "
   "latter's score — a limit must not decide WHICH KINDS of row are shown")
ck(r["census"] == {"archaism": 2, "classical": 1, "overused": 1,
                   "avoided": 1, "shared": 1},
   f"the census counts every considered word, not the returned page: {r['census']}")
ck(all(x["count_c"] == fc["counts"].get(x["norm"], 0) for x in r["rows"]),
   "each row carries all three raw counts, so 'absent from Koine' is checkable")
ck(all("score_ac" in x and "score_bc" in x and "score_ab" in x for x in r["rows"]),
   "...and all three ratios, so the class can be re-derived by hand")
ck(r["params"]["min_revival"] == A.MIN_REVIVAL and "max_b" not in r["params"],
   "the rarity box (min_b/max_b/min_score) is NOT part of this report's params")

# ---- 6. the limit truncates the page, never the census -------------------
print("6. limit handling")
big = {f"w{i}": 50 + i for i in range(400)}
fb2 = freq({f"w{i}": 50 + 10 * i for i in range(400)})
r2 = A.koine_contrast(freq(big), fb2, freq({}), limit=10)
ck(len(r2["rows"]) == 10, "limit caps the returned rows")
ck(r2["n_considered"] == 400 and sum(r2["census"].values()) == 400,
   "the census is over all 400, so a truncated table can still report the mix")

# ---- 7. proper nouns ----------------------------------------------------
print("7. the proper-noun filter")
fa3 = freq({"αθηναιοι": 502, "σφισιν": 131})
fb3 = freq({"αθηναιοι": 3, "σφισιν": 431})
fa3["caps"]["αθηναιοι"] = 502      # capitalized at every occurrence
fb3["caps"]["αθηναιοι"] = 3
r3 = A.koine_contrast(fa3, fb3, freq({}))
ck({x["norm"] for x in r3["rows"]} == {"σφισιν"},
   "an ethnic capitalized everywhere is dropped by default (it is A's subject, "
   "not its diction) — and the bycatch is reported, not silent")
ck(r3["n_dropped_proper"] == 1, f"n_dropped_proper == 1, got {r3['n_dropped_proper']}")
r4 = A.koine_contrast(fa3, fb3, freq({}), drop_proper=False)
ck(len(r4["rows"]) == 2, "drop_proper=False shows it")

# ---- 8. non-finite thresholds do not admit everything --------------------
# `x < nan` is False, so a NaN threshold would make every comparison TRUE and
# admit the whole vocabulary. Same trap `contrast` guards against.
print("8. a non-finite threshold falls back to the default")
nan = float("nan")
ck(cls(50, 200, 0) == "archaism", "sanity: the case used below is an archaism")
r5 = A.koine_contrast(fa, fb, fc, min_ac=nan, min_bc=nan, min_revival=nan)
ck(r5["params"]["min_ac"] == A.MIN_AC,
   "min_ac=NaN falls back to the default instead of admitting everything")

# ---- 9. the marked-spelling evidence rides with the row ------------------
# A row's class is three numbers; the evidence that a row is a REVIVAL rather
# than a subject word is often a spelling choice, and the key has already folded
# it away (`ξυμμαχοι` pools to `συμμαχοι`). It is read off B's pooled forms.
print("9. marked-in-B evidence is read off B's own spellings")
from collections import Counter                       # noqa: E402
def pooled(forms):
    d = freq({"συμμαχοι": sum(forms.values())})
    d["forms"] = {"συμμαχοι": Counter(forms)}
    d["variants"] = A.VARIANTS_DEFAULT
    return d

fa6 = pooled({"ξυμμαχοι": 10})
r6 = A.koine_contrast(fa6, pooled({"ξυμμαχοι": 40}), freq({}))
ck(r6["rows"][0]["marked_b"] == ["xyn"],
   f"B's ξυμμαχοι is flagged as the marked spelling: {r6['rows'][0]['marked_b']}")
ck(A.koine_contrast(fa6, pooled({"συμμαχοι": 40}), freq({}))["rows"][0]["marked_b"] is None,
   "the Koine spelling is not flagged — the column would be noise otherwise")
fa8 = pooled({"συμμαχοι": 10})
fa8["variants"] = ()          # pooling off: nothing is marked, nothing is pooled
ck(A.koine_contrast(fa8, pooled({"ξυμμαχοι": 40}), freq({}))["rows"][0]["marked_b"] is None,
   "with the pooling selection empty there are no rules to be marked for — the "
   "flag follows the selection the counts were built with, it is not a second "
   "opinion about the word")

# ---- 10. the reference is disclosed, never assumed -----------------------
print("10. the reference corpus and its justification are echoed")
out = A.koine_report([{"text": "ες συμμαχοι σφισιν"}], [{"text": "ες σφισιν"}],
                     [{"text": "κοινον"}], reference={"aid": "1", "wid": "002"})
ck(out["reference"]["aid"] == "1" and out["reference"]["wid"] == "002",
   "a caller-supplied reference is echoed back as given")
ck(A.koine_report([{"text": "ες"}], [{"text": "ες"}], [{"text": "ες"}])["reference"]["aid"]
   == A.KOINE_REFERENCE["aid"],
   "with no reference passed, the DECLARED one is used and returned")
ck(A.KOINE_REFERENCE["urn"].startswith("urn:cts:greekLit:tlg"),
   "...and it carries a resolvable URN, so the UI can name and link it")
ck("why" in A.KOINE_REFERENCE and "genre" in A.KOINE_REFERENCE["why"].lower(),
   "the choice of reference is ARGUED in the declaration (genre held constant), "
   "not asserted — the UI prints this text")

# ---- 11. the real works: the claim the design rests on -------------------
# Runs the actual three corpora and checks the two numbers that justify the
# whole third conjunct. Skipped (loudly) if the works are not cached, since
# fetching is a network operation a test must not depend on.
print("11. the real corpora (cached only)")
try:
    from app import texts                    # noqa: E402
    sa = texts.section_texts("0003", "001", window=False)
    sb = texts.section_texts("4029", "001", window=False)
    sc = texts.section_texts("2057", "002", window=False)
except Exception as e:                       # pragma: no cover
    sa = sb = sc = None
    print(f"  skip  could not read the works: {e}")
if sa and sb and sc:
    rr = A.koine_report(sa, sb, sc, limit=200000)
    cen = rr["census"]
    total = sum(cen.values())
    row = {x["norm"]: x for x in rr["rows"]}
    ck(total > 4000, f"the census covers the model author's real vocabulary: {total}")
    ck(0 < cen["archaism"] / total < 0.15,
       f"the sharp class is a minority, not the vocabulary: "
       f"{cen['archaism']}/{total} = {100*cen['archaism']/total:.1f}%")
    ck(cen["avoided"] > cen["archaism"],
       "more words are AVOIDED by the archaizer than revived — vocabulary "
       "attrition is the larger effect, which is the critique's own point")
    # The two-conjunct rule's over-fire, measured rather than argued: every word
    # this report calls `classical` is a word the literal rule would have called
    # an archaism.
    ck(cen["classical"] > cen["archaism"],
       f"the literal 'Koine-absent' rule over-fires: {cen['classical']} words are "
       f"Koine-absent but not overused, against {cen['archaism']} real revivals")
    top = rr["rows"][0]
    ck(top["norm"] == "ες" and top["class"] == "archaism",
       f"the top row is the archaism the instrument should find: {top['word']}")
    ck(row["ες"]["count_c"] == 0 and row["ες"]["count_b"] > row["ες"]["count_a"],
       "ἐς: Koine-absent and overused in B — all three conjuncts on real data")
    ck(row["σφισιν"]["score_ab"] < 0 and row["σφισιν"]["class"] == "archaism",
       "σφίσιν: the pronoun the Koine replaced with αὐτοῖς")
    ck(row["εκκλησια"]["class"] == "avoided" and row["εκκλησια"]["count_c"] > row["εκκλησια"]["count_b"] * 20,
       f"ἐκκλησία: the Koine word the secular archaizer shuns "
       f"(A={row['εκκλησια']['count_a']} B={row['εκκλησια']['count_b']} C={row['εκκλησια']['count_c']})")
    ck(row["συμμαχοι"]["class"] == "classical" and row["συμμαχοι"]["count_b"] < 20,
       "σύμμαχοι: the topic word the literal rule would have called an archaism")

print()
if fails:
    print(f"{len(fails)} FAILED:")
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("all tests ok")

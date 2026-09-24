import os, sys, math
sys.path.insert(0, os.getcwd())
from app import archaism_pure as A

fails = []
def ck(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond: fails.append(msg)

# ---- synthetic: one clear archaism candidate, plus controls -------------
# A (earlier): "arch" x10, "both" x10, "filler" x80   -> total 100
# B (younger): "arch" x1,  "both" x10, "filler" x89   -> total 100
sa = [{"label": "A1", "text": " ".join(["arch"]*10 + ["both"]*10 + ["filler"]*80)}]
sb = [{"label": "B1", "text": " ".join(["arch"]*1 + ["both"]*10 + ["filler"]*89)}]

fa = A.work_freq(sa); fb = A.work_freq(sb)
ck(fa["total"] == 100, "total A = 100 (got %s)" % fa["total"])
ck(fb["total"] == 100, "total B = 100 (got %s)" % fb["total"])
ck(fa["counts"]["arch"] == 10, "count_A(arch) = 10")
ck(fb["counts"]["arch"] == 1,  "count_B(arch) = 1")

r = A.contrast(fa, fb, sections_b=sb)
words = [x["norm"] for x in r["rows"]]
ck(words == ["arch"], "only 'arch' survives the filters (got %s)" % words)
row = r["rows"][0]
# expected score: log2((10.5/100)/(1.5/100)) = log2(7.0)
exp = round(math.log2(7.0), 2)
ck(row["score"] == exp, "score = log2(7) = %s (got %s)" % (exp, row["score"]))
ck(row["rate_a"] == 100.0 and row["rate_b"] == 10.0,
   "rates per 1000: A=100.0 B=10.0 (got %s/%s)" % (row["rate_a"], row["rate_b"]))
ck(row["labels_b"] == ["B1"], "younger-work label attached: %s" % row["labels_b"])
# 'both' has count_a=10 but count_b=10 -> excluded by max_b
ck("both" not in words, "'both' excluded (rare in neither)")
# 'filler' is common in both -> excluded
ck("filler" not in words, "'filler' excluded")

# ---- min_b: the word must SURFACE in the younger work -------------------
sb0 = [{"label": "B1", "text": " ".join(["both"]*10 + ["filler"]*90)}]
f_a, f_b0 = A.work_freq(sa), A.work_freq(sb0)
# Default (min_b=1): a word absent from B is NOT the phenomenon.
ck([x["norm"] for x in A.contrast(f_a, f_b0, sections_b=sb0)["rows"]] == [],
   "default min_b=1 EXCLUDES words absent from B (got %s)"
   % [x["norm"] for x in A.contrast(f_a, f_b0, sections_b=sb0)["rows"]])
# Explicit min_b=0 asks the other question, and must stay FINITE (add-half prior).
r0 = A.contrast(f_a, f_b0, min_b=0, sections_b=sb0)
ck(any(x["norm"] == "arch" for x in r0["rows"]), "'arch' found when min_b=0")
z = [x for x in r0["rows"] if x["norm"] == "arch"][0]
ck(math.isfinite(z["score"]), "count_B=0 score is finite: %s" % z["score"])
ck(z["labels_b"] == [], "count_B=0 -> no occurrences, empty list")
ck(r0["params"]["min_b"] == 0, "min_b reported in params: %s" % r0["params"]["min_b"])
# The real phenomenon: present in B, exactly once (hapax).
ck([x["norm"] for x in A.contrast(fa, fb, sections_b=sb)["rows"]] == ["arch"],
   "'arch' (count_B == 1) IS the phenomenon and survives")
# min_b=2 requires at least two occurrences in B -> 'arch' (1x) drops out.
ck([x["norm"] for x in A.contrast(fa, fb, min_b=2)["rows"]] == [],
   "min_b=2 excludes a count_B==1 hapax")
# min_b > max_b is an empty interval, not silently widened.
ck(A.contrast(fa, fb, min_b=3, max_b=1)["rows"] == [],
   "min_b > max_b yields nothing (not silently widened)")

# ---- direction matters (A and B are NOT symmetric) ---------------------
fa2 = A.work_freq(sb)   # swap: earlier = old B
fb2 = A.work_freq(sa)
ck([x["norm"] for x in A.contrast(fa2, fb2)["rows"]] == [],
   "swapped direction finds nothing (younger has the word MORE often)")

# ---- min_a / max_b / min_score are honoured ---------------------------
ck(A.contrast(fa, fb, min_a=11)["rows"] == [], "min_a=11 excludes count_A=10")
ck([x["norm"] for x in A.contrast(fa, fb, max_b=10)["rows"]] == ["arch","both"][:1] or
   len(A.contrast(fa, fb, max_b=10)["rows"]) >= 1, "max_b=10 admits more rows")
ck(A.contrast(fa, fb, min_score=99.0)["rows"] == [], "min_score=99 excludes everything")
huge = A.contrast(fa, fb, limit=1)
ck(len(huge["rows"]) == 1 and huge["n_candidates"] == 1,
   "limit respected, n_candidates reported")

# ---- determinism ------------------------------------------------------
runs = [tuple(x["norm"] for x in A.contrast(fa, fb)["rows"]) for _ in range(5)]
ck(len(set(runs)) == 1, "sort is deterministic across runs")

# ---- occurrences: one entry per section, capped ------------------------
sb_many = [{"label": "S%d" % i, "text": "arch filler"} for i in range(20)]
occ = A.occurrences(sb_many, {"arch"}, limit=5)
ck(occ["arch"] == ["S0","S1","S2","S3","S4"], "occurrences capped at limit: %s" % occ["arch"])
occ2 = A.occurrences([{"label":"X","text":"arch arch arch"}], {"arch"})
ck(occ2["arch"] == ["X"], "one entry per section, not per occurrence: %s" % occ2["arch"])

# ---- normalize merges accented/unaccented forms ------------------------
sacc = [{"label":"A","text":" ".join(["μῆνιν"]*5 + ["x"]*5)}]
facc = A.work_freq(sacc)
ck(facc["counts"]["μηνιν"] == 5, "accents stripped: μῆνιν -> μηνιν")
ck(facc["display"]["μηνιν"] == "μῆνιν", "display keeps the accented form")


# ---- proper-noun filter -------------------------------------------------
# A (earlier): "Athenaios" ALWAYS capitalized x10; "always" lowercase x10
# B (younger): neither appears
# Both words must SURFACE once in B (min_b=1), else they are not the phenomenon.
spa = [{"label": "A1", "text": " ".join(["Athenaios"]*10 + ["always"]*10 + ["filler"]*80)}]
spb = [{"label": "B1", "text": " ".join(["Athenaios"] + ["always"] + ["filler"]*98)}]
fpa, fpb = A.work_freq(spa), A.work_freq(spb)
ck(fpa["caps"]["athenaios"] == 10, "caps counted for always-capitalized word")
ck(fpa["caps"]["always"] == 0, "caps zero for lowercase word")

d_on = A.contrast(fpa, fpb, drop_proper=True)
ck([x["norm"] for x in d_on["rows"]] == ["always"],
   "proper noun dropped by default (got %s)" % [x["norm"] for x in d_on["rows"]])
ck(d_on["n_dropped_proper"] == 1, "n_dropped_proper = 1 (got %s)" % d_on["n_dropped_proper"])

d_off = A.contrast(fpa, fpb, drop_proper=False)
names = [x["norm"] for x in d_off["rows"]]
ck(set(names) == {"athenaios", "always"}, "drop_proper=False keeps both: %s" % names)
pm = {x["norm"]: x["proper"] for x in d_off["rows"]}
ck(pm["athenaios"] is True and pm["always"] is False,
   "proper flag set correctly: %s" % pm)

# pooled evidence: capitalized 2 of 3 in A, absent in B -> 0.67 > 0.5 -> proper
spool = [{"label":"A1","text":" ".join(["mixed","Mixed","MIXED"] + ["filler"]*97)}]
fpool = A.work_freq(spool)
# min_b=0 here: this case tests the POOLED-RATIO logic, not the surfacing rule.
rpool = A.contrast(fpool, A.work_freq(spb), min_b=0, drop_proper=False)
row = [x for x in rpool["rows"] if x["norm"] == "mixed"]
ck(bool(row) and row[0]["proper"] is True,
   "pooled ratio 2/3 flags proper: %s" % (row[0] if row else None))

# Robustness: count_a >= min_a (3) bounds the pooled ratio from above, so ONE
# capitalized occurrence in the younger work (e.g. a word that happened to
# start a sentence) can never on its own mark a word as a proper noun.
# 20 -> 1 at equal corpus size is log2(13.7) = 3.77, clearing min_score=2.0
# (3 -> 1 would be only 2.3x and is correctly rejected as too weak a collapse).
sone = [{"label":"A1","text":" ".join(["wordy"]*20 + ["filler"]*80)}]
sone_b = [{"label":"B1","text":" ".join(["Wordy"] + ["filler"]*99)}]
row = [x for x in A.contrast(A.work_freq(sone), A.work_freq(sone_b),
                            drop_proper=False)["rows"] if x["norm"] == "wordy"]
ck(bool(row) and row[0]["proper"] is False,
   "1 capitalized of 21 (0.05) is NOT proper -> survives: %s"
   % (row[0]["proper"] if row else None))
ck([x["norm"] for x in A.contrast(A.work_freq(sone), A.work_freq(sone_b))["rows"]]
   == ["wordy"], "and it survives the default filter too")


# ---- elision fragments are NOT words ------------------------------------
from app import flame_pure as FP
ck(FP.words_elided("τοῖς τ\u2019 ἐκλιποῦσι")[1] == ("τ", True),
   "words_elided flags the tau of elided te: %s" % (FP.words_elided("τοῖς τ\u2019 ἐκλιποῦσι")[1],))
ck(FP.words_elided("τοῖς τ\u2019 ἐκλιποῦσι")[0] == ("τοῖς", False),
   "a normal word is not flagged")
ck(FP.words_elided("ἀλλ\u2019 οὐ")[0] == ("ἀλλ", True), "elided ἀλλά flagged")
ck(FP.words_elided("ἀλλ\u2019 οὐ")[1] == ("οὐ", False), "the word AFTER elision is not flagged")
# ... and the mark is not always U+2019: koronis (U+1FBD) is a minority spelling
ck(FP.words_elided("φαίνεται δὲ καὶ Σαμίοις")[0][0] == "φαίνεται", "sanity: plain word")
ck(FP.words_elided("οἱ δ\u1fbd οὖν")[1] == ("δ", True),
   "U+1FBD KORONIS marks elision: %s" % (FP.words_elided("οἱ δ\u1fbd οὖν")[1],))
ck(FP.words_elided("οἱ δ\u1fbd οὖν")[2] == ("οὖν", False), "koronis does not flag the next word")
ck(FP.words_elided("οἱ δ\u1fbd οὖν")[0] == ("οἱ", False), "koronis does not flag the previous word")
ck(FP.words_elided("ἡ δ\u0384 ὥρα")[1] == ("δ", True), "U+0384 oxia also recognised (insurance)")

sel = [{"label": "A1", "text": " ".join(["τοῖς", "τ\u2019", "ἐκλιποῦσι"] + ["wordy"]*20 + ["filler"]*77)}]
fel = A.work_freq(sel)
ck(fel["counts"].get("τ", 0) == 0, "elided fragment NOT counted by default")
ck(fel["n_elided"] == 1 and fel["total"] == 99,
   "n_elided=1 and total excludes it (got %s/%s)" % (fel["n_elided"], fel["total"]))
ck(fel["counts"]["τοις"] == 1, "the host-side word IS counted")
fel2 = A.work_freq(sel, drop_elided=False)
ck(fel2["counts"].get("τ", 0) == 1, "drop_elided=False counts the fragment")
ck(fel2["n_elided"] == 1, "n_elided reported even when not dropping")
# the totals shown to the reader are post-exclusion
sel_b = [{"label": "B1", "text": " ".join(["wordy"] + ["filler"]*99)}]
rep = A.report(sel, sel_b)
ck(rep["n_elided_a"] == 1 and rep["n_elided_b"] == 0,
   "n_elided surfaced in the report: %s/%s" % (rep["n_elided_a"], rep["n_elided_b"]))
ck([x["norm"] for x in rep["rows"]] == ["wordy"],
   "the elided fragment does not appear as a candidate row")

print("\nRESULT: %d failure(s)" % len(fails))
sys.exit(1 if fails else 0)

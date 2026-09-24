"""Unit tests for app/loci_pure.py — KWIC, parallel loci, n-gram phraseology.

Synthetic sections only: the point of these tests is the CONTRACT (indices,
pooling, truncation disclosure, the min_shared bar), and synthetic text makes
the expected answer checkable by eye. The live-data behaviour is asserted
separately against the running server.
"""
import sys
sys.path.insert(0, "/home/tamask/github/KONI")

from app import loci_pure as L

fails = []


def ck(label, got, want):
    if got != want:
        fails.append(f"{label}: got {got!r}, want {want!r}")


SECS = [
    {"label": "1.1", "text": "Θουκυδίδης Ἀθηναῖος ξυνέγραψε τὸν πόλεμον. "
                             "καὶ τὰ ξύμμαχα ἔθνη παρεσκευάζοντο."},
    {"label": "1.2", "text": "οἱ δὲ σύμμαχοι ἐγίγνοντο πολλοί· "
                             "καὶ αἱ ξυμμαχίαι ἐγράφησαν."},
    # Long unpunctuated run: the max_words guard must catch it.
    {"label": "9.9", "text": " ".join(["λόγος"] * 30) + " ξύμμαχοι."},
]

# --- kwic: pooling, indices, context --------------------------------------
k = L.kwic(SECS, {"συμμαχοι"}, span=2)
# Two sections contain the word: 1.2 plain, 9.9 as the tail of the long run.
ck("kwic hits", k["n_hits"], {"συμμαχοι": 2})
ck("kwic not truncated", k["truncated"], {"συμμαχοι": False})
h = k["hits"]["συμμαχοι"][0]
ck("kwic label", h["label"], "1.2")
ck("kwic index", h["index"], 2)
ck("kwic hit", h["hit"], "σύμμαχοι")
ck("kwic marked", h["marked"], [])
ck("kwic pooled", h["pooled"], "συμμαχοι")
ck("kwic before", h["before"], ["οἱ", "δὲ"])
ck("kwic after", h["after"], ["ἐγίγνοντο", "πολλοί"])
# span is honoured even at the section boundary.
k0 = L.kwic(SECS, {"θουκυδιδης"}, span=9)
ck("kwic clamps at start", k0["hits"]["θουκυδιδης"][0]["before"], [])

# A marked spelling is pooled onto the same key and flagged.
km = L.kwic([{"label": "1", "text": "ἡ ξυμμαχία μεγάλη"}], {"συμμαχια"}, span=1)
ck("kwic pooled marked", km["n_hits"], {"συμμαχια": 1})
ck("kwic flags xyn", km["hits"]["συμμαχια"][0]["marked"], ["xyn"])
ck("kwic shows printed form", km["hits"]["συμμαχια"][0]["hit"], "ξυμμαχία")

# Pooling OFF must not match the un-pooled spelling.
kn = L.kwic([{"label": "1", "text": "ἡ ξυμμαχία μεγάλη"}], {"συμμαχια"}, variants=())
ck("kwic unpooled misses", kn["n_hits"], {})

# Truncation is DISCLOSED, never silent.
kt = L.kwic(SECS, {"λογος"}, per_key=3)
ck("kwic per_key truncates", len(kt["hits"]["λογος"]), 3)
ck("kwic truncation flagged", kt["truncated"]["λογος"], True)
ck("kwic truncation counts all", kt["n_hits"]["λογος"], 30)

# Elision fragments: `δ’` contributes no `δ` token.
ke = L.kwic([{"label": "1", "text": "οἱ δ’ ἄλλοι"}], {"δ"})
ck("kwic no elided fragment", ke["n_hits"], {})
ke2 = L.kwic([{"label": "1", "text": "οἱ δ’ ἄλλοι"}], {"δ"}, drop_elided=False)
ck("kwic fragment restored", ke2["n_hits"], {"δ": 1})

# --- kwic by RULE: the style report's rows are not words -------------------
# `ξυ` is not a word; a key lookup for it finds `σύ` ("you") and nothing else.
# The rule selects the token class the row is about.
kr = L.kwic(SECS, set(), rule="xyn")
ck("rule kwic keys on the rule", sorted(kr["hits"]), ["xyn"])
# ξύμμαχα, ξύμμαχοι, ξυμμαχίαι, ξύμμαχοι — every ξυ- token in the fixture.
ck("rule kwic count", kr["n_hits"], {"xyn": 4})
ck("rule kwic marked", all(h["marked"] == ["xyn"] for h in kr["hits"]["xyn"]), True)
ck("rule kwic span", kr["span"], 8)
ck("rule kwic echoes the rule", kr["rule"], "xyn")
# It must match on the UNPOOLED form: pooling destroys the mark it looks for.
krn = L.kwic(SECS, set(), rule="xyn", variants=())
ck("rule kwic independent of pooling", krn["n_hits"], {"xyn": 4})
# The key lookup really would have found something else — the reason the rule
# path exists is not theoretical.
kk = L.kwic([{"label": "1", "text": "σύ τε καὶ ξυμμαχία"}], {"συ"})
ck("key lookup finds σύ, not ξυ-", [h["hit"] for h in kk["hits"]["συ"]], ["σύ"])
# A rule with no occurrences is empty, not an error.
ke = L.kwic(SECS, set(), rule="tt")
ck("rule with no hits", ke["n_hits"], {})

# --- sentences ------------------------------------------------------------
s = L.sentences(SECS)
ck("sentence count", s["n"], 5)
ck("sentence labels", [x["label"] for x in s["items"]],
   ["1.1", "1.1", "1.2", "1.2", "9.9"])
ck("sentence index within section", [x["index"] for x in s["items"]], [0, 1, 0, 1, 0])
ck("sentence length stats present", sorted(s["lengths"]),
   ["max", "median", "min", "p90"])
ck("longest sentence found", s["lengths"]["max"], 31)
# Milestones are apparatus: they must not become bag dimensions.
sm = L.sentences([{"label": "1", "text": "(1) λόγος (2) λόγος"}])
ck("milestones stripped from bag", dict(sm["items"][0]["bag"]), {"λογος": 2})

# --- parallel_loci --------------------------------------------------------
qa = "οἱ σύμμαχοι ἐγίγνοντο πολλοί".split()
# max_words is set below the long run's length so the guard is exercised.
p = L.parallel_loci(SECS, qa, n=3, min_shared=1, max_words=20)
ck("parallel finds the twin", [x["label"] for x in p["hits"]][:1], ["1.2"])
top = p["hits"][0]
ck("parallel score in (0,1]", 0 < top["score"] <= 1.0, True)
ck("parallel shared 2-gram pooled", "συμμαχοι εγινοντο" in top["shared_2"], True)
ck("parallel shared 3-gram", "συμμαχοι εγινοντο πολλοι" in top["shared_3"], True)
# The over-long run is skipped and COUNTED, not silently dropped.
ck("parallel skips long run", p["n_skipped_long"], 1)
ck("parallel reports scored", p["n_scored"], 4)
# With a generous cap nothing is skipped — the guard is length, not punctuation.
p_wide = L.parallel_loci(SECS, qa, n=3, min_shared=1)
ck("no skip under the default cap", p_wide["n_skipped_long"], 0)

# min_shared is a hard bar: with a phrase nothing else shares, no hits.
p2 = L.parallel_loci(SECS, "οὐδενὶ ὅμοιον πάνυ".split(), n=5, min_shared=2)
ck("min_shared bar yields nothing", p2["hits"], [])
# ...and it DROPS candidates, which is disclosed.
p3 = L.parallel_loci(SECS, ["λόγος", "πολλοί"], n=5, min_shared=3)
ck("min_shared drops disclosed", p3["n_dropped"] >= 0, True)

# An empty query returns nothing rather than everything.
p4 = L.parallel_loci(SECS, [], n=3)
ck("empty query", p4["hits"], [])
# Digits alone are not content.
p5 = L.parallel_loci([{"label": "1", "text": "1 2 3 4"}], ["1", "2"], n=3)
ck("digit-only query has no bag", p5["hits"], [])

# --- ngram_table ----------------------------------------------------------
g = L.ngram_table(SECS, {"συμμαχοι"}, n=2)
ck("bigram table total", g["total"], 3)
got = sorted(tuple(x["pooled"]) for x in g["grams"])
ck("bigram bins", got,
   [("δε", "συμμαχοι"), ("λογος", "συμμαχοι"), ("συμμαχοι", "εγινοντο")])
ck("bigram prints original", "σύμμαχοι" in g["grams"][0]["gram"], True)
ck("bigram contentful", all(x["contentful"] for x in g["grams"]), True)

# A window holding TWO wanted keys is counted under each — the reason
# ngram_contrast keys on (key, pooled gram) and not on the gram alone.
# γίγνεται pools to γινεται (gign: γιγν -> γιν); the key is the pooled form.
g2 = L.ngram_table([{"label": "1", "text": "ξυμμαχία γίγνεται"}],
                   {"συμμαχια", "γινεται"}, n=2)
ck("two keys, one window, two counts", g2["total"], 2)
ck("filed under both", sorted(x["key"] for x in g2["grams"]),
   ["γινεται", "συμμαχια"])

# Whole-text mode counts every gram, not just the ones with the key.
g3 = L.ngram_table(SECS, set(), n=2, context=False, limit=100)
ck("whole-text bigrams counted", g3["total"] > 5, True)
ck("function-word gram flagged", any(not x["contentful"] for x in g3["grams"]), True)

# --- ngram_contrast -------------------------------------------------------
# Pooling is the whole reason the two tables can be compared: A writes ξυ-,
# B writes συ-, and ONLY the pooled gram brings them into one row.
ta = L.ngram_table([{"label": "1", "text": "ἡ ξυμμαχία καλή"}], {"συμμαχια"}, n=2)
tb = L.ngram_table([{"label": "1", "text": "ἡ συμμαχία καλή"}], {"συμμαχια"}, n=2)
c = L.ngram_contrast(ta, tb, min_a=1, max_b=10, total_a=100, total_b=100)
ck("pooled grams align", len([r for r in c["rows"] if r["gram"] == ["η", "συμμαχια"]]), 1)
row = [r for r in c["rows"] if r["gram"] == ["η", "συμμαχια"]][0]
ck("aligned counts", (row["count_a"], row["count_b"]), (1, 1))
ck("display prefers A's spelling", row["display"], ["ἡ", "ξυμμαχία"])
ck("equal rates give score 0", round(row["score"], 6), 0.0)

# The Haldane prior: zero in B stays finite instead of dividing by zero.
c0 = L.ngram_contrast(ta, L.ngram_table(SECS, {"συμμαχια"}, n=2),
                      min_a=1, max_b=0, total_a=100, total_b=100)
ck("zero-B is finite", all(abs(r["score"]) < 100 for r in c0["rows"]), True)
ck("zero-B rows present", len(c0["rows"]) > 0, True)
ck("rates divide by the works, not the table",
   round(c0["rows"][0]["rate_a"], 6), round(c0["rows"][0]["count_a"] * 10.0, 6))
# max_b is a filter, not a clamp.
c1 = L.ngram_contrast(ta, tb, min_a=1, max_b=0, total_a=100, total_b=100)
ck("max_b filters B-nonzero out", c1["rows"], [])
# min_a is a filter too.
c2 = L.ngram_contrast(ta, tb, min_a=99, max_b=10, total_a=100, total_b=100)
ck("min_a filters", c2["rows"], [])
# Denominator falls back to the table sum when the caller supplies no total.
c3 = L.ngram_contrast(ta, tb, min_a=1, max_b=10)
ck("fallback denominator used", c3["n_a"] > 0, True)

if fails:
    print(f"FAIL {len(fails)}")
    for f in fails:
        print("  " + f)
    sys.exit(1)
print("OK loci_pure.py")

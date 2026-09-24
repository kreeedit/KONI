"""Regression tests for app/lemmas_pure.py (requirement #1: lemmatisation and
inflectional aggregation).

These run on HAND-BUILT corpora, which is a real constraint and not a detail:
`LemmaIndex` is a CORPUS resolver, not a lexicon. It decides between readings
by counting the forms a corpus exhibits, so a corpus of eight tokens gives it
nothing to count and declaration order decides — the answer then depends on
where a rule sits in a tuple, which is not a property worth testing. Every
corpus below therefore repeats the paradigm the way prose does and adds an
unrelated lexeme for the resolver to weigh it against. The accuracy figures for
real text live in lemmas_pure.ACCURACY and are measured against the gold
treebanks; nothing here claims to measure accuracy.
"""
import os
import sys

sys.path.insert(0, os.getcwd())
from app import lemmas_pure as L              # noqa: E402
from app.variants import DEFAULT as V         # noqa: E402

fails = []


def ck(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        fails.append(msg)


def corpus(text, reps=1):
    """A token counter from space-separated text, repeated `reps` times."""
    forms = {}
    for _ in range(reps):
        for f in text.split():
            forms[f] = forms.get(f, 0) + 1
    return forms


FILLER = ("λογος λογου λογον λογων λογοι λογοις πολις πολεως πολει πολιν "
          "πολεις πολεων χωρα χωρας χωραν τιμη τιμης τιμην")

# ---- 1. the requirement: one lexeme, one key -----------------------------
# ὁπλίτας / ὁπλῖται / ὁπλιτῶν are three cases of one noun. A surface-form
# report makes three rows of them; this layer must make one, and the key must
# be the citation form the requirement names.
para = "οπλιτης οπλιτου οπλιτη οπλιτην οπλιται οπλιτων οπλιταις οπλιτας"
para_forms = para.split()
forms = corpus(para + " " + FILLER, reps=4)
ix = L.LemmaIndex(forms, V)
keys = {f: ix.analyse(f)[1].lemma for f in para_forms}
ck(set(keys.values()) == {"οπλιτης"},
   "the whole paradigm collapses to ONE key ὁπλίτης (got %s)" % sorted(set(keys.values())))
ck(all(ix.key_of(keys[f]) == "οπλιτης" for f in para_forms),
   "and every form's key pools there")

# The same thing through the report the server actually calls, where counts
# are what the table divides by. The corpus is one work, so B is empty and the
# A column must carry every token.
A = [{"label": "A1", "text": para + " " + FILLER + " " + para + " " + FILLER}]
B = []
rep = L.lemma_report(A, B, variants=V)
by = {r["key"]: r for r in rep["rows"]}
row = by.get("οπλιτης")
ck(row is not None, "ὁπλίτης is a row (keys: %s)" % sorted(by))
if row:
    ck(row["count_a"] == 16, "all 16 paradigm tokens count together (got %s)" % row["count_a"])
    ck(row["n_forms_a"] == 8, "and are 8 distinct forms (got %s)" % row["n_forms_a"])
    # The breakdown is the disclosure: the row's count must be checkable
    # against the forms it names, or the row is unfalsifiable.
    ck(sum(f["count_a"] for f in row["forms"]) == row["count_a"],
       "the breakdown sums to the row's A count")
    ck(sum(f["count_b"] for f in row["forms"]) == row["count_b"],
       "the breakdown sums to the row's B count")
ck("οπλιτας" not in by and "οπλιται" not in by and "οπλιτων" not in by,
   "no separate rows for the oblique cases")
ck(by.get("λογος", {}).get("count_a") == 12,
   "λόγος/λόγον/λόγου aggregate (got %s)" % by.get("λογος", {}).get("count_a"))
ck("λογον" not in by and "λογου" not in by and "λογων" not in by,
   "the 2nd-declension oblique cases do not leak into their own rows")

# ---- 2. pooling happens LAST ---------------------------------------------
# θάλασσα and θάλαττα must lemmatise on their OWN spelling — the ττ/σσ
# correspondence is the thing the style report measures, and `unify` erases
# it — and only then meet under one key. If pooling ran first, the two would
# be one form and the ττ rule would have no evidence left to count.
sea = corpus("θαλαττα θαλαττης θαλαττη θαλατταν θαλασσα θαλασσης θαλασση "
             "θαλασσαν " + FILLER, reps=3)
ixs = L.LemmaIndex(sea, V)
a, ha, _ = ixs.analyse("θαλαττης")
b, hb, _ = ixs.analyse("θαλασσης")
ck(ha.lemma != hb.lemma, "ττ and σσ forms lemmatise on their own spelling"
   " (%s vs %s)" % (ha.lemma, hb.lemma))
ck(ixs.key_of(ha.lemma) == ixs.key_of(hb.lemma),
   "and pool to ONE key afterwards (%s vs %s)"
   % (ixs.key_of(ha.lemma), ixs.key_of(hb.lemma)))
tt = "θάλαττα θαλάττης θαλατταν θάλασσα θαλάσσης θαλασσαν"
po = L.lemma_report([{"label": "A1", "text": tt}],
                    [{"label": "B1", "text": "θάλασσα"}], variants=("tt",))
ck(any(r["count_a"] == 6 for r in po["rows"]),
   "with the ττ rule on, all six tokens are one row: %s"
   % [(r["key"], r["count_a"]) for r in po["rows"]])

# ---- 3. the resolver is not self-inflating -------------------------------
# A form must not vote for its own disambiguation — that is the whole reason
# the counts in `_key` subtract it. The test is the INVARIANCE, not a zero
# weight: whatever the resolver decides about `θαλάσσης` must be decided by the
# rest of the paradigm, so multiply the form's own frequency tenfold and the
# answer may not change. (An earlier version of this test asserted that no
# weight existed under the form's own lemma, which is a different and false
# claim — a form that legitimately IS its own lemma does carry its own weight.)
base = {"θαλασσα": 3, "θαλασσαν": 3, "θαλασσης": 6, "θαλασση": 3}
loud = dict(base, θαλασσης=60)
quiet = L.LemmaIndex(dict(base), V).analyse("θαλασσης")[1].lemma
shout = L.LemmaIndex(dict(loud), V).analyse("θαλασσης")[1].lemma
ck(quiet == shout,
   "a form's own frequency does not decide its lemma (%s vs %s)" % (quiet, shout))
ck(quiet == "θαλασσα",
   "and the rest of the paradigm decides it (%s)" % quiet)

# ---- 4. morphology the rules cannot see, inferred from the corpus ---------
# A noun whose stem shows a plural in -α is a neuter, so its -ον form files
# under ITSELF (χωρίον) and not under -ος (χώριος). λόγος has no λόγᾱ, so
# λόγον stays a masculine accusative.
m = L.LemmaIndex({"χωριον": 14, "χωρια": 3, "χωριου": 9,
                  "λογον": 20, "λογος": 30, "λογου": 25}, V)
ck(m.analyse("χωριον")[1].lemma == "χωριον", "χωρίον → χωρίον (neuter)")
ck(m.analyse("λογον")[1].lemma == "λογος", "λόγον → λόγος (masculine)")
# And the 1st-declension inference, which is what makes the paradigm above
# possible: an attested -ου genitive proves the lexeme is masculine -ης, since
# -ου is never a first-declension feminine. A feminine -η noun has no such
# genitive and must be left alone.
fem = L.LemmaIndex(corpus("τιμη τιμης τιμη τιμην " + FILLER, reps=3), V)
ck(fem.analyse("τιμης")[1].lemma == "τιμη", "τιμῆς → τιμή (feminine, no -ου)")
ck(fem.analyse("τιμην")[1].lemma == "τιμη", "τιμήν → τιμή")

# ---- 5. the augment -------------------------------------------------------
# ἐποίησε carries the syllabic augment; without stripping it the aorist gives
# `ἐποιεω`, which is not a headword, and the aorist never meets the present.
ck(any(c.lemma == "ποιεω" for c in L.candidates("εποιησε")),
   "ἐποίησε offers ποιέω as a reading")
ck(any(c.lemma == "λυω" for c in L.candidates("ελυθη")),
   "ἐλύθη offers λύω as a reading")

# ---- 6. the accuracy disclosure is real, not a placeholder ---------------
acc = L.ACCURACY
ck(acc["thucydides"]["n_tokens_all"] > 20000,
   "the gold token count is the measured one (got %s)"
   % acc["thucydides"]["n_tokens_all"])
ck(0.70 < acc["thucydides"]["exact"] < 0.80,
   "Thucydides exact accuracy is measured (got %s)" % acc["thucydides"]["exact"])
ck(acc["thucydides"]["exact"] <= acc["thucydides"]["within"],
   "within-candidate recall is never below exact accuracy")
ck(acc["thucydides"]["purity_noun"] > acc["thucydides"]["purity_verb"],
   "nouns aggregate better than verbs — the disclosed limit")
ck(L.describe()["accuracy"] == acc, "describe() carries the same figures")

# ---- 7. the expander returns the same forms the row was built from --------
# A loci panel that searches a hand-assembled paradigm returns hits that do
# not add up to the count printed beside the row. The forms come from the same
# index, so they must.
para_A = [{"label": "A1", "text": para + " " + FILLER}]
got = L.lemma_key_lookup(para_A, B, "οπλιτης", V)
ck(got["found"] and len(got["forms"]) == 8,
   "key lookup returns 8 forms (got %s)" % len(got["forms"]))
ck(tuple(f["form"] for f in got["forms"]) == L.key_forms(para_A, B, "οπλιτης", V),
   "key_forms and lemma_key_lookup agree")
ck(sum(f["count_a"] for f in got["forms"]) == 8,
   "and their counts sum to the row's")
ck(L.lemma_key_lookup(para_A, B, "nosuchlemma", V)["found"] is False,
   "an unknown key reports found=False instead of an empty success")

# ---- 8. an unanalysable form is not silently called its own lemma ---------
u = L.candidates("ξζξζξ")
ck(u and u[0].source == "unreduced" and u[0].lemma == "ξζξζξ",
   "an unmatched form comes back labelled `unreduced`")

print("\nRESULT: %d failure(s)" % len(fails))
sys.exit(1 if fails else 0)

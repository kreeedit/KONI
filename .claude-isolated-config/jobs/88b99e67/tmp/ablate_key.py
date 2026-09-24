"""Ablate _key() ordering against the Thucydides gold, without editing the repo.

Each variant re-implements LemmaIndex._key with a different sort tuple and
measures exact-match + aggregation purity for Thucydides 1.
"""
import json
import sys
import dataclasses
from collections import Counter, defaultdict

sys.path.insert(0, "/home/tamask/github/KONI")
from app.flame_pure import normalize
from app import lemmas_pure as L
from app.variants import DEFAULT as VAR

GOLD = json.load(open("/home/tamask/github/KONI/.claude-isolated-config/jobs/88b99e67/tmp/gold_thuc.json"))


def make_key(order, headword=True, neuter=True):
    def _key(self, c, form, n, own, i):
        support = self.fcount.get(c.lemma, 0) - (1 if own == c.lemma else 0)
        weight = self.weight.get(c.lemma, 0) - (n if own == c.lemma else 0)
        neu = 0
        if neuter and c.pos == "noun" and c.lemma.endswith("ον") and c.stem:
            neu = 1 if self.forms.get(c.stem + "α") else 0
        msc = 0
        if c.stem:
            if c.lemma.endswith(("ης", "ας")):
                if form != c.stem + "ου" and not self.forms.get(c.stem + "ος") and self.forms.get(c.stem + "ου"):
                    msc = 2
            elif c.lemma.endswith(("η", "α")):
                if form != c.lemma + "ν" and self.forms.get(c.lemma + "ν"):
                    msc = 1
        rule = L.BY_NAME.get(c.rule)
        hw = 1 if (headword and c.lemma == form and "nom_sg" in c.rule) else 0
        parts = {
            "L": len(rule.ending) if rule else 0,
            "S": support,
            "W": weight,
            "N": neu,
            "H": hw,
            "M": msc,
        }
        return tuple(-parts[t] for t in order) + (i,)
    return _key


def elided(f, g):
    return len(f) < len(g) and g.startswith(f)


def with_templates(revert):
    """Rebuild RULES with (or without) the two template widenings."""
    if not revert:
        L.RULES = _RULES_ORIG
        return
    out = []
    for r in _RULES_ORIG:
        if r.name == "a_acc_sg_f":
            r = dataclasses.replace(r, lemmas=("{stem}ης", "{stem}η", "{stem}ας"),
                                    infl="acc sg fem / acc sg masc")
        elif r.name == "a_gen_pl":
            r = dataclasses.replace(r, lemmas=("{stem}ης", "{stem}ας"), infl="gen pl masc")
        out.append(r)
    L.RULES = tuple(out)


def evaluate(order, headword, neuter, revert=False):
    with_templates(revert)
    L.LemmaIndex._key = make_key(order, headword, neuter)
    forms = Counter(normalize(f) for f, _, _ in GOLD)
    ix = L.LemmaIndex(forms, VAR)
    n = exact = 0
    buckets = defaultdict(set)
    for form, lemma, pos in GOLD:
        f, g = normalize(form), normalize(lemma)
        if not f or not g or elided(f, g):
            continue
        n += 1
        _, chosen, _ = ix.analyse(f)
        exact += chosen.lemma == g
        buckets[g].add(ix.key_of(chosen.lemma))
    one = sum(1 for g in buckets if len(buckets[g]) == 1)
    return exact / n, one / len(buckets), n


VARIANTS = [
    ("MSLWN", ("M", "S", "L", "W", "N"), False),
    ("SLW", ("S", "L", "W", "N"), False),
    ("MSLW", ("M", "S", "L", "W"), False),
    ("SMLW", ("S", "M", "L", "W"), False),
    ("LSW", ("L", "S", "W", "N"), False),
    ("LSWH", ("L", "S", "W", "N", "H"), True),
]

if __name__ == "__main__":
    _RULES_ORIG = L.RULES
    print(f"gold Thucydides tokens: {len(GOLD)}")
    for revert in (False, True):
        tag = "old templates" if revert else "new templates"
        for name, order, hw in VARIANTS:
            e, p, n = evaluate(order, hw, neuter=True, revert=revert)
            print(f"  {tag:14s} {name:6s}  exact {e*100:6.2f}%   purity {p*100:6.2f}%")
    L.RULES = _RULES_ORIG

"""Aggregation purity by gold POS, for the two gold corpora."""
import json
import sys
from collections import Counter, defaultdict

sys.path.insert(0, "/home/tamask/github/KONI")
from app.flame_pure import normalize
from app.lemmas_pure import LemmaIndex
from app.variants import DEFAULT as VAR, unify


def elided(f, g):
    return len(f) < len(g) and g.startswith(f)


def make_key(order):
    def _key(self, c, form, n, own, i):
        support = self.fcount.get(c.lemma, 0) - (1 if own == c.lemma else 0)
        weight = self.weight.get(c.lemma, 0) - (n if own == c.lemma else 0)
        neu = 0
        if c.pos == "noun" and c.lemma.endswith("ον") and c.stem:
            neu = 1 if self.forms.get(c.stem + "α") else 0
        from app.lemmas_pure import BY_NAME
        rule = BY_NAME.get(c.rule)
        parts = {"L": len(rule.ending) if rule else 0, "S": support,
                 "W": weight, "N": neu}
        return tuple(-parts[t] for t in order) + (i,)
    return _key


if __import__("os").environ.get("ORDER"):
    LemmaIndex._key = make_key(tuple(__import__("os").environ["ORDER"]))

for name, path in (("thucydides", "gold_thuc.json"), ("polybius", "gold_polyb.json")):
    gold = json.load(open("/home/tamask/github/KONI/.claude-isolated-config/jobs/88b99e67/tmp/" + path))
    forms = Counter(normalize(f) for f, _, _ in gold)
    ix = LemmaIndex(forms, VAR)
    per = defaultdict(set)
    pos_of = {}
    for form, lemma, pos in gold:
        f, g = normalize(form), normalize(lemma)
        if not f or not g or elided(f, g):
            continue
        _, chosen, _ = ix.analyse(f)
        per[g].add(unify(chosen.lemma, VAR))
        pos_of.setdefault(g, {"n": "noun", "a": "adjective", "v": "verb", "d": "adverb"}.get(pos[0], pos[0]))
    for p in ("noun", "adjective", "verb", "adverb"):
        keys = [g for g in per if pos_of.get(g) == p]
        one = sum(1 for g in keys if len(per[g]) == 1)
        print(f"  {name:11s} purity_{p:10s} {one}/{len(keys)} = {100*one/len(keys):.3f}")

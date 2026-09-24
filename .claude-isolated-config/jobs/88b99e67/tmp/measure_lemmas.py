"""Measure app/lemmas_pure.py against gold treebank lemmatisation.

Gold: Perseus AGDT v2.1 (CC BY-SA 3.0), Thucydides 1 + Polybius. Used at
development time only; not redistributed.
"""
import json
import sys
from collections import Counter

sys.path.insert(0, "/home/tamask/github/KONI")
from app.flame_pure import normalize                      # noqa: E402
from app.lemmas_pure import LemmaIndex, candidates        # noqa: E402
from app.variants import DEFAULT as VAR, unify            # noqa: E402


def evaluate(name, path):
    gold = json.load(open(path))
    forms = Counter(normalize(f) for f, _, _ in gold)
    ix = LemmaIndex(forms, VAR)

    def elided(f, g):
        # The production path DROPS a token that an elision mark follows
        # (`delta'` arrives as `δ`, not as `δέ`). The treebank keeps them as
        # tokens, so counting them here would measure tokens the report never
        # sees. The signature is exact: the form is a proper prefix of its own
        # gold lemma.
        return len(f) < len(g) and g.startswith(f)

    for label, keep in (("all gold tokens", lambda f, g: True),
                        ("production tokens", lambda f, g: not elided(f, g))):
        n = exact = within = unreduced = amb = 0
        wrong = Counter()
        for form, lemma, pos in gold:
            f, g = normalize(form), normalize(lemma)
            if not f or not g or not keep(f, g):
                continue
            n += 1
            cands, chosen, ambiguous = ix.analyse(f)
            amb += ambiguous
            unreduced += chosen.source == "unreduced"
            got, want = unify(chosen.lemma, VAR), unify(g, VAR)
            if got == want:
                exact += 1
                within += 1
            else:
                if any(unify(c.lemma, VAR) == want for c in cands):
                    within += 1
                wrong[(f, g, got, chosen.pos, chosen.rule, chosen.source)] += 1
        print(f"--- {name} / {label}: {n} tokens")
        print(f"    exact        {exact}/{n}  = {100*exact/n:.2f}%")
        print(f"    within cands {within}/{n}  = {100*within/n:.2f}%")
        print(f"    ambiguous    {amb}/{n}  = {100*amb/n:.2f}%")
        print(f"    unreduced    {unreduced}/{n}  = {100*unreduced/n:.2f}%")
        print(f"    distinct wrong types: {len(wrong)}")
        print("    top 40 errors (form -> gold | got) [count, pos, rule, source]:")
        for (f, g, got, pos, rule, src), c in wrong.most_common(40):
            print(f"      {c:5d}  {f:<18} -> {g:<16} | {got:<16} {pos:<8} {rule:<18} {src}")
        if keep(  "", "") is False:
            break

    # AGGREGATION PURITY — the figure that actually tests what the layer is for.
    # A wrong headword is a cosmetic error; the table still counts the lexeme
    # correctly, because a consistently wrong headword still groups its forms
    # together. What would break the report is INCONSISTENCY: if two forms of
    # one lexeme land in two buckets, its rate is torn in half — the exact
    # defect this module exists to repair. So: for every gold lemma, how many
    # buckets did its tokens end up in?
    n = 0
    single = 0
    buckets = Counter()
    for form, lemma, pos in gold:
        f, g = normalize(form), normalize(lemma)
        if not f or not g or elided(f, g):
            continue
        n += 1
        _, chosen, _ = ix.analyse(f)
        buckets[(g, unify(chosen.lemma, VAR))] += 1
    per_lemma = Counter()
    for (g, _got), c in buckets.items():
        per_lemma[g] += 1
    print(f"--- {name} / aggregation purity over {len(per_lemma)} gold lemmas")
    for g, k in per_lemma.most_common(0):
        pass
    frac = Counter(per_lemma.values())
    tot_lemmas = len(per_lemma)
    print(f"    lemmas landing in ONE bucket  : {frac[1]}/{tot_lemmas}"
          f"  = {100*frac[1]/tot_lemmas:.2f}%")
    print(f"    land in 2 / 3 / 4+ buckets    : {frac[2]}/{frac[3]}/{sum(v for k, v in frac.items() if k >= 4)}")
    print("    worst split (gold lemma -> distinct buckets), by token count:")
    worst = sorted(per_lemma.items(), key=lambda kv: -kv[1])[:12]
    for g, k in worst:
        if k <= 1:
            continue
        got = sorted(((k, c) for (gg, k), c in buckets.items() if gg == g),
                     key=lambda x: -x[1])
        print(f"      {g:<16} {k} buckets: " +
              ", ".join(f"{b}={c}" for b, c in got[:6]))


if __name__ == "__main__":
    evaluate("Thucydides 1", "/home/tamask/github/KONI/.claude-isolated-config/jobs/88b99e67/tmp/gold_thuc.json")
    evaluate("Polybius", "/home/tamask/github/KONI/.claude-isolated-config/jobs/88b99e67/tmp/gold_polyb.json")

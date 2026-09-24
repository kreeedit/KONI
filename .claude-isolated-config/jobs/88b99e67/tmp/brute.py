"""Brute-force reference: union-find over ALL pairs with lev ratio >= threshold.
Compare with cluster_pairs, and attribute every missed merge to a gate."""
import sys, inspect, textwrap, random, itertools
sys.path.insert(0, "/home/tamask/github/KONI")
from collections import Counter
from app import flame_pure as fp

SRC = inspect.getsource(fp.cluster_pairs)
GATE = """            # 4-gram Jaccard as a cheap proxy for edit similarity
            if 2 * inter / (len(ha) + len(hb)) < threshold * 0.5:
                continue
"""
L1GATE = """            _ca = Counter(cores[ia]); _cb = Counter(cores[ib])
            _l1 = sum((_ca - _cb).values()) + sum((_cb - _ca).values())
            if 1.0 - _l1 / (2.0 * (la + lb)) < threshold:
                continue
"""
NS = {"levenshtein_ratio": fp.levenshtein_ratio, "Counter": Counter,
      "_shingles": fp._shingles}
ns_l1 = dict(NS)
exec(textwrap.dedent(SRC.replace(GATE, L1GATE)), ns_l1)
cluster_L1 = ns_l1["cluster_pairs"]


def exact_groups(cores, threshold):
    """Union-find over the true similarity graph. Returns frozenset of frozensets."""
    U = len(cores)
    par = list(range(U))

    def f(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x
    for a in range(U):
        for b in range(a + 1, U):
            if fp.levenshtein_ratio(cores[a], cores[b]) >= threshold:
                ra, rb = f(a), f(b)
                if ra != rb:
                    par[max(ra, rb)] = min(ra, rb)
    g = {}
    for i in range(U):
        g.setdefault(f(i), []).append(i)
    return {k: sorted(v) for k, v in g.items()}


def cores_of(sigs):
    seen, out = {}, []
    for s in sigs:
        if s not in seen:
            seen[s] = 1
            out.append(s)
    return out


def evaluate(sigs, threshold=0.85, tag=""):
    cores = cores_of(sigs)
    U = len(cores)
    if U > 400:
        return None
    idx = {c: i for i, c in enumerate(cores)}
    ex = exact_groups(cores, threshold)
    # exact grouping over cores -> our own pair partition
    exact_pairsets = {}
    for root, members in ex.items():
        exact_pairsets[root] = members
    got = fp.cluster_pairs(sigs, threshold=threshold, min_size=2)
    got_l1 = cluster_L1(sigs, threshold=threshold, min_size=2)
    # our grouping over cores: reconstruct from clusters of size>=2, plus singles
    def as_sets(res, min_size=2):
        groups = {}
        assigned = set()
        for c in res["clusters"]:
            groups[c["id"]] = sorted({idx_of[p] for p in c["members"]})
            assigned |= set(c["members"])
        for p in range(len(sigs)):
            if p not in assigned:
                groups[("s", p)] = [idx_of[p]]
        return set(frozenset(v) for v in groups.values())

    idx_of = [idx[s] for s in sigs]
    exsets = set(frozenset(v) for v in ex.values())
    gs = as_sets(got)
    gl = as_sets(got_l1)
    print(f"[{tag}] U={U} exact_groups={len(exsets)} jaccard={len(gs)} L1={len(gl)}",
          "jaccard==exact:", gs == exsets, " L1==exact:", gl == exsets)
    if gl != exsets:
        print("   L1 divergence:", sorted(x for x in gl if x not in exsets)[:3],
              sorted(x for x in exsets if x not in gl)[:3])
    if gs != exsets:
        print("   jaccard divergences (missing groups):",
              sorted(sorted(x) for x in exsets - gs)[:5])
    return gs == exsets, gl == exsets


random.seed(7)
ALPHA = "abcdefg"
cases = []
# hand-built adversarial cases
cases.append(["aaaa", "aaab", "aabb", "abbb", "bbbb"])           # repetitive
cases.append(["abcdef", "abcdeg", "abcdeh", "abcdefg"])
cases.append(["x" * 40, "x" * 39 + "y", "x" * 39])
cases.append(["ab", "ab", "ba", "abb"])
cases.append(["z", "y", "x"])
for trial in range(6):
    n = random.randint(8, 30)
    cores = []
    base = "".join(random.choice(ALPHA) for _ in range(random.randint(4, 16)))
    for _ in range(n):
        s = list(base)
        for _ in range(random.randint(0, 3)):
            op = random.choice("sid")
            if op == "s" and s:
                s[random.randrange(len(s))] = random.choice(ALPHA)
            elif op == "i":
                s.insert(random.randrange(len(s) + 1), random.choice(ALPHA))
            elif op == "d" and len(s) > 1:
                del s[random.randrange(len(s))]
        cores.append("".join(s))
    cases.append(cores)

for i, cores in enumerate(cases):
    evaluate(cores, tag=f"case{i}")

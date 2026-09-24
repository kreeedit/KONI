"""Fair measurement: real gate vs SOUND L1 gate (cached counters, no cap),
merge counts + gate-phase cost (DP stubbed) + full wall time."""
import sys, inspect, textwrap, time, pickle
sys.path.insert(0, "/home/tamask/github/KONI")
from collections import Counter
from app import flame_pure as fp

SRC = inspect.getsource(fp.cluster_pairs)
GATE = """            hb = sh[ib]
            inter = len(ha & hb)
            if not inter:
                continue
            # 4-gram Jaccard as a cheap proxy for edit similarity
            if 2 * inter / (len(ha) + len(hb)) < threshold * 0.5:
                continue
"""
L1 = """            _ca = _ctr[ia]; _cb = _ctr[ib]
            _l1 = sum((_ca - _cb).values()) + sum((_cb - _ca).values())
            if 1.0 - _l1 / (2.0 * (la + lb)) < threshold:
                continue
"""
CNT = ("        if ra != rb:\n            uparent[max(ra, rb)] = min(ra, rb)",
       "        if ra != rb:\n            _CNT[0] += 1\n            uparent[max(ra, rb)] = min(ra, rb)")
assert CNT[0] in SRC and GATE in SRC
SRC_CNT = SRC.replace(*CNT)
SRC_L1 = SRC_CNT.replace(GATE, L1).replace(
    "    sh = [_shingles(s) for s in cores]",
    "    sh = [_shingles(s) for s in cores]\n    _ctr = [Counter(c) for c in cores]")


def mk(src, ratio):
    ns = {"levenshtein_ratio": ratio, "Counter": Counter, "_shingles": fp._shingles,
          "_CNT": [0]}
    exec(textwrap.dedent(src), ns)
    return ns


def stub(a, b):
    return 0.0


def probe(sigs, label):
    print(f"=== {label}: pairs={len(sigs)} cores={len(set(sigs))}", flush=True)
    # gate-phase cost only (DP stubbed out)
    for src, tag in ((SRC_CNT, "jaccard"), (SRC_L1, "L1sound")):
        ns = mk(src, stub)
        t = time.time(); ns["cluster_pairs"](sigs, max_lev=10**9); dt = time.time() - t
        print(f"   gate-only ({tag}): {dt:.1f}s", flush=True)
    # full, no cap
    for src, tag in ((SRC_CNT, "jaccard"), (SRC_L1, "L1sound")):
        ns = mk(src, fp.levenshtein_ratio)
        t = time.time(); r = ns["cluster_pairs"](sigs, max_lev=10**9); dt = time.time() - t
        print(f"   FULL ({tag}): merges={ns['_CNT'][0]} clusters={r['stats']['n_clusters']} "
              f"clustered_pairs={r['stats']['n_clustered']} lev={r['stats']['lev_compares']} "
              f"trunc={r['stats']['truncated']} t={dt:.1f}s", flush=True)


for label, path in [("3966-pair self-compare (default max_candidates=4000)", "sigs.pkl"),
                    ("8009-pair (all candidates)", "sigs_all.pkl")]:
    sigs = pickle.load(open("/home/tamask/github/KONI/.claude-isolated-config/jobs/88b99e67/tmp/" + path, "rb"))["sigs"]
    probe(sigs, label)

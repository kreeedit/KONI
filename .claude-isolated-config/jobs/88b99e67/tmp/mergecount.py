"""Count ACTUAL merges (uunion that changed a root) for real vs sound-gated
cluster_pairs, on the 3966-pair and 8009-pair sig sets."""
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
SRC_CNT = SRC.replace(
    "        if ra != rb:\n            uparent[max(ra, rb)] = min(ra, rb)",
    "        if ra != rb:\n            _CNT[0] += 1\n            uparent[max(ra, rb)] = min(ra, rb)")
assert SRC_CNT != SRC
SRC_L1 = SRC_CNT.replace(GATE, L1).replace(
    "    sh = [_shingles(s) for s in cores]",
    "    sh = [_shingles(s) for s in cores]\n    _ctr = [Counter(c) for c in cores]")


def mk(src):
    ns = {"levenshtein_ratio": fp.levenshtein_ratio, "Counter": Counter,
          "_shingles": fp._shingles, "_CNT": [0]}
    exec(textwrap.dedent(src), ns)
    return ns


for label, path in [("3966-pair (default max_candidates)", "sigs.pkl"),
                    ("8009-pair (all candidates)", "sigs_all.pkl")]:
    sigs = pickle.load(open("/home/tamask/github/KONI/.claude-isolated-config/jobs/88b99e67/tmp/" + path, "rb"))["sigs"]
    nsj = mk(SRC_CNT)
    t = time.time(); r = nsj["cluster_pairs"](sigs); tj = time.time() - t
    nsl = mk(SRC_L1)
    t = time.time(); r2 = nsl["cluster_pairs"](sigs, max_lev=200000); tl = time.time() - t
    print(f"--- {label}: pairs={len(sigs)} cores={r['stats']['n_cores']}")
    print(f"    REAL  merges={nsj['_CNT'][0]} clusters(sz>=2)={r['stats']['n_clusters']} "
          f"clustered_pairs={r['stats']['n_clustered']} lev={r['stats']['lev_compares']} "
          f"trunc={r['stats']['truncated']} t={tj:.1f}s")
    print(f"    SOUND merges={nsl['_CNT'][0]} clusters(sz>=2)={r2['stats']['n_clusters']} "
          f"clustered_pairs={r2['stats']['n_clustered']} lev={r2['stats']['lev_compares']} "
          f"trunc={r2['stats']['truncated']} t={tl:.1f}s")
    if not r2["stats"]["truncated"]:
        d = nsl['_CNT'][0] - nsj['_CNT'][0]
        print(f"    merge delta = {d} ({100.0*d/max(1,nsl['_CNT'][0]):.2f}%)  "
              f"wall speedup = {tl/max(tj,1e-9):.1f}x")
    sys.stdout.flush()

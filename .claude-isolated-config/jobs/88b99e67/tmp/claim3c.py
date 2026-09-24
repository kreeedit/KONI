"""Untruncated candidate set + fair sound reference (precomputed counters)."""
import sys, inspect, textwrap, time, pickle
sys.path.insert(0, "/home/tamask/github/KONI")
from collections import Counter
from app import texts, flame_pure as fp
sys.path.insert(0, "/home/tamask/github/KONI/.claude-isolated-config/jobs/88b99e67/tmp")
from pairs import collect

s1 = texts.section_texts("0003", "001")
t0 = time.time()
pairs, sigs, ncand, nranked, nchosen = collect(s1, s1, max_candidates=10**9)
print("ALL candidates: cand=%d ranked=%d chosen=%d pairs=%d (t=%.0fs)" % (
    ncand, nranked, nchosen, len(pairs), time.time() - t0), flush=True)
pickle.dump({"sigs": sigs}, open("/home/tamask/github/KONI/.claude-isolated-config/jobs/88b99e67/tmp/sigs_all.pkl", "wb"))
print("distinct cores:", len(set(sigs)), flush=True)

t = time.time(); r = fp.cluster_pairs(sigs); dt = time.time() - t
print("REAL  ", r["stats"], "t=%.1fs" % dt, flush=True)

SRC = inspect.getsource(fp.cluster_pairs)
OLD = """            hb = sh[ib]
            inter = len(ha & hb)
            if not inter:
                continue
            # 4-gram Jaccard as a cheap proxy for edit similarity
            if 2 * inter / (len(ha) + len(hb)) < threshold * 0.5:
                continue
"""
NEW = """            _l1 = _l1d[ia][ib]
            if 1.0 - _l1 / (2.0 * (la + lb)) < threshold:
                continue
"""
assert OLD in SRC
src2 = SRC.replace(OLD, NEW).replace(
    "    sh = [_shingles(s) for s in cores]",
    "    sh = [_shingles(s) for s in cores]\n"
    "    _ctr = [Counter(c) for c in cores]\n"
    "    _l1d = {}\n"
    "    for _i in range(U):\n"
    "        _a = _ctr[_i]\n"
    "        _l1d[_i] = {_j: sum((_a - _ctr[_j]).values()) + sum((_ctr[_j] - _a).values())\n"
    "                    for _j in range(U)}")
ns = {"levenshtein_ratio": fp.levenshtein_ratio, "Counter": Counter,
      "_shingles": fp._shingles}
exec(textwrap.dedent(src2), ns)
sound = ns["cluster_pairs"]
t = time.time(); r2 = sound(sigs, max_lev=10**7); dt2 = time.time() - t
print("SOUND ", r2["stats"], "t=%.1fs" % dt2, flush=True)
print("clustered real %d vs sound %d (lost %.2f%%)" % (
    r["stats"]["n_clustered"], r2["stats"]["n_clustered"],
    100.0 * (r2["stats"]["n_clustered"] - r["stats"]["n_clustered"]) /
    max(1, r2["stats"]["n_clustered"])), flush=True)
print("lev_compares real %d sound %d ; wall speedup %.1fx" % (
    r["stats"]["lev_compares"], r2["stats"]["lev_compares"], dt2 / dt), flush=True)

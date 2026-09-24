"""Compare the real cluster_pairs against a provably SOUND variant
(L1 multiset bound replacing both the shingle-intersection early-exit and the
Jaccard gate), on the real 3966-pair self-compare sigs."""
import sys, inspect, textwrap, time, pickle
sys.path.insert(0, "/home/tamask/github/KONI")
from collections import Counter
from app import flame_pure as fp

SRC = inspect.getsource(fp.cluster_pairs)
OLD = """            hb = sh[ib]
            inter = len(ha & hb)
            if not inter:
                continue
            # 4-gram Jaccard as a cheap proxy for edit similarity
            if 2 * inter / (len(ha) + len(hb)) < threshold * 0.5:
                continue
"""
NEW = """            _ca = Counter(cores[ia]); _cb = Counter(cores[ib])
            _l1 = sum((_ca - _cb).values()) + sum((_cb - _ca).values())
            if 1.0 - _l1 / (2.0 * (la + lb)) < threshold:
                continue
"""
assert OLD in SRC
NS = {"levenshtein_ratio": fp.levenshtein_ratio, "Counter": Counter,
      "_shingles": fp._shingles}
ns_sound = dict(NS)
exec(textwrap.dedent(SRC.replace(OLD, NEW)), ns_sound)
sound = ns_sound["cluster_pairs"]

sigs = pickle.load(open("/home/tamask/github/KONI/.claude-isolated-config/jobs/88b99e67/tmp/sigs.pkl", "rb"))["sigs"]
print("pairs", len(sigs), "cores", len(set(sigs)), flush=True)

t = time.time(); r1 = fp.cluster_pairs(sigs); t1 = time.time() - t
print("REAL   ", r1["stats"], " t=%.2fs" % t1, flush=True)
t = time.time(); r2 = sound(sigs); t2 = time.time() - t
print("SOUND  ", r2["stats"], " t=%.2fs" % t2, flush=True)
print("clustered: real %d vs sound %d  (lost %d, %.2f%%)" % (
    r1["stats"]["n_clustered"], r2["stats"]["n_clustered"],
    r2["stats"]["n_clustered"] - r1["stats"]["n_clustered"],
    100.0 * (r2["stats"]["n_clustered"] - r1["stats"]["n_clustered"]) /
    max(1, r2["stats"]["n_clustered"])), flush=True)
print("lev_compares: real %d vs sound %d  -> speedup %.1fx" % (
    r1["stats"]["lev_compares"], r2["stats"]["lev_compares"],
    r2["stats"]["lev_compares"] / max(1, r1["stats"]["lev_compares"])), flush=True)
print("wall speedup (sound/real) = %.2fx" % (t2 / t1), flush=True)

# --- adversarial SUBSET: pairs whose core is shorter than 6 chars
shorts = [s for s in sigs if len(s) <= 5]
print("sigs with len<=5:", len(shorts), "of", len(sigs), flush=True)
if shorts:
    from collections import Counter as C
    print(C(shorts).most_common(5), flush=True)

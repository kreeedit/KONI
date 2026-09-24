import sys, time, pickle, inspect, textwrap
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
assert GATE in SRC, "gate snippet not found"

ns = {"levenshtein_ratio": fp.levenshtein_ratio, "Counter": Counter, "_shingles": fp._shingles}
exec(textwrap.dedent(SRC.replace(GATE, L1GATE)), ns)
cluster_pairs_L1 = ns["cluster_pairs"]

data = pickle.load(open("/home/tamask/github/KONI/.claude-isolated-config/jobs/88b99e67/tmp/sigs.pkl", "rb"))
sigs = data["sigs"]
print("pairs:", len(sigs), "distinct cores:", len(set(sigs)))

# instrumented union counter for the real function
ns2 = {}
exec(textwrap.dedent(SRC), ns2)
counts = {"merges": 0}


def run(fn, label):
    t0 = time.time()
    r = fn(sigs)
    dt = time.time() - t0
    print(f"{label}: t={dt:.2f}s stats={r['stats']}")
    # count merges by reconstructing: number of pairs in clusters of size>=2
    return r, dt


r_j, t_j = run(fp.cluster_pairs, "jaccard(real)")
r_l, t_l = run(cluster_pairs_L1, "L1-sound   ")
print("merged-pairs (clustered):", r_j["stats"]["n_clustered"], "vs", r_l["stats"]["n_clustered"])
print("n_clusters:", r_j["stats"]["n_clusters"], "vs", r_l["stats"]["n_clusters"])
print("lev_compares:", r_j["stats"]["lev_compares"], "vs", r_l["stats"]["lev_compares"])
print("speedup (L1/jaccard) = %.2fx" % (t_l / t_j))

# exact "unions performed" count via instrumented copy
SRC_I = SRC.replace("        if ra != rb:\n            uparent[max(ra, rb)] = min(ra, rb)",
                    "        if ra != rb:\n            _CNT[0] += 1\n            uparent[max(ra, rb)] = min(ra, rb)")
assert SRC_I != SRC
def counted(src):
    nsc = {"levenshtein_ratio": fp.levenshtein_ratio, "Counter": Counter, "_shingles": fp._shingles, "_CNT": [0]}
    exec(textwrap.dedent(src), nsc)
    return nsc

nsj = counted(SRC_I)
nsj["cluster_pairs"](sigs)
print("real unions:", nsj["_CNT"][0])
nsl = counted(SRC_I.replace(GATE, L1GATE))
nsl["cluster_pairs"](sigs)
print("L1 unions:", nsl["_CNT"][0])

import os, sys, pickle
sys.path.insert(0, os.getcwd())
from app import flame_pure as F, texts

CAP = int(sys.argv[1]) if len(sys.argv) > 1 else 100000
CACHE = os.path.join(os.environ["CLAUDE_JOB_DIR"], "tmp", "sigs_full.pkl")

if os.path.exists(CACHE):
    sigs = pickle.load(open(CACHE, "rb"))
    print("loaded cached sigs:", len(sigs), flush=True)
else:
    captured = {}
    real = F.cluster_pairs
    def shim(sigs, **kw):
        captured["s"] = list(sigs)
        return real(sigs, **kw)
    F.cluster_pairs = shim
    s1 = texts.section_texts("0003", "001")
    s2 = texts.section_texts("0003", "001")
    npairs = 0
    for ev in F.compare_iter(s1, s2, max_candidates=CAP, progress_every=10**9):
        if ev["t"] == "pair":
            npairs += 1
    sigs = captured["s"]
    print(f"max_candidates={CAP} -> pairs={npairs} sigs={len(sigs)}", flush=True)
    pickle.dump(sigs, open(CACHE, "wb"))
print("distinct cores:", len(set(sigs)), flush=True)

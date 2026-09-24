import sys, inspect, textwrap, time, pickle
sys.path.insert(0, "/home/tamask/github/KONI")
from collections import Counter
from app import flame_pure as fp
SRC = inspect.getsource(fp.cluster_pairs)
SRC_CNT = SRC.replace("        if ra != rb:\n            uparent[max(ra, rb)] = min(ra, rb)",
                      "        if ra != rb:\n            _CNT[0] += 1\n            uparent[max(ra, rb)] = min(ra, rb)")
ns = {"levenshtein_ratio": fp.levenshtein_ratio, "Counter": Counter,
      "_shingles": fp._shingles, "_CNT": [0]}
exec(textwrap.dedent(SRC_CNT), ns)
for label, path in [("3966", "sigs.pkl"), ("8009", "sigs_all.pkl")]:
    sigs = pickle.load(open("/home/tamask/github/KONI/.claude-isolated-config/jobs/88b99e67/tmp/"+path,"rb"))["sigs"]
    t=time.time(); r = ns["cluster_pairs"](sigs); dt=time.time()-t
    print(label, "merges_this_run_counted_below", flush=True)
    print("   ", r["stats"], "t=%.1f"%dt, flush=True)
# merges are cumulative in ns; re-run separately
for label, path in [("3966", "sigs.pkl"), ("8009", "sigs_all.pkl")]:
    n2 = {"levenshtein_ratio": fp.levenshtein_ratio, "Counter": Counter,
          "_shingles": fp._shingles, "_CNT": [0]}
    exec(textwrap.dedent(SRC_CNT), n2)
    sigs = pickle.load(open("/home/tamask/github/KONI/.claude-isolated-config/jobs/88b99e67/tmp/"+path,"rb"))["sigs"]
    r = n2["cluster_pairs"](sigs)
    print(f"{label}: MERGES={n2['_CNT'][0]} lev={r['stats']['lev_compares']} clusters={r['stats']['n_clusters']} clustered_pairs={r['stats']['n_clustered']}", flush=True)

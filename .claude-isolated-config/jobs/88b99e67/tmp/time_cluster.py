import os, sys, json, time
sys.path.insert(0, os.getcwd())
sys.path.insert(0, "scripts")
from app import flame_pure as F

sigs = json.load(open(os.path.join(os.environ["CLAUDE_JOB_DIR"], "tmp", "sigs.json")))["self"]
for thr in (0.85, 0.95, 1.0):
    t0 = time.time()
    r = F.cluster_pairs(sigs, threshold=thr)
    print("thr=%.2f  %.2fs  %s" % (thr, time.time() - t0, r["stats"]), flush=True)
r = F.cluster_pairs(sigs, threshold=0.85)
for c in r["clusters"][:3]:
    print("  cluster id=%d size=%d members[:6]=%s" % (c["id"], c["size"], c["members"][:6]))

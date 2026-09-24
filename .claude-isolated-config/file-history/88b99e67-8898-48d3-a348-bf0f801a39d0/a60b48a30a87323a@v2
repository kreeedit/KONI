import os, sys, json, time, collections
sys.path.insert(0, os.getcwd())
sys.path.insert(0, "scripts")
from app import flame_pure as F

SIGS = json.load(open(os.path.join(os.environ["CLAUDE_JOB_DIR"], "tmp", "sigs.json")))
sigs = SIGS["self"]
n = len(sigs)
thr = 0.85
uids = {}
uid_of = []
for s in sigs:
    if s not in uids:
        uids[s] = len(uids)
    uid_of.append(uids[s])
uniq = list(uids)
U = len(uniq)
print("pairs=%d distinct_cores=%d (%.1f%% collapse)" % (n, U, 100 * (1 - U / n)), flush=True)

sh = [F._shingles(s) for s in uniq]
by_len = sorted(range(U), key=lambda i: len(uniq[i]))

t0 = time.time()
window = lev = unions = 0
for a in range(U):
    ia = by_len[a]
    la = len(uniq[ia])
    ha = sh[ia]
    if la < 2:
        continue
    for b in range(a + 1, U):
        ib = by_len[b]
        lb = len(uniq[ib])
        if (lb - la) / (la + lb) > 1.0 - thr:
            break
        window += 1
        hb = sh[ib]
        inter = len(ha & hb)
        if 2 * inter / (len(ha) + len(hb)) < thr * 0.5:
            continue
        lev += 1
        if F.levenshtein_ratio(uniq[ia], uniq[ib]) >= thr:
            unions += 1
print("distinct-based: window=%d lev=%d unions=%d  %.2fs" % (window, lev, unions, time.time() - t0), flush=True)

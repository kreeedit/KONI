import os, sys, json, time, collections
sys.path.insert(0, os.getcwd())
sys.path.insert(0, "scripts")
from app import flame_pure as F

SIGS = json.load(open(os.path.join(os.environ["CLAUDE_JOB_DIR"], "tmp", "sigs.json")))
sigs = SIGS["self"]
n = len(sigs)
thr = 0.85
print("pairs:", n, flush=True)

by_len = sorted(range(n), key=lambda i: len(sigs[i]))
sh = [F._shingles(sigs[i]) for i in range(n)]
cnt = [collections.Counter(sigs[i]) for i in range(n)]

def l1(a, b):
    ca, cb = cnt[a], cnt[b]
    if len(ca) < len(cb):
        ca, cb = cb, ca
    return sum(abs(v - cb.get(k, 0)) for k, v in ca.items())

def run(mode, cap=100000):
    t0 = time.time()
    window = lev = unions = 0
    truncated = False
    for a in range(n):
        ia = by_len[a]
        la = len(sigs[ia])
        if la < 2:
            continue
        for b in range(a + 1, n):
            ib = by_len[b]
            lb = len(sigs[ib])
            if (lb - la) / (la + lb) > 1.0 - thr:
                break
            window += 1
            if sigs[ia] == sigs[ib]:
                continue
            if mode == "shingle":
                ha, hb = sh[ia], sh[ib]
                inter = len(ha & hb)
                if 2 * inter / (len(ha) + len(hb)) < thr * 0.5:
                    continue
            elif mode == "multiset":
                d_min = max(lb - la, l1(ia, ib) / 2.0)
                if 1.0 - d_min / (la + lb) < thr:
                    continue
            if lev >= cap:
                truncated = True
                break
            lev += 1
            if F.levenshtein_ratio(sigs[ia], sigs[ib]) >= thr:
                unions += 1
        if truncated:
            break
    print("%-9s window=%6d lev=%6d unions=%5d trunc=%s  %.2fs"
          % (mode, window, lev, unions, truncated, time.time() - t0), flush=True)

for m in ("shingle", "multiset"):
    run(m)

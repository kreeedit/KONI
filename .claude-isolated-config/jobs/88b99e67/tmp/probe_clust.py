import sys, time, collections
import os; sys.path.insert(0, os.getcwd())
sys.path.insert(0, "scripts")
from app import flame_pure as F, texts

s1 = texts.section_texts("0003", "001")
sigs = []
for ev in F.compare_iter(s1, s1, progress_every=10**9):
    if ev["t"] == "pair":
        sigs.append(ev["pair"]["core_text"])
print("pairs:", len(sigs))

n = len(sigs)
thr = 0.85
by_len = sorted(range(n), key=lambda i: len(sigs[i]))
sh = [F._shingles(sigs[i]) for i in range(n)]
cnt = [collections.Counter(sigs[i]) for i in range(n)]

def l1(a, b):
    ca, cb = cnt[a], cnt[b]
    if len(ca) < len(cb): ca, cb = cb, ca
    return sum(abs(v - cb.get(k, 0)) for k, v in ca.items())

def run(mode):
    t0 = time.time()
    survivors = 0; window = 0; lev = 0; unioned = 0
    for a in range(n):
        ia = by_len[a]; la = len(sigs[ia])
        if la < 2: continue
        for b in range(a + 1, n):
            ib = by_len[b]; lb = len(sigs[ib])
            if (lb - la) / (la + lb) > 1.0 - thr: break
            window += 1
            if sigs[ia] == sigs[ib]: continue
            if mode == "shingle":
                ha, hb = sh[ia], sh[ib]
                inter = len(ha & hb)
                if 2 * inter / (len(ha) + len(hb)) < thr * 0.5: continue
            elif mode == "multiset":
                d_min = max(lb - la, l1(ia, ib) / 2.0)
                if 1.0 - d_min / (la + lb) < thr: continue
            survivors += 1
            lev += 1
            if F.levenshtein_ratio(sigs[ia], sigs[ib]) >= thr: unioned += 1
    return window, survivors, lev, unioned, time.time() - t0

for m in ("none", "shingle", "multiset"):
    w, s, l, u, dt = run(m)
    print("%-9s window=%6d lev_calls=%6d unions=%5d  %.2fs" % (m, w, l, u, dt))

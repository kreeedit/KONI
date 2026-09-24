import os, sys, time, pickle
from collections import Counter
sys.path.insert(0, os.getcwd())
from app import flame_pure as F

sigs = pickle.load(open(os.path.join(os.environ["CLAUDE_JOB_DIR"], "tmp", "sigs_full.pkl"), "rb"))

def run(mode, threshold=0.85, min_size=2, max_lev=10**9):
    n = len(sigs)
    uid_of_core, uid = {}, [0]*n
    for p, s in enumerate(sigs):
        i = uid_of_core.get(s)
        if i is None:
            i = uid_of_core[s] = len(uid_of_core)
        uid[p] = i
    cores = [None]*len(uid_of_core)
    for s, i in uid_of_core.items():
        cores[i] = s
    U = len(cores)
    uparent = list(range(U))
    merges = [0]
    def ufind(x):
        while uparent[x] != x:
            uparent[x] = uparent[uparent[x]]; x = uparent[x]
        return x
    def uunion(a, b):
        ra, rb = ufind(a), ufind(b)
        if ra != rb:
            uparent[max(ra, rb)] = min(ra, rb); merges[0] += 1
    by_len = sorted(range(U), key=lambda i: len(cores[i]))
    sh = [F._shingles(s) for s in cores]
    l1 = [Counter(s) for s in cores] if mode == "l1" else None
    lev = 0; skips = 0
    t0 = time.time()
    for a in range(U):
        ia = by_len[a]; la = len(cores[ia])
        if la < 2: continue
        ha = sh[ia]; ca = l1[ia] if l1 else None
        for b in range(a+1, U):
            ib = by_len[b]; lb = len(cores[ib])
            if (lb-la)/(la+lb) > 1.0-threshold: break
            if ufind(ia) == ufind(ib): continue
            if mode == "jaccard":
                hb = sh[ib]; inter = len(ha & hb)
                if not inter or 2*inter/(len(ha)+len(hb)) < threshold*0.5:
                    skips += 1; continue
            else:
                cb = l1[ib]
                L1 = sum(abs(ca.get(c,0)-cb.get(c,0)) for c in set(ca)|set(cb))
                if L1 > 2*(1.0-threshold)*(la+lb):
                    skips += 1; continue
            lev += 1
            if F.levenshtein_ratio(cores[ia], cores[ib]) >= threshold:
                uunion(ia, ib)
    groups = {}
    for p in range(n):
        groups.setdefault(ufind(uid[p]), []).append(p)
    cl = [m for m in groups.values() if len(m) >= min_size]
    return dict(mode=mode, pairs=n, cores=U, merges=merges[0], clusters=len(cl),
                clustered=sum(len(m) for m in cl), lev=lev, skips=skips,
                secs=round(time.time()-t0, 1))

for m in ("jaccard", "l1"):
    print(run(m), flush=True)

import os, sys, json, time, collections
sys.path.insert(0, os.getcwd())
sys.path.insert(0, "scripts")
from app import flame_pure as F

SIGS = json.load(open(os.path.join(os.environ["CLAUDE_JOB_DIR"], "tmp", "sigs.json")))


def analyse(sigs, tag):
    n = len(sigs)
    thr = 0.85
    uids = {}
    uid_of = []
    for s in sigs:
        uids.setdefault(s, len(uids))
        uid_of.append(uids[s])
    counts = collections.Counter(uid_of)
    print("%s: pairs=%d distinct=%d  max_multiplicity=%d  top=%s"
          % (tag, n, len(uids), max(counts.values()),
             counts.most_common(5)), flush=True)

    by_len = sorted(range(n), key=lambda i: len(sigs[i]))
    sh = [F._shingles(sigs[i]) for i in range(n)]
    window = lev = 0
    seen_uid_pairs = set()
    repeat = 0
    for a in range(n):
        ia = by_len[a]
        la = len(sigs[ia])
        if la < 2:
            continue
        ha = sh[ia]
        for b in range(a + 1, n):
            ib = by_len[b]
            lb = len(sigs[ib])
            if (lb - la) / (la + lb) > 1.0 - thr:
                break
            window += 1
            if sigs[ia] == sigs[ib]:
                continue
            hb = sh[ib]
            inter = len(ha & hb)
            if 2 * inter / (len(ha) + len(hb)) < thr * 0.5:
                continue
            lev += 1
            key = (uid_of[ia], uid_of[ib])
            if key in seen_uid_pairs:
                repeat += 1
            else:
                seen_uid_pairs.add(key)
    print("   window=%d lev=%d distinct_uid_pairs=%d repeats=%d"
          % (window, lev, len(seen_uid_pairs), repeat), flush=True)


analyse(SIGS["self"], "self-3966")

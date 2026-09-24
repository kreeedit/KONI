import sys, itertools
sys.path.insert(0, "/home/tamask/github/KONI")
from app import flame_pure as fp

print("== A. 4-char core, true edge dropped by the shingle prefilters")
for pair in [("abcd", "abce"), ("abcd", "abcd"), ("abcd", "xabcd"), ("abcd", "abcde")]:
    a, b = pair
    r = fp.levenshtein_ratio(a, b)
    res = fp.cluster_pairs(list(pair), threshold=0.85, min_size=2)
    ha, hb = fp._shingles(a), fp._shingles(b)
    inter = len(ha & hb)
    jac = 2 * inter / (len(ha) + len(hb))
    print(f"  {pair}: ratio={r:.3f} inter={inter} jaccard={jac:.3f} "
          f"clusters={[(c['size'], c['members']) for c in res['clusters']]}")

print("== B. randomized search: ratio>=0.85 but prefilters reject (len 4..20, abc)")
import random
from collections import Counter
random.seed(3)
strings = {}
for L in range(4, 21):
    for _ in range(200):
        strings["".join(random.choice("abc") for _ in range(L))] = None
strings = sorted(strings)
ctr = {s0: Counter(s0) for s0 in strings}
hits = []
for ii, a in enumerate(strings):
    la = len(a)
    ca = ctr[a]
    for b in strings[ii + 1:]:
        if b == a:
            continue
        lb = len(b)
        if abs(lb - la) / (la + lb) > 0.15:
            continue
        cb = ctr[b]
        l1 = sum((ca - cb).values()) + sum((cb - ca).values())
        if 1.0 - l1 / (2.0 * (la + lb)) < 0.85:
            continue
        if fp.levenshtein_ratio(a, b) < 0.85:
            continue
        ha, hb = fp._shingles(a), fp._shingles(b)
        inter = len(ha & hb)
        jac = 2 * inter / (len(ha) + len(hb)) if inter else 0.0
        if inter == 0 or jac < 0.85 * 0.5:
            hits.append((a, b, round(fp.levenshtein_ratio(a, b), 3), inter, round(jac, 3)))
print("  true edges dropped by the shingle prefilters:", len(hits))
from collections import Counter as C
print("  (len_a,len_b) histogram:", C((len(h[0]), len(h[1])) for h in hits).most_common(8))
print("  e.g.", hits[:8])

print("== C. repetitive Greek-like strings (realistic core shapes)")
for pair in [("ετελευτα" * 1 + "α", "ετελευτα" + "β"),
             ("και ο χειμων ετελευτα και", "και ο χειμων ετελευτα κει"),
             ("αααααααα", "αααααααβ")]:
    a, b = pair
    r = fp.levenshtein_ratio(a, b)
    ha, hb = fp._shingles(a), fp._shingles(b)
    inter = len(ha & hb)
    jac = 2 * inter / (len(ha) + len(hb))
    res = fp.cluster_pairs([a, b], threshold=0.85, min_size=2)
    print(f"  ratio={r:.3f} inter={inter} jac={jac:.3f} merged={bool(res['clusters'])}  {a[:12]}../{b[:12]}..")

print("== D. edge cases / crash probes")
for sigs in ([], [""], ["", ""], ["a"], ["a", "a"], ["ab", "ab"], ["ab", "ba"]):
    try:
        r = fp.cluster_pairs(sigs)
        print(f"  sigs={sigs!r} -> clusters={[(c['size'], c['members']) for c in r['clusters']]} stats={r['stats']}")
    except Exception as e:
        print(f"  sigs={sigs!r} -> EXCEPTION {type(e).__name__}: {e}")

print("== E. min_size behaviour")
r = fp.cluster_pairs(["ab", "ab", "cd"], min_size=1)
print("  min_size=1:", [(c['size'], c['members']) for c in r['clusters']], r['stats'])
r = fp.cluster_pairs(["ab", "ab", "cd"], min_size=3)
print("  min_size=3:", r['clusters'], r['stats'])

print("== F. max_lev truncation flag")
sigs = ["word%d" % i for i in range(200)]
r = fp.cluster_pairs(sigs, threshold=0.5, max_lev=0)
print("  max_lev=0:", r['stats'])

print("== G. _core_sequence run detection")
blocks = [{"matches": [(5, 1), (6, 2), (9, 3), (10, 4), (11, 5)], "n": 5, "core": 3}]
print("  ", fp._core_sequence(blocks, ["a", "b", "c", "d", "e", "w5", "w6", "x", "y", "w9", "w10", "w11"]))
blocks = [{"matches": [(3, 0), (4, 1)], "n": 2, "core": 2},
          {"matches": [(7, 5), (8, 6), (9, 7)], "n": 3, "core": 3}]
print("  ", fp._core_sequence(blocks, list("0123abcd789")))
print("  empty:", fp._core_sequence([], ["a"]), fp._core_sequence([{"matches": []}], ["a"]))

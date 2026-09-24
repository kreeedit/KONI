"""Verify claim 1 on real data: cluster member indices survive both paths."""
import sys
sys.path.insert(0, "/home/tamask/github/KONI")
from app import texts, flame_pure as fp

for a1, w1, tag in [("0003", "001", "thuc self")]:
    s1 = texts.section_texts(a1, w1)
    if s1 is None:
        print(tag, "no text"); continue
    kw = dict(similarity_threshold=0.0)
    yield_pairs = []
    cl = {}
    for ev in fp.compare_iter(s1, s1, progress_every=10**9, **kw):
        if ev["t"] == "pair":
            yield_pairs.append((ev["pair"]["i"], ev["pair"]["j"], ev["pair"]["chain_len"]))
        elif ev["t"] == "clusters":
            cl = ev
    res = fp.compare(s1, s1, **kw)
    print(f"--- {tag}: streamed {len(yield_pairs)} pairs, compare() {len(res['pairs'])} pairs")
    # streaming: members must index yield order
    bad_stream = 0
    for c in cl["clusters"]:
        for m in c["members"]:
            if not (0 <= m < len(yield_pairs)):
                bad_stream += 1
    # non-streaming: members must index display order
    disp = [(p["i"], p["j"], p["chain_len"]) for p in res["pairs"]]
    bad_ns = 0
    for c in res["clusters"]:
        for m in c["members"]:
            if not (0 <= m < len(disp)):
                bad_ns += 1
    print("  stream OOR members:", bad_stream, " nonstream OOR members:", bad_ns)
    # expected display order (stable, chain_len desc)
    exp = [yield_pairs[k] for k in
           sorted(range(len(yield_pairs)), key=lambda k: yield_pairs[k][2], reverse=True)]
    print("  display order matches stable sort:", exp == disp)
    # cross-check every non-streaming cluster against the streaming one by content
    smap = {}
    for c in cl["clusters"]:
        key = frozenset(yield_pairs[m][:2] for m in c["members"])
        smap[key] = c["size"]
    mismatch = 0
    for c in res["clusters"]:
        key = frozenset(disp[m][:2] for m in c["members"])
        if smap.get(key) != c["size"]:
            mismatch += 1
    print("  cluster content mismatches (streaming vs compare):", mismatch,
          "/", len(res["clusters"]))
    # chain_len distribution / tie density
    from collections import Counter
    cnt = Counter(p[2] for p in yield_pairs)
    print("  chain_len ties:", [(k, v) for k, v in cnt.most_common(4)])

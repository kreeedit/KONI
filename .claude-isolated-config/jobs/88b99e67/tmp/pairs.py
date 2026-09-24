"""Reproduce compare_iter's pairing loop but capture the raw sigs."""
import sys, time
sys.path.insert(0, "/home/tamask/github/KONI")
from collections import Counter
from app import texts, flame_pure as fp


def collect(s1, s2, ngram=4, n_out=1, min_chain_words=2, fuzz_threshold=0.75,
            similarity_threshold=None, min_shared=3, max_candidates=4000):
    u1 = fp._units(s1)
    u2 = fp._units(s2)
    vocab = {}
    for _, _, _, subs, _ in u1 + u2:
        for s in subs:
            if s not in vocab:
                vocab[s] = len(vocab)
    base = len(vocab) + 1
    counters1 = [Counter(fp._hashes([vocab[s] for s in subs], base, ngram, n_out))
                 for _, _, _, subs, _ in u1]
    counters2 = [Counter(fp._hashes([vocab[s] for s in subs], base, ngram, n_out))
                 for _, _, _, subs, _ in u2]
    idf = fp._idf(counters1 + counters2)
    wn = 2
    grams2 = [fp._word_ngrams(u[2], wn) for u in u2]
    inv = {}
    for j, gs in enumerate(grams2):
        for g in set(gs):
            inv.setdefault(g, []).append(j)
    df_cap = max(40, int(0.04 * len(u2)))
    cand = {}
    for i in range(len(u1)):
        local = {}
        for g in set(fp._word_ngrams(u1[i][2], wn)):
            posting = inv.get(g)
            if not posting or len(posting) > df_cap:
                continue
            for j in posting:
                local[j] = local.get(j, 0) + 1
        for j, shared in local.items():
            if shared >= min_shared:
                cand[(i, j)] = shared
    ranked = sorted(cand.items(), key=lambda kv: kv[1], reverse=True)[:max_candidates]
    vc1, vc2, scored = {}, {}, []
    for (i, j), _s in ranked:
        v1 = vc1.get(i)
        if v1 is None:
            v1 = vc1[i] = fp._tfidf(counters1[i], idf)
        v2 = vc2.get(j)
        if v2 is None:
            v2 = vc2[j] = fp._tfidf(counters2[j], idf)
        scored.append((fp.cosine(v1, v2), i, j))
    sel = 0.0 if similarity_threshold is None else float(similarity_threshold)
    chosen = [(s, i, j) for (s, i, j) in scored if s >= sel]
    pairs, sigs = [], []
    for score, i, j in chosen:
        label_i, orig_i, norm_i, _, _ = u1[i]
        label_j, orig_j, norm_j, _, _ = u2[j]
        raw = fp._fuzzy_blocks(norm_i, norm_j, fuzz_threshold, n_out)
        kept = [b for b in raw if b["core"] >= ngram and b["n"] >= min_chain_words]
        if kept:
            sigs.append(" ".join(fp._core_sequence(kept, norm_i)))
            pairs.append({"i": i, "j": j, "chain_len": max(b["n"] for b in kept)})
    return pairs, sigs, len(cand), len(ranked), len(chosen)


if __name__ == "__main__":
    s1 = texts.section_texts("0003", "001")
    t0 = time.time()
    pairs, sigs, ncand, nranked, nchosen = collect(s1, s1)
    print("n_candidates(pairs w/ shared>=3):", ncand, "ranked:", nranked,
          "chosen:", nchosen, "pairs:", len(pairs), "sigs:", len(sigs))
    print("t=%.1fs" % (time.time() - t0))
    import pickle
    with open("/home/tamask/github/KONI/.claude-isolated-config/jobs/88b99e67/tmp/sigs.pkl", "wb") as f:
        pickle.dump({"sigs": sigs, "chain_len": [p["chain_len"] for p in pairs]}, f)
    print("distinct cores:", len(set(sigs)))
    from collections import Counter as C
    c = C(sigs)
    print("non-empty sigs:", sum(1 for s in sigs if s))
    print("top cores:", c.most_common(3)[:3])

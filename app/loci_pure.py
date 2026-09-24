"""Loci: keyword-in-context, parallel-locus search and n-gram phraseology.

The third and last independent part of the archaism rework (point 5 of the
methodological critique). Everything here exists because a row in a frequency
table is a CLAIM, and a claim needs its evidence reachable in one action:

  * `kwic`          — the actual occurrences, with +-`span` words of context.
                      "WHERE IN B: 8.2.10" says a word is there; it does not
                      say what the author did with it, which is the only thing
                      a philologist can evaluate. Also the reason a count must
                      be checkable: a row that displays 12 loci and claims 3
                      occurrences is a bug the reader can now see.
  * `parallel_loci` — Thucydides' most similar sentences to one Procopian
                      locus, ranked by TF-IDF cosine over the SAME engine
                      (`flame_pure._idf` / `_tfidf` / `cosine`) that drives the
                      reuse search. A single shared word proves nothing; the
                      shared n-grams are reported alongside the score so the
                      reader can see whether the similarity is phraseology or
                      just two sentences about the same war.
  * `ngram_table` / `ngram_contrast` — 2- and 3-gram phraseology around a word,
                      in both works, ranked by the same Haldane-corrected log2
                      ratio as the lexical report. This is what separates an
                      allusion (a phrase B took over) from a coincidence (a word
                      B happens to use).

WHAT IS DELIBERATELY NOT HERE
-----------------------------
  * No stemming, no lemmatisation. A Latin-script lemmatiser needs the Morpheus
    `greek.ml` data file, which is the agreed-but-unstarted point 1. Until then
    the n-gram tables pool the same morphophonetic variants as the frequency
    report (`variants.unify`), which is a partial and EXPLICIT substitute: it
    merges γιγν-/γιν- and ξυ-/συ-, and it does not touch inflection.
  * No sentence segmentation beyond punctuation. Splitting on `.;·!?` is what
    these editions' orthography supports; a text with unpunctuated runs of
    direct speech will produce long "sentences". `sentences()` reports the
    length distribution so a caller can see when that happens rather than
    trusting the split silently.
  * No cross-lingual or fuzzy parallel search here. `flame_pure.compare_iter`
    already does Levenshtein-tolerant block matching and is the right tool for
    finding reuse over a whole work; `parallel_loci` is deliberately the cheap,
    explainable, single-anchor version, and reports its raw evidence.
"""
from __future__ import annotations

import math
import re
from collections import Counter

from .flame_pure import _idf, _tfidf, cosine, normalize, words_elided
from .variants import DEFAULT as VARIANTS_DEFAULT
from .variants import marked_rules
from .variants import unify as variants_unify

# The editions' sentence-final marks. `;` is the Greek question mark and `·` the
# ano teleia, so both end a sentence here. Splitting AFTER the mark keeps it in
# the preceding sentence, which is where a reader expects it.
_SENT_SPLIT = re.compile(r"(?<=[.;·!?])\s+")
# Milestones like (1) are apparatus, not text: they must not become "words" in a
# similarity bag, where every sentence would then share the token `1`.
_MILESTONE_RE = re.compile(r"[\(\[]\s*\d+\s*[\)\]]")
_DIGITS_RE = re.compile(r"^\d+$")


def _tokens(section: dict, drop_elided: bool = True) -> list[str]:
    """Original tokens of a section, elision fragments optionally dropped."""
    out = []
    for w, elided in words_elided(section.get("text", "")):
        if elided and drop_elided:
            continue
        out.append(w)
    return out


def _bag(forms: list[str]) -> Counter:
    """Normalised, variant-pooled bag of words for similarity work.

    Digits are dropped: after `_MILESTONE_RE` most are gone, but a stray year or
    book number is a token no two sentences should be similar over. Pooling is
    applied so `ξυμμαχία` and `συμμαχία` are one dimension, matching the
    frequency report — otherwise a ξυ-heavy sentence could not match a συ-heavy
    one and the parallel search would systematically miss the very imitation
    this whole view is looking for.
    """
    c: Counter = Counter()
    for w in forms:
        n = normalize(w)
        if not n or _DIGITS_RE.match(n):
            continue
        c[variants_unify(n, VARIANTS_DEFAULT)] += 1
    return c


def kwic(sections: list[dict], keys: set[str], variants: tuple[str, ...] = VARIANTS_DEFAULT,
         span: int = 8, limit: int = 200, per_key: int = 40, rule: str | None = None,
         drop_elided: bool = True) -> dict:
    """Keyword-in-context for each wanted POOLED key, or for one spelling RULE.

    `keys` are the normalised, already-pooled forms (`archaism_pure` keys). A
    token matches when its own pooled form equals the key, so a row whose count
    is the sum of `ξυμμαχία` and `συμμαχία` shows BOTH — which is the point of
    having pooled them.

    `rule`, when given, replaces the key test with the rule's own: every token
    the rule considers to wear the MARKED spelling is a hit. This is what the
    style report needs, because its rows are not words. `ξυ` is not a word and a
    key lookup for it finds `σύ` ("you") and nothing else; what the row is about
    is "every word written with ξυ-", which only the rule can answer.

    Two details that look like choices but are not:
      * `rule` is tested against the UNPOOLED normalised form. Pooling destroys
        the mark it is looking for — `ξυμμαχία` pools to `συμμαχια`, which no
        longer starts with ξυ — so testing the pooled form would find nothing.
      * `rule` is matched on `(rule,)` alone, NOT on `variants`. The style
        table's rules are its rows; a rule whose token list is suppressed
        because the reader unticked its pooling checkbox would be a dead row.

    `span` is in words, not characters: a character window cuts Greek words in
    half and makes two loci of different lengths incomparable. `limit` bounds
    the total, `per_key` the number any one word may contribute — a word like
    καί would otherwise fill the response on its own.

    Returns {"hits": {key: [hit, ...]}, "n_hits": {key: int},
             "truncated": {key: bool}, "span": int} where a hit is
    {"label", "index", "before": [str], "hit": str, "after": [str],
     "marked": [rule, ...], "pooled": str}. When `rule` is given, the single key
    is `rule` itself, so the caller indexes the result the same way either way.
    """
    want: set[str] = {rule} if rule else set(keys)
    hits: dict[str, list[dict]] = {k: [] for k in want}
    counts: Counter = Counter()
    if not want:
        return {"hits": hits, "n_hits": {}, "truncated": {}, "span": span}
    total = 0
    for s in sections:
        lab = s.get("label", "")
        toks = _tokens(s, drop_elided)
        for i, tok in enumerate(toks):
            n = normalize(tok)
            marked = marked_rules(n, (rule,) if rule else variants)
            # A per-word hit is matched on the POOLED form (so both spellings of
            # the row show); a per-rule hit is matched on the mark itself.
            key = rule if rule else variants_unify(n, variants)
            if rule is None:
                if key not in hits:
                    continue
            elif rule not in marked:
                continue
            counts[key] += 1
            if len(hits[key]) >= per_key or total >= limit:
                continue
            lo = max(0, i - span)
            hi = min(len(toks), i + span + 1)
            hits[key].append({
                "label": lab,
                "index": i,
                "before": toks[lo:i],
                "hit": toks[i],
                "after": toks[i + 1:hi],
                "marked": marked,
                "pooled": key if rule else variants_unify(n, variants),
            })
            total += 1
    return {"hits": hits,
            "n_hits": dict(counts),
            # Disclosed: a word whose display stops at `per_key` must say so, or
            # the reader will count the loci and conclude the rest are absent.
            "truncated": {k: counts[k] > len(v) for k, v in hits.items()},
            "span": span, "rule": rule}


def sentences(sections: list[dict], drop_elided: bool = True) -> dict:
    """Split every section into sentences, keeping the citation label.

    Returns {"items": [{"label", "text", "bag", "index", "words": int}],
             "lengths": {"min", "median", "p90", "max"}, "n": int}.

    The length distribution is part of the return value on purpose: a text with
    long unpunctuated runs of direct speech yields 300-word "sentences", and a
    caller comparing similarity scores has to know that the units it is scoring
    are not of comparable size.
    """
    items: list[dict] = []
    for s in sections:
        raw = _MILESTONE_RE.sub(" ", s.get("text", ""))
        lab = s.get("label", "")
        for j, chunk in enumerate(_SENT_SPLIT.split(raw)):
            chunk = chunk.strip()
            if not chunk:
                continue
            toks = _tokens({"text": chunk}, drop_elided)
            if not toks:
                continue
            items.append({"label": lab, "text": chunk,
                          "bag": _bag(toks), "index": j,
                          "words": len(toks)})
    lens = sorted(x["words"] for x in items)
    def pct(p: float) -> int:
        if not lens:
            return 0
        return lens[min(len(lens) - 1, int(round(p * (len(lens) - 1))))]
    return {"items": items,
            "lengths": {"min": lens[0] if lens else 0,
                        "median": pct(0.5), "p90": pct(0.9),
                        "max": lens[-1] if lens else 0},
            "n": len(items)}


def _shared_ngrams(a: list[str], b: list[str], n: int) -> list[str]:
    """The n-grams the two windows have in common, in order, deduplicated."""
    def grams(xs: list[str]) -> list[tuple[str, ...]]:
        return [tuple(xs[i:i + n]) for i in range(len(xs) - n + 1)]
    gb = set(grams(b))
    out: list[str] = []
    seen: set[tuple[str, ...]] = set()
    for g in grams(a):
        if g in gb and g not in seen:
            seen.add(g)
            out.append(" ".join(g))
    return out


def parallel_loci(sections_a: list[dict], query_words: list[str], n: int = 5,
                  min_shared: int = 1, max_words: int = 400,
                  drop_elided: bool = True) -> dict:
    """The sentences of A most similar to a window of `query_words`.

    TF-IDF cosine over sentence bags, scored with the engine's own functions.
    Two guards keep it honest rather than merely suggestive:

      * `min_shared` — a hit must share at least this many distinct n-grams
        (2- and 3-gram, pooled spelling) with the query. Cosine over short
        sentences can be dominated by function words (`καὶ ... δὲ ...`), and a
        "parallel" with no shared phrase is a false friend. Hits below the bar
        are dropped, not down-weighted, and `n_dropped` reports how many.
      * `max_words` — sentences longer than this are mostly unpunctuated runs
        and would score high simply by containing everything. They are skipped
        and counted in `n_skipped_long`, never silently.

    Returns {"hits": [{"label","text","score","shared_2","shared_3",
             "words"}], "n_scored", "n_dropped", "n_skipped_long",
             "lengths": {...}} sorted by score descending.
    """
    idx = sentences(sections_a, drop_elided=drop_elided)
    items = idx["items"]
    pool = [x for x in items if x["words"] <= max_words]
    qbag = _bag(query_words)
    if not qbag or not pool:
        return {"hits": [], "n_scored": len(pool),
                "n_dropped": 0, "n_skipped_long": len(items) - len(pool),
                "lengths": idx["lengths"]}
    idf = _idf([x["bag"] for x in pool])
    qvec = _tfidf(qbag, idf)
    scored = []
    for x in pool:
        sc = cosine(qvec, _tfidf(x["bag"], idf))
        if sc <= 0.0:
            continue
        scored.append((sc, x))
    scored.sort(key=lambda p: -p[0])
    # The windows compared for shared phraseology are the SENTENCE's words, not
    # its bag — order matters for an n-gram and a bag has none. Computed once,
    # not per candidate.
    qtoks = [variants_unify(normalize(w), VARIANTS_DEFAULT) for w in query_words]
    qtoks = [t for t in qtoks if t]
    hits = []
    n_dropped = 0
    for sc, x in scored:
        if len(hits) >= n:
            break
        stoks = [variants_unify(normalize(w), VARIANTS_DEFAULT)
                 for w in _tokens({"text": x["text"]}, drop_elided)]
        s2 = _shared_ngrams(stoks, qtoks, 2)
        s3 = _shared_ngrams(stoks, qtoks, 3)
        if len(s2) + len(s3) < min_shared:
            n_dropped += 1
            continue
        hits.append({"label": x["label"], "text": x["text"],
                     "score": round(sc, 6), "shared_2": s2, "shared_3": s3,
                     "words": x["words"]})
    return {"hits": hits, "n_scored": len(pool), "n_dropped": n_dropped,
            "n_skipped_long": len(items) - len(pool), "lengths": idx["lengths"]}


def ngram_table(sections: list[dict], keys: set[str], n: int = 2,
                variants: tuple[str, ...] = VARIANTS_DEFAULT,
                context: bool = True, limit: int = 60,
                drop_elided: bool = True) -> dict:
    """The n-grams a key participates in, with counts.

    `context=True` counts n-grams that CONTAIN the key (both the key's left and
    right neighbours, as a window over the key). `context=False` counts every
    n-gram of the text, which is what a phrase-level comparison of two works
    needs — but it is a much bigger table, so the caller asks for it explicitly.

    `keys` are pooled keys, and every token is pooled before the window is
    taken, so `τὰ ξύμμαχα` and `τὰ σύμμαχα` are one bin. Each row carries BOTH
    spellings: `gram` is the original (accented, as-printed) window, for reading,
    and `pooled` is the pooled window the bin is actually counted under, for
    comparing two works. They are not interchangeable — A's `ἡ ξυμμαχία` and B's
    `ἡ συμμαχία` are the same phrase and only the pooled form says so.

    Returns {"grams": [{"gram": [str], "pooled": [str], "count": int,
             "key": str, "contentful": bool}], "total": int, "n_gram": int}.
    """
    counts: Counter = Counter()
    display: dict[tuple, list[str]] = {}
    total = 0
    for s in sections:
        toks = _tokens(s, drop_elided)
        if len(toks) < n:
            continue
        norms = [variants_unify(normalize(t), variants) for t in toks]
        for i in range(len(toks) - n + 1):
            window = norms[i:i + n]
            gk = tuple(window)
            if context:
                if not any(w in keys for w in window):
                    continue
                # The key this gram is filed under: the pooled key present in
                # the window. A window can hold two keys (ξυμμαχία ... γίγνομαι)
                # and is counted under each, because the table is per word.
                for w in set(window):
                    if w in keys:
                        counts[(w, gk)] += 1
                        display.setdefault((w, gk), toks[i:i + n])
                continue
            counts[gk] += 1
            display.setdefault(gk, toks[i:i + n])
            total += 1
    rows = []
    for k, c in counts.most_common(limit):
        if context:
            key, gk = k
        else:
            key, gk = None, k
        rows.append({"gram": list(display.get(k) or gk), "pooled": list(gk),
                     "count": c, "key": key,
                     # Flagged so the UI can de-emphasise `ἐν τῇ`-type bins
                     # without hiding them: the counts stay inspectable.
                     "contentful": any(_contentful(w) for w in gk)})
    return {"grams": rows, "total": sum(counts.values()), "n_gram": n}


# Function words so common that a gram made only of them says nothing about
# style. Not a stoplist — nothing is removed — only a display flag. These are
# POOLED spellings (accents stripped), as the table stores them.
_FUNCTION_WORDS = frozenset("""
αι αν αλλα αλλ αρα απο αυτα αυται αυτας αυτη αυτην αυτης αυτο αυτον αυτος αυτου
αυτους αυτων γαρ γε γουν δε δη δια εαν εγω ει εκ εξ εν επι εστι εστιν εισι ειναι
ην η ο οι ην ης ινα κατα με μεν μεντοι μετα μη νυν ο ου ουκ ουχ ος οτι οταν οτε
ουν περι προς συ συν τα ται ταις τας τε την της το τοι τοις τον του τουτο τουτον
τους των υπερ υπο ως
""".split())


def _contentful(tok: str) -> bool:
    """Does this pooled token carry meaning, or is it a function word?

    Deliberately conservative: an unknown token counts as contentful, so the
    flag errs toward showing the row. Accents are already stripped by the
    pooling, and one-letter tokens are function words in Greek without
    exception (`ὁ`, `ἡ`, `τὸ`, `ἐν`, `ἐξ`).
    """
    if len(tok) <= 2:
        return False
    return tok not in _FUNCTION_WORDS


def ngram_contrast(ga: dict, gb: dict, min_a: int = 2, max_b: int = 0,
                   limit: int = 40, total_a: int = 0, total_b: int = 0) -> dict:
    """Phraseology of A against B, ranked by the same collapse score as the
    lexical report.

    The score is the Haldane-Anscombe-corrected log2 rate ratio used throughout
    `archaism_pure`, so a gram with zero occurrences in B stays finite instead of
    dividing by zero, and the rows are comparable with the word rows above them.

    `total_a` / `total_b` are the corpus sizes the rates divide by. They are
    parameters rather than derived from `ga`/`gb` because `ngram_table` with
    `context=True` counts each gram once PER KEY, so its own `total` is a sum
    over rows, not a token count — feeding that in as a denominator would be a
    silent unit error.

    Returns {"rows": [{"gram","key","count_a","count_b","rate_a","rate_b",
             "score"}], "n_a","n_b","params": {...}} where `key` is the pooled
    word the gram was filed under, or None for a whole-text table.
    """
    def index(g: dict) -> dict:
        # Keyed by (filed-under key, POOLED gram). Both halves are load-bearing:
        #
        #   * the key, because a `context` table files one window under EACH
        #     wanted key it contains, and those rows share a gram — keying on
        #     the gram alone would silently collapse two counts into one;
        #   * the POOLED gram, not the printed one, because that is the whole
        #     point of the pooling: A's `ἡ ξυμμαχία` and B's `ἡ συμμαχία` are
        #     one phrase, and indexing on the printed spelling would file them
        #     as two rows that never meet — the comparison would report exactly
        #     the correspondence it exists to find as an absence in B.
        #
        # `None` is the key of a whole-text table.
        return {(x.get("key"), tuple(x.get("pooled") or x["gram"])): x["count"]
                for x in g.get("grams", [])}
    ia, ib = index(ga), index(gb)
    # As-printed spelling per pooled gram, so a row can be shown the way the
    # author wrote it. A's spelling wins when both have one: A is the model
    # author here, and the printed form is only for reading — the counts and the
    # score are the pooled ones either way.
    shown: dict[tuple, list[str]] = {}
    for g in (gb, ga):
        for x in g.get("grams", []):
            shown[tuple(x.get("pooled") or x["gram"])] = list(x["gram"])
    na = total_a or sum(ia.values()) or 1
    nb = total_b or sum(ib.values()) or 1
    rows = []
    for g, ca in ia.items():
        cb = ib.get(g, 0)
        if ca < min_a or cb > max_b:
            continue
        ra = ca * 1000.0 / na
        rb = cb * 1000.0 / nb
        sc = math.log2(((ca + 0.5) / na) / ((cb + 0.5) / nb))
        # `gram` is the pooled window — the thing the two counts are counts OF.
        # A caller wanting to print it as text has `gram`; a caller wanting the
        # as-printed spelling has the per-work tables it passed in.
        rows.append({"gram": list(g[1]), "key": g[0],
                     "display": shown.get(g[1], list(g[1])),
                     "count_a": ca, "count_b": cb,
                     "rate_a": ra, "rate_b": rb, "score": sc})
    rows.sort(key=lambda r: -r["score"])
    return {"rows": rows[:limit], "n_a": na, "n_b": nb,
            "params": {"min_a": min_a, "max_b": max_b, "limit": limit}}

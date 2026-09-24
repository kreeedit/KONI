"""Archaism detector — lexical frequency contrast between two works.

Pure stdlib, zero dependencies, like the rest of the engine.

NOT text reuse. The Flame engine asks "did this PASSAGE recur between these
two works?"; this module asks "did this WORD's rate collapse from the earlier
work to the younger one?" Different question, different granularity (work-level,
not passage-level), different output surface. Do not present one as the other.

The signal, for a word w and an ORDERED pair (A = earlier, B = younger):

    count_A(w) >= min_a      the word was established in the earlier work
    min_b <= count_B(w) <= max_b   it SURFACES in the younger work, rarely
    score(w)   >= min_score  the collapse is large

`min_b` defaults to 1, and that is a substantive part of the definition, not a
tidiness filter: the phenomenon is a word that TURNS UP in the younger work
(a few times, or once) after being common in the earlier one. A word the
younger author never uses at all is a different observation — it is the
earlier work's vocabulary, and with `min_b = 0` those absent words dominate
every result list by sheer count (they are the large majority of any author's
vocabulary), burying the handful of genuine rare-attestation rows.

where `score` is the log2 ratio of the two rates under an add-half prior:

    score = log2( ((count_a + 0.5) / N_a) / ((count_b + 0.5) / N_b) )

The +0.5 (Haldane-Anscombe) keeps `count_b == 0` finite instead of producing
an infinite ratio. Rates are per token, reported per 1000 words by the caller.

WHAT THIS IS NOT. A rate collapse is a CANDIDATE, never a verdict. The same
signal is produced by a genuine archaism, a quotation or allusion, a technical
or religious term, a proper noun, a topic or genre shift, and by plain sampling
noise — and nothing in a bag of word counts can tell those apart. The module
ranks candidates by the size of the collapse and says so. Any UI or report
built on it must present the rows as candidates to inspect, not as findings.

TOPIC DOMINATES THE RAW RANKING, so `drop_proper` defaults to True. Measured
on Thucydides -> Procopius, the unfiltered top rows are ALL ethnics and
toponyms — Ἀθηναῖοι (502 -> 0), Λακεδαιμόνιοι (213 -> 0), Συρακόσιοι,
Πελοποννήσιοι, Κορίνθιοι — because Thucydides' subject IS the Peloponnesian
War and Procopius' subject is Justinian's wars. That is topic shift, not
archaism, and no frequency statistic can distinguish the two; only dropping
the proper nouns can. The filter is a majority-capitalization test on the
ORIGINAL spellings (see `work_freq`), which separates cleanly in these
editions: the capitalization ratio per word is bimodal, with 397 words at
100% and 2637 at 0% in Thucydides, and almost nothing in between. What it
correctly KEEPS is the real signal — αἰεί (Ionic/epic "always") is 121x in
Thucydides at 0% capitalization and 0x in Procopius, and survives.

SURFACE FORMS, NOT LEMMAS. ποταμόν and ποταμός are two separate rows. This is
honest but noisier: an inflection split across two rows can hide a real signal,
and a "hapax" here means a hapax *of that surface form*, not of the lexeme.
Lemma grouping would need a morphological analyser, i.e. a dependency.

Normalization is `flame_pure.normalize` (NFKD + drop combining marks + lower),
so accented and unaccented spellings of the same form count together.
"""
from __future__ import annotations

import math
from collections import Counter

from .flame_pure import normalize, words, words_elided
from .variants import BY_NAME as VARIANT_RULES
from .variants import DEFAULT as VARIANTS_DEFAULT
from .variants import describe as variants_describe
from .variants import marked_rules
from .variants import names as variants_names
from .variants import unify as variants_unify

# Defaults chosen to match the described phenomenon: a word that occurred
# SEVERAL times in the earlier work and is RARE (or a hapax) in the younger.
MIN_A = 3          # established in the earlier work
MIN_B = 1          # the word must actually OCCUR in the younger work
MAX_B = 1          # ...rarely: 1 = exactly a hapax. Raise for "a few times".
MIN_SCORE = 2.0    # >= 4x rate collapse (log2)
LIMIT = 300        # cap on returned rows
# A word counts as a proper noun when it is capitalized in the majority of its
# occurrences across BOTH works. Pooling the two works matters: a candidate is
# rare in the younger one by construction, so its ratio there would be decided
# by one or two tokens.
PROPER_RATIO = 0.5

# --- the third corpus: a contemporary, NON-archaizing Koine reference -------
# Declared here, not fetched here: this module never touches the network, the
# caller resolves the work through `texts` and passes its sections in. The
# entry carries the evidence for the CHOICE so the UI can disclose it instead
# of asserting it.
KOINE_REFERENCE = {
    "aid": "2057", "wid": "002",
    "author": "Socrates Scholasticus",
    "work": "Historia Ecclesiastica",
    "era": "4th-5th c. A.D.",
    "urn": "urn:cts:greekLit:tlg2057.tlg002",
    "why": "The archaism test needs a THIRD work: a contemporary Koine author "
           "who does NOT archaize, so that 'absent from the later period' can "
           "be told apart from 'absent from this one work'. Socrates writes "
           "historiography like Thucydides and Procopius, so GENRE is held "
           "constant and only the register varies — the confound the whole "
           "critique is about. It is in First1KGreek, so no new dependency: "
           "the existing CTS path reads it.",
}

# Class thresholds, in log2 of the rate ratio (see `koine_contrast`). 1.0 is a
# halving/doubling of the rate under the add-half prior; the prior keeps a zero
# count finite, which is what makes a single "absent" threshold workable at all.
MIN_AC = 1.0       # word is (much) more frequent in A than in the Koine norm
MIN_BC = 1.0       # ...and in B too
MIN_REVIVAL = 0.5  # ...and B uses it MORE than its own model author does
# Report order: the sharp class first, then the class it must be read against,
# then the two mannerism classes. Without a fixed order a limit silently decides
# which classes the reader ever sees.
CLASS_ORDER = ("archaism", "classical", "overused", "avoided", "shared")


def work_freq(sections: list[dict], drop_elided: bool = True,
              variants: tuple[str, ...] = VARIANTS_DEFAULT) -> dict:
    """Word frequencies over a work's FULL text.

    The caller MUST pass unwindowed units — `texts.section_texts(aid, wid,
    window=False)`. The engine's comparison windows overlap by UNIT_OVERLAP
    words, so counting over them double-counts every boundary by a fraction
    that depends on each unit's length and therefore does NOT cancel between
    two works; it would inflate the rates of whichever work has longer leaves.

    `drop_elided` (default True) discards elision fragments — see
    `flame_pure.words_elided`. These are not words but the tails of elided ones
    (τ for τε, ἀλλ for ἀλλά), and since they make up 1.64% of Thucydides' tokens
    against 0.81% of Procopius', leaving them in produces `τ`, `ἀλλ`, `ἐπ` as
    top "archaism" rows AND skews the rates unevenly between the works. Pass
    False to count them, and `n_elided` reports how many were excluded either
    way, so the choice is never silent.

    `variants` selects which morphophonetic correspondences to POOL (see
    `variants.unify`). Pooling is a correctness fix, not a taste: Thucydides'
    `ἧσσον` and Procopius' `ἥττων` are one word, and left unpooled its
    statistics are torn in half so neither row shows the real rate. It is safe
    in one direction only — the classical spelling is folded onto the Koine one,
    never back. Pass `()` to key on surface forms exactly as before; the
    selection actually applied is reported back in `variants`.

    Returns {"counts": Counter[key], "total": int, "display": {key: orig},
             "caps": Counter[key], "forms": {key: Counter[norm_form]},
             "n_elided": int, "variants": tuple}.  `display` keeps the first
    original (accented) spelling seen, so a row can be shown as it appears in
    the text; `caps` counts occurrences whose ORIGINAL spelling was capitalized
    — the evidence for the proper-noun filter; `forms` keeps every distinct
    normalised spelling pooled under that key, which is what lets a row disclose
    that it merged `ἥττων` with `ἥσσον` instead of quietly reporting one of
    them. Accents are dropped by `normalize` but case is not, so the two pieces
    of evidence are collected separately, from the raw token.
    """
    counts: Counter = Counter()
    caps: Counter = Counter()
    display: dict[str, str] = {}
    formc: dict[str, Counter] = {}
    n_elided = 0
    for s in sections:
        for w, elided in words_elided(s.get("text", "")):
            if elided:
                n_elided += 1
                if drop_elided:
                    continue
            n = normalize(w)
            if not n:
                continue
            key = variants_unify(n, variants)
            counts[key] += 1
            if w[:1].isupper():
                caps[key] += 1
            if key not in display:
                display[key] = w
            formc.setdefault(key, Counter())[n] += 1
    return {"counts": counts, "total": sum(counts.values()),
            "display": display, "caps": caps, "n_elided": n_elided,
            "forms": formc, "variants": tuple(variants),
            # Carried so `contrast` can run its location pass with the SAME
            # tokenization this count used, instead of assuming the default.
            "drop_elided": drop_elided}


def occurrences(sections: list[dict], wanted: set[str], limit: int = 12,
                drop_elided: bool = True) -> dict:
    """Section labels in which each wanted word occurs (one entry per section).

    A SECOND pass, restricted to the handful of candidate words. Collecting
    labels eagerly in `work_freq` would store a section list for every word —
    including καί, which appears in every section — for a result that only ever
    displays the rare ones. The limit bounds what a very common word would cost
    if it did survive the filters.

    Tokenizes exactly as `work_freq` does, `drop_elided` included. It used to
    use plain `words()`, which counts the elided fragments — so a word whose
    real count was 1 could be shown with 12 section labels, every one of them a
    section where the only hit was a fragment. The evidence panel contradicted
    the count it was there to support; now the two passes agree.
    """
    out: dict[str, list[str]] = {w: [] for w in wanted}
    for s in sections:
        lab = s.get("label", "")
        seen: set[str] = set()
        for w, elided in words_elided(s.get("text", "")):
            if elided and drop_elided:
                continue
            n = normalize(w)
            if n in out and n not in seen:
                seen.add(n)
                if len(out[n]) < limit:
                    out[n].append(lab)
    return out


def variant_breakdown(key: str, fa: dict, fb: dict) -> list[dict]:
    """The distinct spellings pooled under `key`, with counts in A and B.

    Empty when the key stands for a single spelling in both works, which is the
    common case — the row then needs no disclosure.
    """
    forms_a = fa.get("forms", {}).get(key, {})
    forms_b = fb.get("forms", {}).get(key, {})
    # The union across BOTH works, not each work separately. The whole point of
    # the pool is that the two works choose DIFFERENT spellings: A writes ἧσσον
    # and never ἥττων, B the reverse, so each side sees exactly one form and a
    # per-work test would report "nothing was pooled" for the clearest case
    # there is. (Measured: that mistake made every one of 300 rows silent.)
    if len(set(forms_a) | set(forms_b)) < 2:
        return []
    out = []
    for form in sorted(set(forms_a) | set(forms_b),
                       key=lambda f: (-(forms_a.get(f, 0) + forms_b.get(f, 0)), f)):
        out.append({"form": form,
                    "count_a": forms_a.get(form, 0),
                    "count_b": forms_b.get(form, 0),
                    "marked": marked_rules(form, fa.get("variants", ())) or None})
    return out


def variant_report(sections_a: list[dict], sections_b: list[dict],
                   variants: tuple[str, ...] = VARIANTS_DEFAULT,
                   drop_proper: bool = True) -> dict:
    """REPORT 2 OF 2 — the style register, measured as a spelling-choice rate.

    This answers a different question from `contrast`, and it exists because
    `contrast` structurally CANNOT answer it. `contrast` ranks words by how far
    their rate collapsed, so it finds only archaisms that are also rare in the
    younger work. Measured on Thucydides -> Procopius, the three correspondences
    in `variants` run in three DIFFERENT directions:

        xyn  (ξυ-)     12.790/1k -> 12.851/1k   PARITY   (A/B 1.00)
        gign (γιγν-)    2.404/1k ->  0.121/1k   COLLAPSE (A/B 19.83)
        tt   (ττ-)      0.068/1k ->  0.485/1k   EXCESS   (A/B 0.14)

    `xyn` is systemic imitation at the model author's own rate — nothing is
    rare, so a rarity filter is blind to it. `tt` runs the other way entirely,
    because -ττ- is the 2nd-c. AD Atticist restoration rather than a
    Thucydidean trait; a rarity filter scores it as ANTI-archaism. And this is
    why a third, contemporary reference corpus is needed to interpret the
    ratios: whether a parity or an excess is the archaizing choice is a fact
    about the period's norm, not something derivable from the model author. The
    structure here (`compare` over any two works) is already the shape that
    three-way comparison needs; only the caller changes.

    Rates are MARKED tokens per 1000 tokens, proper nouns removed when
    `drop_proper` — the filter is load-bearing here: 62-64% of the raw ττ
    tokens in both works are proper nouns (`Ἀττική`, `Οὐιττιγίς`).

    Returns {"rules": [per-rule dict], "n_a": int, "n_b": int, "params": {...}}
    where each rule dict carries both works' rates and the direction label.
    """
    ra = variant_rates(sections_a, variants, drop_proper)
    rb = variant_rates(sections_b, variants, drop_proper)
    out = []
    for name in variants:
        a, b = ra["rules"].get(name), rb["rules"].get(name)
        if a is None or b is None:
            continue
        ratio = (a["rate"] / b["rate"]) if b["rate"] else None
        if ratio is None:
            direction = "absent-in-B"
        elif 0.75 <= ratio <= 1.33:
            direction = "parity"
        elif ratio > 1:
            direction = "collapse"
        else:
            direction = "excess"
        out.append({
            "name": name, "summary": VARIANT_RULES[name].summary,
            "marked": VARIANT_RULES[name].marked,
            "key_side": VARIANT_RULES[name].key_side,
            "count_a": a["count"], "count_b": b["count"],
            "rate_a": a["rate"], "rate_b": b["rate"],
            "n_proper_a": a["n_proper"], "n_proper_b": b["n_proper"],
            "ratio_ab": round(ratio, 3) if ratio else None,
            "direction": direction,
            "evidence": VARIANT_RULES[name].evidence,
            "caveat": VARIANT_RULES[name].caveat,
        })
    return {"rules": out, "n_a": ra["total"], "n_b": rb["total"],
            "params": {"variants": list(variants), "drop_proper": drop_proper}}


def variant_rates(sections: list[dict], variants: tuple[str, ...] = VARIANTS_DEFAULT,
                  drop_proper: bool = True) -> dict:
    """Marked-spelling counts for one work: the numerator of the style metric.

        "count"  tokens whose normalised form wears the marked spelling
        "rate"   count per 1000 tokens
        "n_proper" how many of those were dropped as proper nouns

    Only the MARKED side is counted, never the key side. That is deliberate and
    measured: the key-side count is polluted beyond use — of Procopius' 27 `γιν`
    tokens, 25 are `Οὐιττιγίν` and 9 `Αἴγιναν`, and of the `συ-` side's top
    forms, 291 of 338 in Thucydides are `Συρακόσιοι`. The marked side, by
    contrast, is exact (`γιγν` occurs in no other word). So the metric is a
    rate per token, which needs no denominator from the pair and is therefore
    comparable between works of different length.
    """
    total = 0
    counts: Counter = Counter()
    prop: Counter = Counter()
    for s in sections:
        for w, elided in words_elided(s.get("text", "")):
            if elided:
                continue
            n = normalize(w)
            if not n:
                continue
            total += 1
            for name in variants:
                rule = VARIANT_RULES.get(name)
                if rule is None or not rule.applies_to(n):
                    continue
                counts[name] += 1
                if w[:1].isupper():
                    prop[name] += 1
    denom = total or 1
    rules = {}
    for name in variants:
        clean = counts[name] - (prop[name] if drop_proper else 0)
        rules[name] = {"count": clean, "n_proper": prop[name],
                       "rate": round(1000 * clean / denom, 3)}
    return {"rules": rules, "total": total}


def contrast(fa: dict, fb: dict, min_a: int = MIN_A, min_b: int = MIN_B,
             max_b: int = MAX_B, min_score: float = MIN_SCORE, limit: int = LIMIT,
             sections_b: list[dict] | None = None,
             drop_proper: bool = True) -> dict:
    """Rank words by how far their rate collapsed from work A to work B.

    `fa`/`fb` are `work_freq` results. A is the EARLIER work, B the YOUNGER —
    the direction is the caller's to state, since this module does not know
    (and should not guess) which work is later. Swapping them asks a different
    question and gives a different answer.

    Pass `sections_b` to attach the younger work's occurrence labels to each
    row (a second pass, only over the survivors).

    `min_b` is the lower bound on the younger work's count, defaulting to 1: the
    word must SURFACE there. Setting it to 0 asks the different question of what
    the younger author never uses, and those absent words swamp the ranking (see
    the module docstring).

    `drop_proper` removes words that are capitalized in the majority of their
    occurrences across both works. It defaults ON because otherwise the ranking
    is dominated by the earlier work's SUBJECT MATTER rather than its diction
    (see the module docstring for the measurement). Pass False to see them.

    Returns {"rows": [...], "n_a": int, "n_b": int, "params": {...},
             "n_candidates": int} — `n_candidates` is the count BEFORE `limit`,
    so a truncated table can say so instead of silently shortening. It also
    counts BEFORE the proper-noun filter is reported separately, as
    `n_dropped_proper`, so a table can say what it hid.
    """
    # Clamp here, not only at the HTTP layer, so a direct caller cannot ask for
    # a negative `limit` (which would slice from the END of the ranked list and
    # silently drop the strongest rows).
    min_a = max(1, int(min_a))
    min_b = max(0, int(min_b))
    # A max_b below min_b is an empty interval, not an error — it should return
    # nothing rather than silently widening to `min_b` and answering a
    # different question than the caller asked.
    max_b = max(0, int(max_b))
    limit = max(0, int(limit))
    min_score = float(min_score)
    if not math.isfinite(min_score):
        # `score < nan` is False for every row, so a non-finite threshold would
        # ADMIT everything rather than reject it — fall back to the default.
        min_score = MIN_SCORE

    ca, cb = fa["counts"], fb["counts"]
    capa, capb = fa.get("caps", {}), fb.get("caps", {})
    na = fa["total"] or 1
    nb = fb["total"] or 1
    disp_b = fb["display"]

    rows = []
    n_dropped_proper = 0
    for w, count_a in ca.items():
        if count_a < min_a:
            continue
        count_b = cb.get(w, 0)
        if count_b > max_b or count_b < min_b:
            continue
        # Add-half prior so count_b == 0 stays finite (log2 of a ratio of
        # rates, not of raw counts — the works differ in length).
        score = math.log2(((count_a + 0.5) / na) / ((count_b + 0.5) / nb))
        if score < min_score:
            continue
        # Pool both works' capitalization evidence. Using the younger work's
        # alone would be decided by the one or two tokens this filter is
        # looking for in the first place.
        seen = count_a + count_b
        proper = seen > 0 and (capa.get(w, 0) + capb.get(w, 0)) / seen > PROPER_RATIO
        if proper and drop_proper:
            n_dropped_proper += 1
            continue
        rows.append({
            "norm": w,
            # Prefer the younger work's own spelling for display: that is where
            # the reader will look, and the row is about its rarity there.
            "word": disp_b.get(w) or fa["display"].get(w, w),
            "count_a": count_a, "count_b": count_b,
            "rate_a": round(count_a / na * 1000, 4),
            "rate_b": round(count_b / nb * 1000, 4),
            "score": round(score, 2),
            "proper": proper,
            # Which spellings this row pooled, and which of them wear a marked
            # (classicizing) form. Disclosed because a pooled row's count is a
            # SUM over variants: a reader who sees only `ἥττων` would take the
            # number for that spelling alone.
            "variants": variant_breakdown(w, fa, fb),
        })

    # Deterministic: score, then how established it was, then the word itself.
    rows.sort(key=lambda r: (-r["score"], -r["count_a"], r["norm"]))
    n_candidates = len(rows)
    rows = rows[:limit]

    if sections_b is not None and rows:
        occ = occurrences(sections_b, {r["norm"] for r in rows},
                          drop_elided=fb.get("drop_elided", True))
        for r in rows:
            r["labels_b"] = occ.get(r["norm"], [])

    return {
        "rows": rows, "n_a": fa["total"], "n_b": fb["total"],
        "n_candidates": n_candidates, "n_dropped_proper": n_dropped_proper,
        # Elision fragments excluded from the counts, per work. Reported so a
        # caller can see that the totals are post-exclusion, not raw.
        "n_elided_a": fa.get("n_elided", 0), "n_elided_b": fb.get("n_elided", 0),
        "params": {"min_a": min_a, "min_b": min_b, "max_b": max_b,
                   "min_score": min_score, "limit": limit,
                   "drop_proper": drop_proper,
                   # The pooling that was ACTUALLY used, read back from the
                   # counts rather than assumed — `fa` carries its own
                   # selection, so a table can disclose it even when the caller
                   # passed nothing. A mismatch between the two works' pooling
                   # is flagged instead of hidden: comparing differently
                   # tokenized counts would invent a difference.
                   "variants": list(fa.get("variants", ())),
                   "variants_mismatch": bool(
                       fb.get("variants", ()) != fa.get("variants", ()))},
    }


def report(sections_a: list[dict], sections_b: list[dict],
           min_a: int = MIN_A, min_b: int = MIN_B, max_b: int = MAX_B,
           min_score: float = MIN_SCORE, limit: int = LIMIT,
           drop_proper: bool = True,
           variants: tuple[str, ...] = VARIANTS_DEFAULT) -> dict:
    """REPORT 1 OF 2 — convenience wrapper: count both works, then contrast.

    `sections_a`/`sections_b` must be UNWINDOWED units of the earlier and the
    younger work respectively (see `work_freq`). `variants` is the pooling
    selection, applied identically to both works — pooling one side and not the
    other would compare different tokenizations and invent a difference.
    """
    fa = work_freq(sections_a, variants=variants)
    fb = work_freq(sections_b, variants=variants)
    return contrast(fa, fb, min_a=min_a, min_b=min_b, max_b=max_b,
                    min_score=min_score, limit=limit, sections_b=sections_b,
                    drop_proper=drop_proper)


def _classify(ca: int, cb: int, cc: int, na: int, nb: int, nc: int,
              min_ac: float, min_bc: float, min_revival: float) -> tuple[str, float, float, float]:
    """Rate-pattern class of one word over the three corpora.

    Three log2 rate ratios under the same add-half prior `contrast` uses:

        score_ac  A's rate against the Koine norm's  — "this word is classical"
        score_bc  B's rate against the Koine norm's  — "...and so is B's usage"
        score_ab  A's rate against B's               — "B uses it MORE than A"

    and the class is read off them:

        archaism   score_ac >= min_ac and score_bc >= min_bc and score_ab <= -min_revival
        classical  score_ac >= min_ac and score_bc >= min_bc   (but not overused)
        overused   score_bc >= min_bc                          (Koine has it too)
        avoided    score_bc <= -min_bc                         (B shuns the Koine word)
        shared     everything else

    WHY `score_ab` IS THE LOAD-BEARING TERM, and why the rest is not enough.
    The user's criterion — classical-high, Koine-absent, present in B — is
    exactly `score_ac >= min_ac and score_bc >= min_bc`, and applied literally
    it returns 1378 of 5485 words (25%): `συμμαχοι`, `νηες`, `θερους`,
    `σικελια`, `αφικνουνται`. Those are not archaisms. They are absent from C
    for the same reason the proper nouns are: Socrates writes church history
    and has no fleets, no summers-of-a-campaign and no Sicily. Relocating the
    comparison from B's rarity (`contrast`, where the same confound appears as
    a `B=1` artefact) to C's absence does not remove the confound — it moves it.

    `score_ab` is what removes it, and it is the right question on independent
    grounds: archaizing MEANS overusing the model author's diction relative to
    the model author's own rate. Measured, the two populations separate
    cleanly on it:

        revival  (score_ab <= -0.5)  σφισιν, σφισι, σφων, ταλλα, ηκιστα,
                                     ενθενδε, νω, ονπερ, ξυνηνεχθη, πανταπασιν
        subject  (score_ab >  -0.5)  συμμαχοι, νηες, θερους, σικελια,
                                     καρχηδονα, πολιορκιαν, στρατω, φρουριον

    — 341 words against 1037, and the sharp class is the one whose members are
    grammatical and marked rather than topical and lexical.

    WHAT `score_ab` STILL DOES NOT DO, disclosed rather than papered over: the
    sharp class still contains Procopius' own subject matter when he happens to
    dwell on it more than Thucydides does — `καρχηδονα` (Carthage), `στρατω`,
    `πολιορκιαν`, `ποταμος`, `πεδιω` are in it, because Justinian's wars talk
    about sieges, rivers and plains more than book 1 of Thucydides does. No bag
    of counts can separate "overused because archaizing" from "overused because
    the topic demands it", and the reader is given `marked_b` (the Attic
    spelling choices `variants` can see in B's own tokens) plus all three counts
    and rates to tell them apart by inspection.
    """
    na, nb, nc = na or 1, nb or 1, nc or 1
    sac = math.log2(((ca + 0.5) / na) / ((cc + 0.5) / nc))
    sbc = math.log2(((cb + 0.5) / nb) / ((cc + 0.5) / nc))
    sab = math.log2(((ca + 0.5) / na) / ((cb + 0.5) / nb))
    if sac >= min_ac and sbc >= min_bc:
        return ("archaism" if sab <= -min_revival else "classical"), sac, sbc, sab
    if sbc >= min_bc:
        return "overused", sac, sbc, sab
    if sbc <= -min_bc:
        return "avoided", sac, sbc, sab
    return "shared", sac, sbc, sab


def koine_contrast(fa: dict, fb: dict, fc: dict, min_a: int = MIN_A,
                   min_ac: float = MIN_AC, min_bc: float = MIN_BC,
                   min_revival: float = MIN_REVIVAL, limit: int = LIMIT,
                   sections_b: list[dict] | None = None,
                   drop_proper: bool = True) -> dict:
    """REPORT 3 OF 3 — the same vocabulary seen against a Koine reference.

    `fa`/`fb` are `work_freq` results for the model author and the archaizer,
    `fc` for the contemporary NON-archaizing reference work (see
    `KOINE_REFERENCE`); A is earlier than B, C is contemporary with B.

    This is a DIFFERENT report from `contrast`, not a variant of it, and the
    difference is structural rather than a matter of parameters. `contrast`
    cannot reach the phenomenon at all: its `max_b = 1` box admits only words
    that all but vanish in B, so a word the archaizer uses MORE than the model
    author is excluded by construction — measured, `σφισιν` (0.89/1k -> 1.94/1k)
    and `καιπερ` (0.12 -> 0.49) are unreachable there however the thresholds are
    set, and the top 200 rows of that report contain ZERO archaisms (148 are
    topic-driven and 52 are `avoided` — words B shuns). So this function scans
    the vocabulary independently: `min_a` on the model author is the only
    admission test, and every surviving word gets a class and all three rates.
    The census it returns is the finding, not the ranked list alone.

    Ranked within class by evidential strength, classes in the fixed
    `CLASS_ORDER` order — a limit must not be allowed to decide WHICH KINDS of
    row the reader sees, and `avoided` alone is 48% of the vocabulary.

    `drop_proper` applies the same majority-capitalization test as `contrast`,
    pooled over all three works: ethnics and toponyms are C-absent by topic in
    every direction here (`Ἀθηναῖοι`, `Καρχηδόνιοι`), and they would otherwise
    top the sharp class in both works.

    Returns {"rows": [...], "census": {class: int}, "n_a"/"n_b"/"n_c": int,
             "n_considered": int, "n_dropped_proper": int, "params": {...},
             "n_elided_a/b/c": int}. Each row carries `count_*`, `rate_*`,
             `score_ac`/`score_bc`/`score_ab`, `class`, `proper`, `marked_b`
             (which Attic spelling choices B makes in this word) and `variants`
             (the spellings pooled under it).
    """
    min_a = max(1, int(min_a))
    limit = max(0, int(limit))
    # A non-finite threshold would ADMIT everything (`x < nan` is False), the
    # same trap `contrast` guards against.
    min_ac = float(min_ac) if math.isfinite(float(min_ac)) else MIN_AC
    min_bc = float(min_bc) if math.isfinite(float(min_bc)) else MIN_BC
    min_revival = (float(min_revival) if math.isfinite(float(min_revival))
                   else MIN_REVIVAL)

    ca_, cb_, cc_ = fa["counts"], fb["counts"], fc["counts"]
    capa, capb, capc = fa.get("caps", {}), fb.get("caps", {}), fc.get("caps", {})
    na, nb, nc = fa["total"], fb["total"], fc["total"]
    disp_b = fb["display"]
    selection = fa.get("variants", ())

    rows = []
    census: Counter = Counter()
    n_dropped_proper = 0
    for w, count_a in ca_.items():
        if count_a < min_a:
            continue
        count_b, count_c = cb_.get(w, 0), cc_.get(w, 0)
        # Only the model author's threshold admits a word; B and C are free to
        # be zero, which is the whole point of asking about them.
        seen = count_a + count_b + count_c
        proper = seen > 0 and (capa.get(w, 0) + capb.get(w, 0)
                               + capc.get(w, 0)) / seen > PROPER_RATIO
        if proper and drop_proper:
            n_dropped_proper += 1
            continue
        cls, sac, sbc, sab = _classify(count_a, count_b, count_c, na, nb, nc,
                                       min_ac, min_bc, min_revival)
        census[cls] += 1
        # Which of B's own spellings of this word wear a marked form. Read off
        # B's pooled forms rather than the key: the key has already folded the
        # Attic spelling onto the Koine one, so the marker is invisible there
        # (`ξυμμαχοι` pools to `συμμαχοι`).
        marked_b = sorted({m for form, n in fb.get("forms", {}).get(w, {}).items()
                           if n for m in marked_rules(form, selection)})
        rows.append({
            "norm": w, "word": disp_b.get(w) or fa["display"].get(w, w),
            "count_a": count_a, "count_b": count_b, "count_c": count_c,
            "rate_a": round(count_a / (na or 1) * 1000, 4),
            "rate_b": round(count_b / (nb or 1) * 1000, 4),
            "rate_c": round(count_c / (nc or 1) * 1000, 4),
            "score_ac": round(sac, 2), "score_bc": round(sbc, 2),
            "score_ab": round(sab, 2),
            "class": cls, "proper": proper, "marked_b": marked_b or None,
            "variants": variant_breakdown(w, fa, fb),
        })

    # Strength = how much evidence the class label rests on. For the two
    # Koine-absent classes that is the absence itself, sharpened for `archaism`
    # by how far past the model author B goes; for the mannerism classes it is
    # the size of the divergence from the Koine norm.
    def strength(r: dict) -> float:
        if r["class"] == "archaism":
            return r["score_ac"] - r["score_ab"]
        if r["class"] == "classical":
            return r["score_ac"]
        return abs(r["score_bc"])

    rows.sort(key=lambda r: (CLASS_ORDER.index(r["class"]), -strength(r), r["norm"]))
    n_considered = len(rows)
    rows = rows[:limit]

    if sections_b is not None and rows:
        occ = occurrences(sections_b, {r["norm"] for r in rows},
                          drop_elided=fb.get("drop_elided", True))
        for r in rows:
            r["labels_b"] = occ.get(r["norm"], [])

    return {
        "rows": rows, "n_a": fa["total"], "n_b": fb["total"], "n_c": fc["total"],
        # The census is over EVERY word that passed `min_a` (and the proper
        # filter), not over the returned page — it is the part of the finding a
        # limit cannot truncate.
        "census": {k: census.get(k, 0) for k in CLASS_ORDER},
        "n_considered": n_considered, "n_dropped_proper": n_dropped_proper,
        "n_elided_a": fa.get("n_elided", 0), "n_elided_b": fb.get("n_elided", 0),
        "n_elided_c": fc.get("n_elided", 0),
        "params": {"min_a": min_a, "min_ac": min_ac, "min_bc": min_bc,
                   "min_revival": min_revival, "limit": limit,
                   "drop_proper": drop_proper,
                   "variants": list(selection),
                   "variants_mismatch": bool(
                       fb.get("variants", ()) != selection
                       or fc.get("variants", ()) != selection)},
    }


def koine_report(sections_a: list[dict], sections_b: list[dict],
                 sections_c: list[dict], min_a: int = MIN_A,
                 min_ac: float = MIN_AC, min_bc: float = MIN_BC,
                 min_revival: float = MIN_REVIVAL, limit: int = LIMIT,
                 drop_proper: bool = True,
                 variants: tuple[str, ...] = VARIANTS_DEFAULT,
                 reference: dict | None = None) -> dict:
    """REPORT 3 OF 3 — convenience wrapper: count all three works, then classify.

    All three section lists must be UNWINDOWED (see `work_freq`). `reference`
    is metadata describing work C for the UI to disclose — pass
    `KOINE_REFERENCE`; it is echoed back untouched and this module does not
    read it, because what makes a corpus a Koine reference is an argument about
    the period, not a property of its word counts.
    """
    fa = work_freq(sections_a, variants=variants)
    fb = work_freq(sections_b, variants=variants)
    fc = work_freq(sections_c, variants=variants)
    out = koine_contrast(fa, fb, fc, min_a=min_a, min_ac=min_ac, min_bc=min_bc,
                         min_revival=min_revival, limit=limit,
                         sections_b=sections_b, drop_proper=drop_proper)
    out["reference"] = dict(reference or KOINE_REFERENCE)
    return out

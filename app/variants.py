"""Morphophonetic variant layer: the same word written two ways.

WHY THIS EXISTS
---------------
A purely lexical comparison hides systemic archaizing. Thucydides writes
`θάλασσα`, `ἧσσον`, `τεσσαράκοντα`; Procopius writes `θάλαττα`, `ἥττων`,
`τέτταρα` — the SAME lexemes, split across two rows, so each row's statistics
are torn in half and neither shows the real rate. Worse, the split is not
random: it follows the Attic/Ionic correspondence, so the two halves are a
register signal that the surface-form view cannot see at all.

So this module does two separate jobs, and keeping them separate is the whole
point:

  1. POOLING (`unify`) — map both spellings to one key so counts add up. This
     fixes the statistics. It is safe in one direction only: the classical
     spelling is normalised onto the Koine one, never back.

  2. SIDE DETECTION (`is_classicizing`) — ask whether a given token wears the
     older/Attic spelling. The RATE of that per 1000 tokens is a style metric
     that does not depend on topic, genre or vocabulary attrition: it compares
     how often each author makes the same spelling CHOICE. That is what
     "archaizing style" means at the level of a text, and it is measurable.

HONESTY ABOUT WHAT IS *NOT* HERE
--------------------------------
Deliberately excluded, each for a measured reason:

  * The Attic η ~ Ionic α correspondence (νεηνίης/νεανίας, θώρηξ/θώραξ).
    Measured over the two works, the naive patterns `ην` and `αν` match 4.7%
    and 6.7% of ALL tokens — `τήν`, `ἄν`, `Ἀθηναίων` swamp everything. It is a
    morphological correspondence, not an orthographic one, and separating it
    needs a lemma lexicon. Left to `archaism_pure`'s planned Morpheus layer.
  * A blind `ρρ` ~ `ρσ` character rule. Measured: Thucydides' ρρ hits are
    `Ἀρράβαιον` (a proper noun) and `ἐπερρώσθησαν` (ἐπ- + ἐρρω-, prefix
    assimilation); his ρσ hits are `χερσίν` (< χείρ, inflectional) and
    `Περσῶν`. Applying it blindly merges unrelated words. Curated lexemes only.
  * A `γιν` ~ `γιγν` rule in the *reverse* direction. Measured: Procopius' 27
    `γιν` hits are dominated by proper nouns — `Οὐιττιγίν` 25, `Αἴγιναν` 9,
    `Ῥηγίνων` 8, `Ἀγίν` 8. Mapping `γιν`→`γιγν` would render `Αἴγινα` as a form
    of `γίγνομαι`. Only `γιγν`→`γιν` is implemented, and `γιγν` is exact: no
    other Greek word contains it (`γίγας` has `γιγα`, not `γιγν`).

MEASURED EVIDENCE FOR EACH RULE
-------------------------------
Marked-spelling tokens per 1000 tokens, through the production path
(`applies_to`) over the unwindowed text (`window=False`), elision fragments
excluded and PROPER NOUNS REMOVED. A = Thucydides `0003/001` (147693 tokens),
B = Procopius `4029/001` (222699 tokens):

  rule            A Thuc      B Proc      A/B     direction
  xyn  (ξυ-)     12.790/1k  12.851/1k   1.00    PARITY
  gign (γιγν-)    2.404/1k   0.121/1k  19.83    COLLAPSE
  tt   (ττ-)      0.068/1k   0.485/1k   0.14    EXCESS  (B is 7.1x A)
  rr   (ρσ-)      0.284/1k   0.256/1k   1.11    parity   (metric off)

THREE DIFFERENT DIRECTIONS, and that is the point.

  * `gign` is the collapse the current view hunts: Thucydides reduplicates,
    Procopius has all but abandoned it (27 clean hits, and 11 of those are the
    same two words).
  * `xyn` is PARITY. Procopius writes ξυμμαχία at *Thucydides' own rate* — to
    three decimals. That is the clearest possible case of systemic imitation,
    and a rarity filter cannot see it at all, because nothing is rare: the
    words are common and evenly spread, only the SPELLING was chosen.
  * `tt` runs the other way. Procopius uses -ττ- 7.1x more than Thucydides
    because -ττ- is the 2nd-c. AD Atticist restoration, not a Thucydidean
    trait. A view that only filters for rarity scores this as *anti*-archaism.

So the register signal needs its own report rather than a `MAX. COUNT IN B`
box, and the rate must be compared against the contemporary norm (a third,
reference corpus) to know which direction is the archaizing one — a rule's
direction is not derivable from the model author alone.

The `tt` numbers also justify the proper-noun filter that is already in place:
62% of Thucydides' and 64% of Procopius' raw ττ tokens are proper nouns
(`Ἀττική` 84 in A, `Οὐιττιγίς` 116 = the Gothic king Witigis in B). Without
the filter the rule measures a prosopography, not a style; with it, the excess
survives (10 vs 108 clean tokens), so the signal is real.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Words whose initial ξυ- is NOT an Attic ξυν-/ξυμ- for συν-/συμ-.
# ξύλον (wood) and its family, and the razor words from ξύω: these belong to
# the ξ-stem verbs/nouns, and mapping them onto συ- would collide with real
# σύλον/συλάω. Measured: they do not appear in the top 18 ξυ- forms of either
# work, but a rule that is merely lucky on one corpus is not a rule.
_XY_STOP = ("ξυλο", "ξυλε", "ξυλη", "ξυλι", "ξυρο", "ξυρε", "ξυρα", "ξυνω")

# ξυνός/ξυνή ("common") is classicizing for κοινός, a DIFFERENT correspondence
# from ξυν- for συν-. Pooling it under συ- would be wrong, so it is excluded
# from this rule and left to the lemma layer.
_XY_STOP += ("ξυνος", "ξυνη", "ξυνον", "ξυνα")

# Ἀττικ- is the meta-vocabulary (Attic, Atticism, ἀττικίζω). It contains ττ as
# a proper-noun stem, not the -ττ-/-σσ- correspondence; pooling it onto ἀσσικ-
# would be nonsense and detecting it as a spelling choice would be circular.
_TT_STOP = ("αττικ",)

# ρρ/ρσ relies on the fact that Thucydides has the OLDER Attic ρσ where later
# Attic normalised to ρρ. Only these lexeme families show the correspondence;
# everywhere else ρρ is prefix assimilation and ρσ is inflection.
_RR_LEXEMES = (
    ("θαρσ", "θαρρ"),      # θάρσος/θάρρος, θαρσέω/θαρρέω, θαρσαλέος/θαρραλέος
    ("αρσην", "αρρην"),    # ἄρσην/ἄρρην  (ἀρσενικός/ἀρρενικός)
    ("κορσ", "κορρ"),      # κόρση/κόρρη
    ("μυρσ", "μυρρ"),      # μυρσίνη/μυρρίνη
)


@dataclass(frozen=True)
class Rule:
    """One declared Attic/Koine correspondence.

    `older` is the side the model author (Thucydides) uses for `xyn`, `gign`
    and `rr`; for `tt` the older side is `ss` and the phrase `everyday` is
    wrong — the field is the label of the side THIS RULE treats as the marked
    one, spelled out per rule in `marked`. What is constant across rules is
    only the direction of POOLING: the Koine side is the key.
    """
    name: str
    summary: str
    key_side: str                 # the label the pooling key carries
    marked: str                   # the label counted as the marked spelling
    pooling: str                  # "prefix" | "substring" | "lexemes"
    metric: bool                  # usable as a style metric
    marked_pattern: str = ""      # substring/prefix matched on the normalised form
    marked_stop: tuple = ()
    lexemes: tuple = ()
    evidence: str = ""
    caveat: str = ""

    def applies_to(self, form: str) -> bool:
        """Is `form` (already `normalize`d) wearing the marked spelling?"""
        if self.pooling == "prefix":
            hit = form.startswith(self.marked_pattern)
        elif self.pooling == "substring":
            hit = self.marked_pattern in form
        else:  # lexemes
            return any(form.startswith(a) for a, _ in self.lexemes)
        if not hit:
            return False
        return not any(form.startswith(s) for s in self.marked_stop)


RULES: tuple[Rule, ...] = (
    Rule(
        name="xyn",
        summary="Attic ξυν-/ξυμ- for Koine συν-/συμ-",
        key_side="συ", marked="ξυ", pooling="prefix", metric=True,
        marked_pattern="ξυ", marked_stop=_XY_STOP,
        evidence="A 12.790/1k -> B 12.851/1k (A/B 1.00): PARITY, the clearest "
                 "systemic imitation in the set and invisible to a rarity filter",
        caveat="ξυνός is excluded: it stands to κοινός, not to συν-.",
    ),
    Rule(
        name="gign",
        summary="Attic reduplicated γιγν- for Koine γιν-",
        key_side="γιν", marked="γιγν", pooling="substring", metric=True,
        marked_pattern="γιγν",
        evidence="A 2.404/1k -> B 0.121/1k (A/B 19.83): COLLAPSE",
        caveat="Exact: no other Greek word contains γιγν (γίγας has γιγα). "
               "The reverse direction is NOT applied — Αἴγινα, Ῥήγιον, "
               "Οὐιττιγίς would all become forms of γίγνομαι.",
    ),
    Rule(
        name="tt",
        summary="Attic -ττ- for Koine -σσ- (θάλαττα / θάλασσα)",
        key_side="σσ", marked="ττ", pooling="substring", metric=True,
        marked_pattern="ττ", marked_stop=_TT_STOP,
        evidence="A 0.068/1k -> B 0.485/1k (A/B 0.14): EXCESS, B is 7.1x A — this "
                 "rule runs opposite to the others",
        caveat="Marked side is the LATER Atticist restoration, not Thucydides' "
               "usage. 64% of B's raw ττ tokens are proper nouns "
               "(Οὐιττιγίς 116 = the Gothic king Witigis, Ῥήγιον, Σίττας), and "
               "POOLING them is merge-harmless but visible: Οὐιττιγίς pools to "
               "Οὐισσιγίς, which is no word. The proper-noun filter is "
               "load-bearing for this rule, not a nicety.",
    ),
    Rule(
        name="rr",
        summary="older Attic -ρσ- for later -ρρ- (θάρσος / θάρρος)",
        key_side="ρρ", marked="ρσ", pooling="lexemes", metric=False,
        lexemes=_RR_LEXEMES,
        evidence="metric disabled",
        caveat="Polluted on all sides: Thucydides' ρρ is Ἀρράβαιον (proper) and "
               "ἐπερρώσθησαν (prefix assimilation), his ρσ is χερσίν (< χείρ, "
               "inflection) and Περσῶν. Pooling only.",
    ),
)

BY_NAME = {r.name: r for r in RULES}
DEFAULT = tuple(r.name for r in RULES)
METRIC_RULES = tuple(r.name for r in RULES if r.metric)


def names(arg: str | list[str] | tuple | None) -> tuple[str, ...]:
    """Parse a rule selection: None/"all"/"" -> every rule, "none" -> ().

    Unknown names are dropped rather than raising: the selection arrives from a
    query string, and a typo there must not 500 the endpoint. It is a filter,
    so silently doing less is the safe failure — but the caller is expected to
    report what it actually used (`selected_rules`) rather than echo the ask.
    """
    if arg is None:
        return DEFAULT
    if isinstance(arg, (list, tuple)):
        want = [str(a).strip() for a in arg]
    else:
        s = str(arg).strip()
        if s.lower() in ("", "all"):
            return DEFAULT
        if s.lower() in ("none", "-"):
            return ()
        want = [p.strip() for p in s.split(",")]
    return tuple(w for w in want if w in BY_NAME)


def unify(form: str, rules: tuple[str, ...] | list[str] = DEFAULT) -> str:
    """Pooling key of a NORMALISED form. One direction only, as documented.

    `rules` selects which correspondences to collapse. With `()` the form is
    returned unchanged, so the caller can turn the whole layer off and get the
    exact old behaviour.
    """
    out = form
    for name in rules:
        r = BY_NAME.get(name)
        if r is None:
            continue
        if r.pooling == "prefix":
            if out.startswith(r.marked_pattern) and not any(
                    out.startswith(s) for s in r.marked_stop):
                out = r.key_side + out[len(r.marked_pattern):]
        elif r.pooling == "substring":
            if r.marked_pattern in out and not any(
                    out.startswith(s) for s in r.marked_stop):
                out = out.replace(r.marked_pattern, r.key_side)
        else:  # lexemes
            for marked, koine in r.lexemes:
                if out.startswith(marked):
                    out = koine + out[len(marked):]
                    break
    return out


def marked_rules(form: str, rules: tuple[str, ...] | list[str] = DEFAULT) -> list[str]:
    """Which rules consider this normalised form to wear the MARKED spelling.

    Used for the per-row breakdown: it answers "which spelling choice is this
    token making", not "what word is it". A form may be marked for more than
    one rule (e.g. `ξυμβαίνοντα` is not, but `προσγιγνόμενα` is marked for gign).
    """
    return [n for n in rules
            if (r := BY_NAME.get(n)) is not None and r.applies_to(form)]


def describe(rules: tuple[str, ...] | list[str] = DEFAULT) -> list[dict]:
    """Machine-readable rule descriptions, so the UI never restates them."""
    return [{"name": r.name, "summary": r.summary, "key_side": r.key_side,
             "marked": r.marked, "metric": r.metric, "evidence": r.evidence,
             "caveat": r.caveat}
            for r in RULES if r.name in rules]

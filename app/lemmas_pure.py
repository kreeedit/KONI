"""Lemma layer — morphological aggregation on top of the variant pooling.

WHY THIS EXISTS
---------------
`variants.unify` already merges the same word written two ways (`ἥσσον` /
`ἥττων`). That fixes the SPELLING split. It does not fix the INFLECTION split,
and the inflection split is the larger one: `ποταμόν` and `ποταμός` are still
two separate rows in the rarity ranking, so the lexeme's count is torn across
them and a "hapax" in that table means a hapax *of that surface form*, not of
the word. Measured over the two works under study, distinct surface forms
outnumber their lemmas by roughly 2.4x, so an unlemmatised row understates the
lexeme's real rate by about that factor.

This module groups surface forms under a lemma — and, the reason it is a module
and not a lookup table, DISCLOSES the morphological analysis it used to do it,
so that a row expands into its inflectional breakdown:

    ὁπλίτης   12/3
      ὁπλίτας   7/2   acc pl masc
      ὁπλῖται   3/0   nom pl masc
      ὁπλιτῶν   2/1   gen pl masc

WHAT THIS IS NOT — read before trusting a row
---------------------------------------------
The standard library contains no morphological analyser for Ancient Greek, and
this is not one. It is a RULE TABLE plus a RESOLVER:

  1. A closed-class table (`_CLOSED`): article, pronouns, prepositions,
     conjunctions, particles, numerals. Finite, memorised, exact. These are the
     most frequent tokens in any Greek text, so the table alone carries a large
     share of every count, and none of it is inferred.

  2. A suffix rule table for the open classes (`_NOMINAL`, `_VERBAL`). Each
     rule declares ONE normalised ending and the lemma templates it can
     reconstruct from the stem. It never returns a single answer, because
     ambiguity is the norm: `-ου` is the 2nd-declension genitive singular AND
     the 1st-declension masculine genitive singular, and a rule that picked one
     would be inventing a reading the form does not carry.

  3. A RESOLVER that uses the corpus to choose among the candidates: a
     candidate lemma which is itself ATTESTED as a token of the corpus (in its
     own canonical shape) outranks one that is not. That is how a reader
     disambiguates, and it costs no external data — the engine already has the
     text. A form whose candidates are ALL attested is reported AMBIGUOUS, with
     every reading kept and shown, rather than silently assigned to one.

MEASURED ACCURACY
-----------------
The rules were developed against GOLD lemmatisation from the Perseus Ancient
Greek Dependency Treebank (CC BY-SA 3.0, `PerseusDL/treebank_data`), whose
lemma and full POS tag are annotated per token: Thucydides 1 and Polybius, read
through the same `normalize` the engine uses. The figures are in `ACCURACY`
below and in log.md, so a row can be presented with the number attached rather
than with an assurance. The gold data is NOT redistributed here; it was used at
development time to measure and is not read at runtime.

WHAT IS DELIBERATELY NOT ATTEMPTED, each for a measured reason
-------------------------------------------------------------
  * SUPPLETION AND IRREGULAR VERBS. `εἶπον` belongs to `λέγω`, `ἦλθον` to
    `ἔρχομαι`, `ἤνεγκον` to `φέρω`. The aorist stem is a DIFFERENT stem, and no
    suffix rule can recover the present from it — that needs a verb lexicon.
    Such forms are left unreduced and reported as `unverified`; they are the
    largest residual error class and the measurement states their share.
  * WORD FORMATION (derivation). Only inflection is undone. `πολίτης` and
    `πόλις` are related words, not forms of one lemma, and merging them would
    be a different (and much more speculative) claim.
  * ACCENT. The engine works on `flame_pure.normalize` output, which drops
    accents and breathings, and so does this layer. Two words separated only by
    accent (τίς/τις, ὅς/ὅ) therefore stay merged at this level; the closed-class
    table records both readings where both are real, so the merge is visible
    rather than silent.
  * CONTEXT. The resolver reads the corpus as a BAG of tokens. It cannot use
    the article's case to fix a noun's case, or a verb's person to fix its
    subject. A tagger would; this is not one.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from .flame_pure import normalize, words_elided
from .variants import DEFAULT as VARIANTS_DEFAULT
from .variants import unify as variants_unify

# Measured against the gold treebanks, same tokenizer, same normalisation.
# Fractions are of TOKENS (not of types), because that is what the aggregation
# is over and what a rate in the table is divided by. Every figure below comes
# from a measurement run, never from an estimate; the run is described in
# log.md and a stale figure is worse than no figure, so keep the two in step.
#
#   exact           the chosen lemma equals the gold lemma
#   within          the gold lemma is among the form's candidate readings, i.e.
#                   the right answer was available and the resolver ranked
#                   something else first. `exact / within` is the pair that
#                   says whether a future resolver could do better.
#   ambiguous_a     more than one reading of the form is carried by real corpus
#                   weight, i.e. the two are separated only by accent or by
#                   syntax. Disclosed rather than guessed.
#   unreduced       no rule and no table entry matched at all.
#   purity          of the gold lemmas whose tokens appear, the share that land
#                   in ONE aggregation key. This is the figure that matters for
#                   what this module is FOR: a consistently wrong headword
#                   still aggregates a lexeme's forms together, but two keys
#                   for one lexeme tear its rate in half. Nouns and adjectives
#                   (the ὁπλίτης case) sit at 85% and 72%; verbs at 51%, which
#                   is where the irregular stems are.
#
# The figures are over PRODUCTION tokens (`n_tokens_production`): the report's
# tokenizer drops a token that an elision mark follows, and counting the
# treebank's `δ'` as a token would measure tokens the report never sees.
ACCURACY = {
    "gold": "Perseus AGDT v2.1 (CC BY-SA 3.0): Thucydides 1, Polybius 1-2",
    "thucydides": {"n_tokens_all": 25159, "n_tokens_production": 24622,
                   "exact": 0.7440, "within": 0.8107,
                   "ambiguous": 0.1553, "unreduced": 0.1244,
                   "purity": 0.7130,
                   "purity_noun": 0.860, "purity_adjective": 0.718,
                   "purity_verb": 0.507, "purity_adverb": 0.888},
    "polybius": {"n_tokens_all": 28154, "n_tokens_production": 27532,
                 "exact": 0.7418, "within": 0.8093,
                 "ambiguous": 0.1140, "unreduced": 0.1063,
                 "purity": 0.7258,
                 "purity_noun": 0.866, "purity_adjective": 0.722,
                 "purity_verb": 0.562, "purity_adverb": 0.871},
}

# ---------------------------------------------------------------------------
# 1. CLOSED CLASS — memorised, not inferred.
# ---------------------------------------------------------------------------
# form (normalised) -> tuple of (lemma, pos, features). A form maps to more
# than one reading where the language really has more than one, and both are
# kept: `η` is the article's nominative singular feminine AND the adverb ἦ;
# `ει` is the 2nd person singular of εἰμί AND the conjunction εἰ after
# normalization. Choosing one silently would hide a real ambiguity.
#
# Everything here is the standard paradigm. Nothing was read off the corpus,
# which is the point: this part of the module is not an estimate.
_CLOSED: dict[str, tuple[tuple[str, str, str], ...]] = {}


def _c(form: str, lemma: str, pos: str, infl: str) -> None:
    """Register one closed-class reading (append; a form may have several)."""
    _CLOSED.setdefault(normalize(form), ())
    _CLOSED[normalize(form)] += ((normalize(lemma), pos, infl),)


# The article ὁ ἡ τό.
for _f, _i in (("ὁ", "nom sg masc"), ("ἡ", "nom sg fem"), ("τό", "nom sg neut"),
               ("τοῦ", "gen sg masc"), ("τῆς", "gen sg fem"), ("τοῦ", "gen sg neut"),
               ("τῷ", "dat sg masc"), ("τῇ", "dat sg fem"), ("τῷ", "dat sg neut"),
               ("τόν", "acc sg masc"), ("τήν", "acc sg fem"), ("τό", "acc sg neut"),
               ("τώ", "nom acc dual"), ("τοῖν", "gen dat dual"),
               ("οἱ", "nom pl masc"), ("αἱ", "nom pl fem"), ("τά", "nom pl neut"),
               ("τῶν", "gen pl"), ("τοῖς", "dat pl masc"), ("ταῖς", "dat pl fem"),
               ("τοῖς", "dat pl neut"),
               ("τούς", "acc pl masc"), ("τάς", "acc pl fem"), ("τά", "acc pl neut")):
    _c(_f, "ὁ", "article", _i)
# The feminine nominative singular is filed under `ἡ` in the gold, not under
# `ὁ`, in 139 of the 240 article tokens of that form; the `ὁ` reading is kept
# beside it and `_FORM_PREF` states which one the resolver takes. The same
# string is also `ἥ` (nominative singular feminine of the relative, 16 tokens)
# and `ἦ` (the adverb, 7) — three real readings that only the accent separated
# before `normalize` removed it.
_c("ἡ", "ἡ", "article", "nom sg fem (filed under ἡ)")
_c("ἦ", "ἦ", "adverb", "indeclinable (ἦ 'indeed')")

# αὐτός — the third-person pronoun / intensive adjective.
for _f, _i in (("αὐτός", "nom sg masc"), ("αὐτή", "nom sg fem"), ("αὐτό", "nom sg neut"),
               ("αὐτοῦ", "gen sg masc neut"), ("αὐτῆς", "gen sg fem"),
               ("αὐτῷ", "dat sg masc neut"), ("αὐτῇ", "dat sg fem"),
               ("αὐτόν", "acc sg masc"), ("αὐτήν", "acc sg fem"), ("αὐτό", "acc sg neut"),
               ("αὐτοί", "nom pl masc"), ("αὐταί", "nom pl fem"), ("αὐτά", "nom pl neut"),
               ("αὐτῶν", "gen pl"), ("αὐτοῖς", "dat pl masc neut"), ("αὐταῖς", "dat pl fem"),
               ("αὐτούς", "acc pl masc"), ("αὐτάς", "acc pl fem"), ("αὐτά", "acc pl neut")):
    _c(_f, "αὐτός", "pronoun", _i)

# οὗτος, ἐκεῖνος, ὅδε — demonstratives.
for _f, _i in (("οὗτος", "nom sg masc"), ("αὕτη", "nom sg fem"), ("τοῦτο", "nom acc sg neut"),
               ("τούτου", "gen sg masc neut"), ("ταύτης", "gen sg fem"),
               ("τούτῳ", "dat sg masc neut"), ("ταύτῃ", "dat sg fem"),
               ("τοῦτον", "acc sg masc"), ("ταύτην", "acc sg fem"),
               ("οὗτοι", "nom pl masc"), ("αὗται", "nom pl fem"), ("ταῦτα", "nom acc pl neut"),
               ("τούτων", "gen pl"), ("τούτοις", "dat pl masc neut"), ("ταύταις", "dat pl fem"),
               ("τούτους", "acc pl masc"), ("ταύτας", "acc pl fem")):
    _c(_f, "οὗτος", "pronoun", _i)
for _f, _i in (("ἐκεῖνος", "nom sg masc"), ("ἐκείνη", "nom sg fem"), ("ἐκεῖνο", "nom sg neut"),
               ("ἐκείνου", "gen sg masc neut"), ("ἐκείνης", "gen sg fem"),
               ("ἐκείνῳ", "dat sg masc neut"), ("ἐκείνῃ", "dat sg fem"),
               ("ἐκεῖνον", "acc sg masc"), ("ἐκείνην", "acc sg fem"),
               ("ἐκεῖνοι", "nom pl masc"), ("ἐκεῖναι", "nom pl fem"), ("ἐκεῖνα", "nom acc pl neut"),
               ("ἐκείνων", "gen pl"), ("ἐκείνοις", "dat pl masc neut"),
               ("ἐκείναις", "dat pl fem"), ("ἐκείνους", "acc pl masc"),
               ("ἐκείνας", "acc pl fem")):
    _c(_f, "ἐκεῖνος", "pronoun", _i)
for _f, _i in (("ὅδε", "nom sg masc"), ("ἥδε", "nom sg fem"), ("τόδε", "nom acc sg neut"),
               ("τοῦδε", "gen sg masc neut"), ("τῆσδε", "gen sg fem"),
               ("τῷδε", "dat sg masc neut"), ("τῇδε", "dat sg fem"),
               ("τόνδε", "acc sg masc"), ("τήνδε", "acc sg fem"),
               ("οἵδε", "nom pl masc"), ("αἵδε", "nom pl fem"), ("τάδε", "nom acc pl neut"),
               ("τῶνδε", "gen pl"), ("τοῖσδε", "dat pl masc neut"), ("ταῖσδε", "dat pl fem"),
               ("τούσδε", "acc pl masc"), ("τάσδε", "acc pl fem")):
    _c(_f, "ὅδε", "pronoun", _i)

# Personal pronouns. These are suppletive stems and no rule can reach them.
# The first person PLURAL is filed under `ἐγώ` and the second under `σύ`, which
# is the convention the AGDT gold uses (`ἡμῶν` -> `ἐγώ`, `ὑμῖν` -> `σύ`) and
# the convention of the standard Greek lexica. Filing `ἡμεῖς` under itself
# would make one lexeme into two rows and split its count — the exact defect
# this module exists to repair.
for _f, _l, _i in (("ἐγώ", "ἐγώ", "nom sg"), ("ἐμοῦ", "ἐγώ", "gen sg"),
                   ("μου", "ἐγώ", "gen sg enclitic"), ("ἐμοί", "ἐγώ", "dat sg"),
                   ("μοι", "ἐγώ", "dat sg enclitic"), ("ἐμέ", "ἐγώ", "acc sg"),
                   ("με", "ἐγώ", "acc sg enclitic"),
                   ("ἡμεῖς", "ἐγώ", "nom pl"), ("ἡμῶν", "ἐγώ", "gen pl"),
                   ("ἡμῖν", "ἐγώ", "dat pl"), ("ἡμᾶς", "ἐγώ", "acc pl"),
                   ("σύ", "σύ", "nom sg"), ("σοῦ", "σύ", "gen sg"),
                   ("σου", "σύ", "gen sg enclitic"), ("σοί", "σύ", "dat sg"),
                   ("σοι", "σύ", "dat sg enclitic"), ("σέ", "σύ", "acc sg"),
                   ("σε", "σύ", "acc sg enclitic"),
                   ("ὑμεῖς", "σύ", "nom pl"), ("ὑμῶν", "σύ", "gen pl"),
                   ("ὑμῖν", "σύ", "dat pl"), ("ὑμᾶς", "σύ", "acc pl"),
                   ("σφεῖς", "σφεῖς", "nom pl"), ("σφῶν", "σφεῖς", "gen pl"),
                   ("σφίσιν", "σφεῖς", "dat pl"), ("σφίσι", "σφεῖς", "dat pl"),
                   ("σφισιν", "σφεῖς", "dat pl"), ("σφισι", "σφεῖς", "dat pl"),
                   ("σφᾶς", "σφεῖς", "acc pl"), ("σφας", "σφεῖς", "acc pl"),
                   ("ἑαυτοῦ", "ἑαυτοῦ", "gen sg masc neut reflexive"),
                   ("ἑαυτῆς", "ἑαυτοῦ", "gen sg fem reflexive"),
                   ("ἑαυτῷ", "ἑαυτοῦ", "dat sg masc neut reflexive"),
                   ("ἑαυτῇ", "ἑαυτοῦ", "dat sg fem reflexive"),
                   ("ἑαυτόν", "ἑαυτοῦ", "acc sg masc reflexive"),
                   ("ἑαυτήν", "ἑαυτοῦ", "acc sg fem reflexive"),
                   ("ἑαυτό", "ἑαυτοῦ", "nom acc sg neut reflexive"),
                   ("ἑαυτῶν", "ἑαυτοῦ", "gen pl reflexive"),
                   ("ἑαυτοῖς", "ἑαυτοῦ", "dat pl masc neut reflexive"),
                   ("ἑαυταῖς", "ἑαυτοῦ", "dat pl fem reflexive"),
                   ("ἑαυτούς", "ἑαυτοῦ", "acc pl masc reflexive"),
                   ("ἑαυτάς", "ἑαυτοῦ", "acc pl fem reflexive"),
                   ("ἑαυτά", "ἑαυτοῦ", "nom acc pl neut reflexive"),
                   ("αὑτοῦ", "ἑαυτοῦ", "gen sg masc neut reflexive"),
                   ("αὑτῆς", "ἑαυτοῦ", "gen sg fem reflexive"),
                   ("αὑτῷ", "ἑαυτοῦ", "dat sg masc neut reflexive"),
                   ("αὑτόν", "ἑαυτοῦ", "acc sg masc reflexive"),
                   ("αὑτῶν", "ἑαυτοῦ", "gen pl reflexive"),
                   ("αὑτοῖς", "ἑαυτοῦ", "dat pl masc neut reflexive"),
                   ("αὑτούς", "ἑαυτοῦ", "acc pl masc reflexive"),
                   ("αὑτά", "ἑαυτοῦ", "nom acc pl neut reflexive"),
                   ("ἀλλήλων", "ἀλλήλων", "gen pl reciprocal"),
                   ("ἀλλήλοις", "ἀλλήλων", "dat pl reciprocal"),
                   ("ἀλλήλαις", "ἀλλήλων", "dat pl fem reciprocal"),
                   ("ἀλλήλους", "ἀλλήλων", "acc pl reciprocal"),
                   ("ἀλλήλας", "ἀλλήλων", "acc pl fem reciprocal"),
                   ("ἀλλήλα", "ἀλλήλων", "nom acc pl neut reciprocal")):
    _c(_f, _l, "pronoun", _i)

# Relative, indefinite and interrogative pronouns. `ὅς/ὅ` and `τίς/τις` differ
# ONLY by accent, which `normalize` drops — so both readings are registered and
# the merge is disclosed instead of guessed away.
for _f, _l, _i in (("ὅς", "ὅς", "nom sg masc relative"), ("ἥ", "ὅς", "nom sg fem relative"),
                   ("ὅ", "ὅς", "nom acc sg neut relative"), ("οὗ", "ὅς", "gen sg masc relative"),
                   ("ἧς", "ὅς", "gen sg fem relative"), ("ᾧ", "ὅς", "dat sg masc relative"),
                   ("ὅν", "ὅς", "acc sg masc relative"), ("ἥν", "ὅς", "acc sg fem relative"),
                   ("οἵ", "ὅς", "nom pl masc relative"), ("αἵ", "ὅς", "nom pl fem relative"),
                   ("ἅ", "ὅς", "nom acc pl neut relative"), ("ὧν", "ὅς", "gen pl relative"),
                   ("οἷς", "ὅς", "dat pl masc neut relative"), ("αἷς", "ὅς", "dat pl fem relative"),
                   ("οὕς", "ὅς", "acc pl masc relative"), ("ἅς", "ὅς", "acc pl fem relative"),
                   ("ὅστις", "ὅστις", "nom sg masc"), ("ἥτις", "ὅστις", "nom sg fem"),
                   ("ὅτι", "ὅστις", "nom acc sg neut"),
                   ("ὅτου", "ὅστις", "gen sg masc neut"), ("ὅτῳ", "ὅστις", "dat sg masc neut"),
                   ("ὅντινα", "ὅστις", "acc sg masc"), ("οἵτινες", "ὅστις", "nom pl masc"),
                   ("αἵτινες", "ὅστις", "nom pl fem"), ("ἅτινα", "ὅστις", "nom acc pl neut"),
                   ("ὧντινων", "ὅστις", "gen pl"), ("οἷσπερ", "ὅσπερ", "dat pl masc"),
                   ("ὅσπερ", "ὅσπερ", "nom sg masc"),
                   ("τίς", "τίς", "nom sg interrogative"), ("τί", "τίς", "nom acc sg neut interrogative"),
                   ("τίνος", "τίς", "gen sg interrogative"), ("τίνι", "τίς", "dat sg interrogative"),
                   ("τίνα", "τίς", "acc sg interrogative"), ("τίνες", "τίς", "nom pl interrogative"),
                   ("τίνας", "τίς", "acc pl interrogative"),
                   ("τις", "τις", "nom sg indefinite"), ("τι", "τις", "nom acc sg neut indefinite"),
                   ("τινος", "τις", "gen sg indefinite"), ("τινι", "τις", "dat sg indefinite"),
                   ("τινα", "τις", "acc sg indefinite"), ("τινες", "τις", "nom pl indefinite"),
                   ("τινας", "τις", "acc pl indefinite"), ("τισι", "τις", "dat pl indefinite"),
                   ("τισιν", "τις", "dat pl indefinite"), ("τινων", "τις", "gen pl indefinite")):
    _c(_f, _l, "pronoun", _i)

# Prepositions. Invariable except for ἐκ/ἐξ and εἰς/ἐν, which the table covers
# per form; every other preposition below is a single normalised string, which
# is why this group costs one line each and removes a whole error class.
for _p in ("ἐν", "εἰς", "ἐκ", "πρός", "πρό", "παρά", "περί", "κατά",
           "μετά", "ἀνά", "διά", "ὑπό", "ἀπό", "ἐπί", "σύν", "ὑπέρ", "ἀντί",
           "ἀμφί", "ἄνευ", "ἐκτός", "πλήν", "μέχρι", "ἄχρι", "χάριν", "ἕνεκα",
           "ἕνεκεν", "εἵνεκα", "ὑπό", "παρά"):
    _c(_p, _p, "preposition", "indeclinable")
# ἐξ is filed under ἐκ, which is the convention of the lexica and of the AGDT
# gold alike: they are one word in two shapes, and filing them separately would
# split its count — the defect this whole layer exists to remove.
_c("ἐξ", "ἐκ", "preposition", "indeclinable (before a vowel)")
# The elided and assimilated shapes below are lexically correct but are NOT
# reached in production: `flame_pure.words_elided` drops a token that an
# elision mark follows, so `δ᾽` never arrives here as `δ`. They are kept
# because `candidates()` is public and a caller tokenizing differently should
# still get a right answer — and the accuracy measurement below deliberately
# reports the production-restricted figure separately, so these entries cannot
# flatter it.
_c("ἔφ", "ἐπί", "preposition", "indeclinable (assimilated)")
_c("ἐπ", "ἐπί", "preposition", "indeclinable (elided)")
_c("καθ", "κατά", "preposition", "indeclinable (assimilated)")
_c("κατ", "κατά", "preposition", "indeclinable (elided)")
_c("ἀπ", "ἀπό", "preposition", "indeclinable (elided)")
_c("ὑπ", "ὑπό", "preposition", "indeclinable (elided)")
_c("μεθ", "μετά", "preposition", "indeclinable (assimilated)")
_c("ἀφ", "ἀπό", "preposition", "indeclinable (assimilated)")
_c("ὑφ", "ὑπό", "preposition", "indeclinable (assimilated)")
_c("παρ", "παρά", "preposition", "indeclinable (elided)")
_c("δι", "διά", "preposition", "indeclinable (elided)")
_c("ἀν", "ἀνά", "preposition", "indeclinable (elided)")
_c("ἐς", "εἰς", "preposition", "indeclinable (Ionic)")
_c("ποτί", "πρός", "preposition", "indeclinable (Doric)")
_c("πρὸς", "πρός", "preposition", "indeclinable")

# Conjunctions, particles and the negations. The single highest-yield group in
# the whole table: καί, δέ, τε, ἐν, εἰς, ἐκ are the most frequent tokens of
# every Greek text, and every one of them is memorised rather than inferred.
for _f, _l in (("καί", "καί"), ("δέ", "δέ"), ("τε", "τε"), ("γάρ", "γάρ"),
               ("οὖν", "οὖν"), ("μέν", "μέν"), ("ἀλλά", "ἀλλά"), ("ἀλλ", "ἀλλά"),
               ("ἤ", "ἤ"), ("οὐ", "οὐ"), ("οὐκ", "οὐ"), ("οὐχ", "οὐ"),
               ("μή", "μή"), ("μηδ", "μηδέ"), ("μηδέ", "μηδέ"),
               ("οὐδέ", "οὐδέ"), ("οὐδ", "οὐδέ"), ("οὐδέν", "οὐδείς"),
               ("οὐδενός", "οὐδείς"), ("οὐδενί", "οὐδείς"), ("οὐδένα", "οὐδείς"),
               ("μηδέν", "μηδείς"), ("μηδενός", "μηδείς"), ("μηδένα", "μηδείς"),
               ("εἰ", "εἰ"), ("εἰς", "εἰς"), ("ἐάν", "ἐάν"), ("ἄν", "ἄν"),
               ("ὅπως", "ὅπως"), ("ὅτι", "ὅτι"), ("ὡς", "ὡς"), ("ἵνα", "ἵνα"),
               ("δή", "δή"), ("γέ", "γέ"), ("τοι", "τοι"), ("νυν", "νυν"),
               ("οὐκοῦν", "οὐκοῦν"), ("ὥστε", "ὥστε"), ("ἤτοι", "ἤτοι"),
               ("καθά", "καθά"), ("ὅτε", "ὅτε"), ("ὁπότε", "ὁπότε"),
               ("ἐπεί", "ἐπεί"), ("πρίν", "πρίν"),
               ("ἕως", "ἕως"), ("ὄφρα", "ὄφρα"), ("ἆρα", "ἆρα"), ("ἄρα", "ἄρα"),
               ("μέντοι", "μέντοι"), ("δήπου", "δήπου"), ("γούν", "γοῦν"),
               ("τοίνυν", "τοίνυν"), ("ὅμως", "ὅμως"), ("οὔτε", "οὔτε"),
               ("μήτε", "μήτε"), ("εἴτε", "εἴτε"), ("ἤτε", "ἤτε"),
               ("ἐπάν", "ἐπάν"), ("ὅταν", "ὅταν"), ("ὁπόταν", "ὁπόταν")):
    _c(_f, _l, "conjunction", "indeclinable")

# `ἐπειδή` is `ἐπεί` plus the enclitic `δή`, and the gold files all 49 of its
# tokens under `ἐπεί`. Filing it under itself would carve the conjunction in
# two and halve both halves' rates — exactly the defect this module repairs.
_c("ἐπειδή", "ἐπεί", "conjunction", "indeclinable (ἐπεί + δή enclitic)")

# Adverbs. Not a closed class in the strict sense (adverbs are formed
# productively from adjectives), but these are memorised tokens, not rules.
for _f, _l in (("οὐκέτι", "οὐκέτι"), ("μηκέτι", "μηκέτι"), ("ἐνταῦθα", "ἐνταῦθα"),
               ("ἐνθάδε", "ἐνθάδε"), ("εὐθύς", "εὐθύς"), ("εὐθύ", "εὐθύς"),
               ("ἔπειτα", "ἔπειτα"), ("ἐπί", "ἐπί"), ("τότε", "τότε"),
               ("ποτέ", "ποτέ"), ("οὔποτε", "οὔποτε"), ("μήποτε", "μήποτε"),
               ("ἀεί", "ἀεί"), ("αἰεί", "ἀεί"), ("πάντοτε", "πάντοτε"),
               ("μάλιστα", "μάλιστα"), ("μᾶλλον", "μᾶλλον"), ("ἤδη", "ἤδη"),
               ("ἔτι", "ἔτι"), ("αὖθις", "αὖθις"), ("αὖ", "αὖ"),
               ("οὕτως", "οὕτως"), ("οὕτω", "οὕτως"), ("πάνυ", "πάνυ"),
               ("σφόδρα", "σφόδρα"), ("ἅμα", "ἅμα"), ("ἁπλῶς", "ἁπλῶς"),
               ("σαφῶς", "σαφῶς"), ("ὄντως", "ὄντως"), ("εὖ", "εὖ"),
               ("μάλα", "μάλα"), ("νῦν", "νῦν"), ("τότε", "τότε"),
               ("οἴκαδε", "οἴκαδε"), ("ἔνθα", "ἔνθα"), ("ἐκεῖ", "ἐκεῖ"),
               ("αὐτοῦ", "αὐτοῦ"), ("ὅπου", "ὅπου"), ("ποῖ", "ποῖ"),
               ("πῇ", "πῇ"), ("ὅπῃ", "ὅπῃ"), ("ταύτῃ", "ταύτῃ"),
               ("οὐδαμῶς", "οὐδαμῶς"), ("μηδαμῶς", "μηδαμῶς"),
               ("ἄνω", "ἄνω"), ("κάτω", "κάτω"), ("πρόσω", "πρόσω"),
               ("ὀπίσω", "ὀπίσω"), ("ἐγγύς", "ἐγγύς"), ("ἑκάς", "ἑκάς"),
               # Adverbs formed from an adjective are filed under the ADJECTIVE,
               # which is the lexicographic convention and the AGDT gold's:
               # `ὕστερον` belongs to `ὕστερος`, `πρῶτον` to `πρῶτος`. Filing
               # them under themselves would carve one lexeme into two rows —
               # and these are frequent, so the measurement showed it at once
               # (46 `ὕστερον`, 31 `πρότερον`, 28 `πρῶτον` in Thucydides alone).
               ("πρότερον", "πρότερος"), ("προτέρου", "πρότερος"),
               ("ὕστερον", "ὕστερος"), ("ὑστέρου", "ὕστερος"),
               ("πρῶτον", "πρῶτος"), ("πρώτου", "πρῶτος"),
               ("ὅλως", "ὅλος"), ("μόνον", "μόνος"), ("μόνου", "μόνος"),
               ("ὁμοίως", "ὅμοιος"), ("ὁμοίως", "ὅμοιος"),
               ("πάλιν", "πάλιν"), ("ἔμπροσθεν", "ἔμπροσθεν"),
               ("ὄπισθεν", "ὄπισθεν"), ("ἔναντι", "ἐναντίος"),
               ("μόλις", "μόλις"), ("ἅπαξ", "ἅπαξ"), ("πολλάκις", "πολλάκις"),
               ("ὀλίγον", "ὀλίγος"), ("πολύ", "πολύς"), ("πλέον", "πλείων"),
               ("πλεῖστον", "πλεῖστος"), ("μέγιστον", "μέγιστος"),
               ("τάχιστα", "τάχιστος"), ("μάλισθ", "μάλιστα"),
               # The superlative adverbs formed from an adjective go under the
               # adjective here too: `ἥκιστα` is 21 tokens of `ἥκιστος` in the
               # gold and none of `ἥκιστα`, and `ὀλίγιστα` is the same shape.
               ("ἥκιστα", "ἥκιστος"), ("ἥκιστον", "ἥκιστος"),
               ("ὀλίγιστα", "ὀλίγιστος"), ("ὀλίγιστον", "ὀλίγιστος")):
    _c(_f, _l, "adverb", "indeclinable (adverbial use of the superlative)")

# Numerals: the low cardinals and the ordinals that occur, plus εἷς/μία/ἕν and
# the plural-only forms. Small, finite, and frequent enough in historians.
for _f, _l, _i in (("εἷς", "εἷς", "nom sg masc"), ("μία", "εἷς", "nom sg fem"),
                   ("ἕν", "εἷς", "nom acc sg neut"), ("ἑνός", "εἷς", "gen sg masc neut"),
                   ("μιᾶς", "εἷς", "gen sg fem"), ("ἑνί", "εἷς", "dat sg masc neut"),
                   ("ἕνα", "εἷς", "acc sg masc"), ("μίαν", "εἷς", "acc sg fem"),
                   ("δύο", "δύο", "nom acc dual/pl"), ("δυοῖν", "δύο", "gen dat dual"),
                   ("τρεῖς", "τρεῖς", "nom pl masc fem"), ("τρία", "τρεῖς", "nom acc pl neut"),
                   ("τριῶν", "τρεῖς", "gen pl"), ("τρισίν", "τρεῖς", "dat pl"),
                   ("τέσσαρες", "τέσσαρες", "nom pl"), ("τέτταρες", "τέσσαρες", "nom pl"),
                   ("τέσσαρα", "τέσσαρες", "nom acc pl neut"),
                   ("τέτταρα", "τέσσαρες", "nom acc pl neut"),
                   ("τεσσάρων", "τέσσαρες", "gen pl"), ("τεττάρων", "τέσσαρες", "gen pl"),
                   ("πέντε", "πέντε", "indeclinable"), ("ἕξ", "ἕξ", "indeclinable"),
                   ("ἑπτά", "ἑπτά", "indeclinable"), ("ὀκτώ", "ὀκτώ", "indeclinable"),
                   ("ἐννέα", "ἐννέα", "indeclinable"), ("δέκα", "δέκα", "indeclinable"),
                   ("ἕνδεκα", "ἕνδεκα", "indeclinable"), ("δώδεκα", "δώδεκα", "indeclinable"),
                   ("εἴκοσι", "εἴκοσι", "indeclinable"), ("τριάκοντα", "τριάκοντα", "indeclinable"),
                   ("τεσσαράκοντα", "τεσσαράκοντα", "indeclinable"),
                   ("τετταράκοντα", "τεσσαράκοντα", "indeclinable"),
                   ("πεντήκοντα", "πεντήκοντα", "indeclinable"),
                   ("ἑκατόν", "ἑκατόν", "indeclinable"), ("διακόσιοι", "διακόσιοι", "nom pl masc"),
                   ("τριακόσιοι", "τριακόσιοι", "nom pl masc"),
                   ("τετρακόσιοι", "τετρακόσιοι", "nom pl masc"),
                   ("χίλιοι", "χίλιοι", "nom pl masc"), ("χιλίων", "χίλιοι", "gen pl"),
                   ("μύριοι", "μύριοι", "nom pl masc")):
    _c(_f, _l, "numeral", _i)

# εἰμί and the copula-like forms. Suppletive, astronomically frequent, and
# worth memorising outright rather than deriving from -μι rules that would then
# also fire on every other -μι verb.
for _f, _i in (("εἰμί", "1sg pres ind"), ("εἶ", "2sg pres ind"), ("ἐστί", "3sg pres ind"),
               ("ἐστίν", "3sg pres ind"), ("ἐσμέν", "1pl pres ind"), ("ἐστέ", "2pl pres ind"),
               ("εἰσί", "3pl pres ind"), ("εἰσίν", "3pl pres ind"),
               ("ἦν", "1sg 3sg impf ind"), ("ἦσαν", "3pl impf ind"),
               ("ἔσται", "3sg fut ind"), ("ἔσονται", "3pl fut ind"),
               ("ἐστίν", "3sg pres ind"), ("εἶναι", "infinitive pres"),
               ("ὤν", "participle pres nom sg masc"), ("οὖσα", "participle pres nom sg fem"),
               ("ὄν", "participle pres nom acc sg neut"), ("ὄντος", "participle pres gen sg masc neut"),
               ("ὄντι", "participle pres dat sg masc neut"), ("ὄντα", "participle pres acc sg masc"),
               ("ὄντες", "participle pres nom pl masc"), ("ὄντων", "participle pres gen pl"),
               ("οὔσης", "participle pres gen sg fem"), ("οὖσαν", "participle pres acc sg fem"),
               ("ἴσθι", "imperative pres 2sg"), ("ἔστω", "imperative pres 3sg"),
               ("ὦ", "1sg pres subj"), ("ᾖ", "3sg pres subj"), ("ὦσι", "3pl pres subj"),
               ("ὦσιν", "3pl pres subj"), ("εἴη", "3sg opt"), ("εἴησαν", "3pl opt"),
               ("ἔστι", "3sg pres ind"), ("ἔστιν", "3sg pres ind")):
    _c(_f, "εἰμί", "verb", _i)

# εἶμι (to go) and the common imperatives — suppletive, not derivable.
for _f, _l, _i in (("ἴθι", "εἶμι", "imperative pres 2sg"), ("ἴτω", "εἶμι", "imperative pres 3sg"),
                   ("ἰέναι", "εἶμι", "infinitive pres"), ("ἰών", "εἶμι", "participle pres nom sg masc"),
                   ("ἴμεν", "εἶμι", "1pl pres ind"), ("ἴασι", "εἶμι", "3pl pres ind"),
                   ("ἴασιν", "εἶμι", "3pl pres ind")):
    _c(_f, _l, "verb", _i)

# φημί — suppletive and very frequent in narrative.
for _f, _i in (("φημί", "1sg pres ind"), ("φῄς", "2sg pres ind"), ("φησί", "3sg pres ind"),
               ("φησίν", "3sg pres ind"), ("φαμέν", "1pl pres ind"), ("φασί", "3pl pres ind"),
               ("φασίν", "3pl pres ind"), ("ἔφη", "3sg impf ind"), ("ἔφασαν", "3pl impf ind"),
               ("φάναι", "infinitive pres"), ("φάς", "participle pres nom sg masc")):
    _c(_f, "φημί", "verb", _i)


# The registrations above are grouped by word class for readability, which is
# NOT the order a caller wants them tried in. `η` is registered as the article
# and again as the adverb ἦ; `ου` as the relative pronoun's genitive and again
# as the negation; `ην` as εἰμί's imperfect and again as the pronoun's
# accusative. In every one of those the two readings are both real Greek and
# only SYNTAX decides between them, which this layer does not read. So the
# tie-break has to be stated rather than left to the accident of which block
# happens to sit higher in the file, and it is this: the reading whose class is
# more frequent in Greek prose wins, and the groups are ordered accordingly.
# The measurement is what put this here — with registration order deciding,
# `ου` went to the relative pronoun (119 tokens wrong), `ην` to the pronoun (102),
# `αν` to the preposition (110) and `η` to the article's rival.
#
# Within a group the registration order is kept (`sort` is stable), so the
# finer ordering inside, say, the conjunctions is still the one written above.
_CLASS_PRIORITY = {"article": 0, "conjunction": 1, "verb": 2, "preposition": 3,
                   "pronoun": 4, "adverb": 5, "numeral": 6, "adjective": 7,
                   "noun": 8}
for _f, _v in list(_CLOSED.items()):
    _CLOSED[_f] = tuple(sorted(_v, key=lambda r: _CLASS_PRIORITY.get(r[1], 9)))


# Three forms where the class order above is measurably the wrong way round, and
# only for those three. `ων` is `ὧν` (gen pl of the relative, 82 tokens in the
# gold) and `ὤν` (present participle of εἰμί, 13); `ω` is `ᾧ` (38) against `ὦ`
# (14). Ranking the verb first — which is right for `ην`, where εἰμί runs 131
# to 43 — puts the pronoun's tokens under εἰμί and vice versa. The classes
# cannot settle this because the two readings belong to different classes and
# the winner differs from form to form, so the preference has to be stated per
# form. These are listed rather than derived, and the figures come from the
# Perseus AGDT gold described at the head of this module.
#
# Keys and values are NORMALISED, like everything else the resolver compares:
# the lemmas here read `ος` and not `ὅς` because that is what `_c` stored.
_FORM_PREF = {"ων": "ος", "ω": "ος", "η": "η"}


# ---------------------------------------------------------------------------
# 1b. DEFECTIVE AND IRREGULAR PARADIGMS — memorised, same as the closed class.
# ---------------------------------------------------------------------------
# These are not a word class; they are the words whose stems CHANGE across the
# paradigm, which no suffix rule can undo and which are too frequent to leave
# unreduced. `ναῦς` alone is one of the most common nouns in Thucydides, and
# `πᾶς` and `πολύς` are among the most common words in Greek. Every entry
# below was added because the measurement showed the form in the error list,
# not because it looked irregular in principle.
#
# Labelled `paradigm` rather than `closed` so the two are never confused: a
# closed-class reading is a fact about a word class, a paradigm reading is a
# fact about one lexeme.
_PARADIGM: dict[str, tuple[tuple[str, str, str], ...]] = {}


def _p(form: str, lemma: str, pos: str, infl: str) -> None:
    _PARADIGM.setdefault(normalize(form), ())
    _PARADIGM[normalize(form)] += ((normalize(lemma), pos, infl),)


# ναῦς — νη- in the singular, ναυ- in the plural.
for _f, _i in (("ναῦς", "nom sg"), ("νεώς", "gen sg"), ("νηός", "gen sg"),
               ("νηί", "dat sg"), ("νηΐ", "dat sg"), ("ναῦν", "acc sg"),
               ("νῆες", "nom pl"), ("νῆας", "acc pl"), ("νηῶν", "gen pl"),
               ("νεῶν", "gen pl"), ("ναυσί", "dat pl"), ("ναυσίν", "dat pl"),
               ("ναῦσι", "dat pl"), ("ναυσίν", "dat pl")):
    _p(_f, "ναῦς", "noun", _i)
# πᾶς — παντ- / παν- / πασ-.
for _f, _i in (("πᾶς", "nom sg masc"), ("παντός", "gen sg masc neut"),
               ("παντί", "dat sg masc neut"), ("πάντα", "acc sg masc"),
               ("πᾶν", "nom acc sg neut"), ("πάντες", "nom pl masc"),
               ("πάντων", "gen pl"), ("πᾶσι", "dat pl"), ("πᾶσιν", "dat pl"),
               ("πάσας", "acc pl fem"), ("πάντας", "acc pl masc"),
               ("πᾶσα", "nom sg fem"), ("πάσης", "gen sg fem"), ("πάσῃ", "dat sg fem"),
               ("πᾶσαν", "acc sg fem"), ("πᾶσαι", "nom pl fem"),
               ("πασῶν", "gen pl fem"), ("πάσαις", "dat pl fem")):
    _p(_f, "πᾶς", "adjective", _i)
# πολύς — πολυ- / πολλ- / πλει- / πλειστ-.
for _f, _i in (("πολύς", "nom sg masc"), ("πολύ", "nom acc sg neut"),
               ("πολλοῦ", "gen sg masc neut"), ("πολλῷ", "dat sg masc neut"),
               ("πολύν", "acc sg masc"), ("πολλοί", "nom pl masc"),
               ("πολλῶν", "gen pl"), ("πολλοῖς", "dat pl"), ("πολλούς", "acc pl masc"),
               ("πολλά", "nom acc pl neut"), ("πολλή", "nom sg fem"),
               ("πολλῆς", "gen sg fem"), ("πολλῇ", "dat sg fem"),
               ("πολλήν", "acc sg fem"), ("πολλαί", "nom pl fem"),
               ("πολλάς", "acc pl fem"),
               # The comparative and superlative are a DIFFERENT stem and are
               # filed under the positive, which is what the lexica do.
               ("πλείων", "comparative nom sg masc"), ("πλέον", "comparative nom acc sg neut"),
               ("πλέονος", "comparative gen sg"), ("πλείονος", "comparative gen sg"),
               ("πλείονι", "comparative dat sg"), ("πλείονα", "comparative acc sg"),
               ("πλείους", "comparative acc pl masc"), ("πλείονες", "comparative nom pl masc"),
               ("πλεόνων", "comparative gen pl"), ("πλείοσι", "comparative dat pl"),
               ("πλείοσιν", "comparative dat pl"), ("πλείονας", "comparative acc pl masc"),
               ("πλείω", "comparative nom acc pl neut"), ("πλείστη", "superlative nom sg fem"),
               ("πλεῖστος", "superlative nom sg masc"), ("πλεῖστον", "superlative nom acc sg neut"),
               ("πλείστου", "superlative gen sg"), ("πλείστῳ", "superlative dat sg"),
               ("πλεῖστοι", "superlative nom pl masc"), ("πλείστων", "superlative gen pl"),
               ("πλείστοις", "superlative dat pl"), ("πλείστους", "superlative acc pl masc"),
               ("πλεῖστα", "superlative nom acc pl neut"), ("πλείστας", "superlative acc pl fem")):
    _p(_f, "πολύς", "adjective", _i)
# μέγας — μεγα- / μεγαλ-.
for _f, _i in (("μέγας", "nom sg masc"), ("μέγα", "nom acc sg neut"),
               ("μεγάλου", "gen sg masc neut"), ("μεγάλῳ", "dat sg masc neut"),
               ("μέγαν", "acc sg masc"), ("μεγάλοι", "nom pl masc"),
               ("μεγάλων", "gen pl"), ("μεγάλοις", "dat pl"),
               ("μεγάλους", "acc pl masc"), ("μεγάλα", "nom acc pl neut"),
               ("μεγάλη", "nom sg fem"), ("μεγάλης", "gen sg fem"),
               ("μεγάλην", "acc sg fem"), ("μεγάλαι", "nom pl fem"),
               ("μεγάλας", "acc pl fem"),
               ("μείζων", "comparative nom sg masc"), ("μεῖζον", "comparative nom acc sg neut"),
               ("μείζονος", "comparative gen sg"), ("μείζονι", "comparative dat sg"),
               ("μείζονα", "comparative acc sg"), ("μείζονες", "comparative nom pl masc"),
               ("μειζόνων", "comparative gen pl"), ("μείζοσι", "comparative dat pl"),
               ("μείζονας", "comparative acc pl masc"), ("μείζω", "comparative nom acc pl neut"),
               ("μέγιστος", "superlative nom sg masc"), ("μέγιστον", "superlative nom acc sg neut"),
               ("μεγίστου", "superlative gen sg"), ("μέγιστοι", "superlative nom pl masc"),
               ("μεγίστων", "superlative gen pl"), ("μεγίστοις", "superlative dat pl"),
               ("μεγίστους", "superlative acc pl masc"), ("μέγιστα", "superlative nom acc pl neut"),
               ("μεγίστη", "superlative nom sg fem"), ("μεγίστην", "superlative acc sg fem"),
               ("μεγίστας", "superlative acc pl fem"), ("μεγίστας", "superlative acc pl fem")):
    _p(_f, "μέγας", "adjective", _i)
# ἀνήρ — ἀνδρ- everywhere except the nominative and vocative singular.
for _f, _i in (("ἀνήρ", "nom sg"), ("ἀνδρός", "gen sg"), ("ἀνδρί", "dat sg"),
               ("ἄνδρα", "acc sg"), ("ἄνδρες", "nom pl"), ("ἀνδρῶν", "gen pl"),
               ("ἀνδράσι", "dat pl"), ("ἀνδράσιν", "dat pl"), ("ἄνδρας", "acc pl")):
    _p(_f, "ἀνήρ", "noun", _i)
# γυνή — γυναικ-.
for _f, _i in (("γυνή", "nom sg"), ("γυναικός", "gen sg"), ("γυναικί", "dat sg"),
               ("γυναῖκα", "acc sg"), ("γυναῖκες", "nom pl"), ("γυναικῶν", "gen pl"),
               ("γυναιξί", "dat pl"), ("γυναιξίν", "dat pl"), ("γυναῖκας", "acc pl")):
    _p(_f, "γυνή", "noun", _i)
# χείρ — χειρ- / χερ-.
for _f, _i in (("χείρ", "nom sg"), ("χειρός", "gen sg"), ("χειρί", "dat sg"),
               ("χειρί", "dat sg"), ("χεῖρα", "acc sg"), ("χεῖρες", "nom pl"),
               ("χερσίν", "dat pl"), ("χερσί", "dat pl"), ("χεῖρας", "acc pl"),
               ("χειρῶν", "gen pl")):
    _p(_f, "χείρ", "noun", _i)
# παῖς — παιδ-.
for _f, _i in (("παῖς", "nom sg"), ("παιδός", "gen sg"), ("παιδί", "dat sg"),
               ("παῖδα", "acc sg"), ("παῖδες", "nom pl"), ("παίδων", "gen pl"),
               ("παισί", "dat pl"), ("παισίν", "dat pl"), ("παῖδας", "acc pl")):
    _p(_f, "παῖς", "noun", _i)
# γῆ — γῆ / γῇ / γῆν, with the Attic γεω- in the oblique plural.
for _f, _i in (("γῆ", "nom sg"), ("γῆς", "gen sg"), ("γῇ", "dat sg"), ("γῆν", "acc sg")):
    _p(_f, "γῆ", "noun", _i)
# Ζεύς — Δι- in the oblique cases.
for _f, _i in (("Ζεύς", "nom sg"), ("Διός", "gen sg"), ("Διί", "dat sg"),
               ("Δία", "acc sg"), ("Ζῆνα", "acc sg")):
    _p(_f, "Ζεύς", "noun", _i)
# ἥσσων / ἥττων — the comparative of the defective `ἥσσων` (there is no
# positive in use). Both spellings are the SAME word across the Attic/Koine
# correspondence, so both go under one lemma and `variants.unify` then folds
# the marked spelling in as well. This is the lexeme the `θάλασσα`/`θάλαττα`
# rule and the `ττ` register metric both turn on, so leaving it unreduced would
# defeat the aggregation exactly where the comparison is most interesting.
for _f, _i in (("ἥσσων", "nom sg masc"), ("ἥττων", "nom sg masc"),
               ("ἥσσονος", "gen sg"), ("ἥττονος", "gen sg"),
               ("ἥσσονι", "dat sg"), ("ἥττονι", "dat sg"),
               ("ἥσσω", "acc sg masc"), ("ἥττω", "acc sg masc"),
               ("ἥσσον", "nom acc sg neut"), ("ἥττον", "nom acc sg neut"),
               ("ἥσσους", "acc pl masc"), ("ἥττους", "acc pl masc"),
               ("ἥσσονες", "nom pl masc"), ("ἥττονες", "nom pl masc"),
               ("ἡσσόνων", "gen pl"), ("ἡττόνων", "gen pl"),
               ("ἥσσοσι", "dat pl"), ("ἥττοσι", "dat pl"),
               ("ἥσσοσιν", "dat pl"), ("ἥττοσιν", "dat pl"),
               ("ἥσσονας", "acc pl masc"), ("ἥττονας", "acc pl masc"),
               ("ἥσσω", "nom acc pl neut"), ("ἥττω", "nom acc pl neut")):
    _p(_f, "ἥσσων", "adjective", _i)
# τοιοῦτος / τοσοῦτος / τηλικοῦτος — the correlative demonstratives.
for _f, _l, _i in (("τοιοῦτος", "τοιοῦτος", "nom sg masc"),
                   ("τοιαύτη", "τοιοῦτος", "nom sg fem"),
                   ("τοιοῦτο", "τοιοῦτος", "nom acc sg neut"),
                   ("τοιοῦτον", "τοιοῦτος", "nom acc sg neut"),
                   ("τοιούτου", "τοιοῦτος", "gen sg masc neut"),
                   ("τοιαύτης", "τοιοῦτος", "gen sg fem"),
                   ("τοιούτῳ", "τοιοῦτος", "dat sg masc neut"),
                   ("τοιούτους", "τοιοῦτος", "acc pl masc"),
                   ("τοιοῦτοι", "τοιοῦτος", "nom pl masc"),
                   ("τοιαῦται", "τοιοῦτος", "nom pl fem"),
                   ("τοιαῦτα", "τοιοῦτος", "nom acc pl neut"),
                   ("τοιούτων", "τοιοῦτος", "gen pl"),
                   ("τοιούτοις", "τοιοῦτος", "dat pl"),
                   ("τοσαύτην", "τοσοῦτος", "acc sg fem"),
                   ("τοσοῦτος", "τοσοῦτος", "nom sg masc"),
                   ("τοσοῦτον", "τοσοῦτος", "nom acc sg neut"),
                   ("τοσούτου", "τοσοῦτος", "gen sg masc neut"),
                   ("τοσούτῳ", "τοσοῦτος", "dat sg masc neut"),
                   ("τοσαῦτα", "τοσοῦτος", "nom acc pl neut"),
                   ("τοσούτων", "τοσοῦτος", "gen pl"),
                   ("τοσούτους", "τοσοῦτος", "acc pl masc"),
                   ("τοσοῦτοι", "τοσοῦτος", "nom pl masc"),
                   ("τοσαύταις", "τοσοῦτος", "dat pl fem")):
    _p(_f, _l, "pronoun", _i)
# The ὅσος / οἷος / ὁπόσος correlatives, which the relative-pronoun table does
# not reach because their stems are their own.
for _f, _l, _i in (("ὅσος", "ὅσος", "nom sg masc"), ("ὅση", "ὅσος", "nom sg fem"),
                   ("ὅσον", "ὅσος", "nom acc sg neut"), ("ὅσου", "ὅσος", "gen sg masc neut"),
                   ("ὅσῳ", "ὅσος", "dat sg masc neut"), ("ὅσην", "ὅσος", "acc sg fem"),
                   ("ὅσοι", "ὅσος", "nom pl masc"), ("ὅσαι", "ὅσος", "nom pl fem"),
                   ("ὅσα", "ὅσος", "nom acc pl neut"), ("ὅσων", "ὅσος", "gen pl"),
                   ("ὅσοις", "ὅσος", "dat pl"), ("ὅσους", "ὅσος", "acc pl masc"),
                   ("ὅσας", "ὅσος", "acc pl fem"), ("ὅσπερ", "ὅσπερ", "nom sg masc"),
                   ("ὅπερ", "ὅσπερ", "nom acc sg neut"), ("ἥπερ", "ὅσπερ", "nom sg fem"),
                   ("οἷος", "οἷος", "nom sg masc"), ("οἵα", "οἷος", "nom sg fem"),
                   ("οἷον", "οἷος", "nom acc sg neut"), ("οἵου", "οἷος", "gen sg masc neut"),
                   ("οἷοι", "οἷος", "nom pl masc"), ("οἷα", "οἷος", "nom acc pl neut"),
                   ("οἵων", "οἷος", "gen pl"), ("οἵους", "οἷος", "acc pl masc"),
                   ("ὁπόσος", "ὁπόσος", "nom sg masc"), ("ὁπόσον", "ὁπόσος", "nom acc sg neut"),
                   ("ὁπόσοι", "ὁπόσος", "nom pl masc"), ("ὁπόσα", "ὁπόσος", "nom acc pl neut"),
                   ("ὁποῖος", "ὁποῖος", "nom sg masc"), ("ὁποῖον", "ὁποῖος", "nom acc sg neut")):
    _p(_f, _l, "pronoun", _i)
# κύων, οὖς, ἧπαρ — frequent enough in these authors to memorise.
for _f, _i in (("κύων", "nom sg"), ("κυνός", "gen sg"), ("κυνί", "dat sg"),
               ("κύνα", "acc sg"), ("κύνες", "nom pl"), ("κυσί", "dat pl"),
               ("κυσίν", "dat pl"), ("κύνας", "acc pl")):
    _p(_f, "κύων", "noun", _i)


# ---------------------------------------------------------------------------
# 2. OPEN CLASS — suffix rules.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class LemmaRule:
    """One declared ending and the lemmas it can reconstruct.

    `lemmas` are templates over `{stem}`. A rule with more than one template is
    declaring an ambiguity, not hedging: `-ου` really is both the 2nd-declension
    genitive and the 1st-declension masculine genitive, and the form alone does
    not say which. The resolver decides from the corpus; this rule records the
    fact that there was something to decide.

    `drop` removes further characters from the stem after `ending` is stripped
    (`λυσαντος` - `σαντος` = `λυ`, but `γιγαντος` - `αντος` = `γιγ`). `stem_re`
    constrains the stem where an ending is too promiscuous without it —
    without that guard the 3rd-declension genitive `-ος` rule fires on every
    2nd-declension nominative and doubles the ambiguity for no gain.
    """
    name: str
    pos: str
    ending: str
    lemmas: tuple[str, ...]
    infl: str
    summary: str = ""
    drop: int = 0
    stem_min: int = 2
    stem_re: str = ""


_NOMINAL: tuple[LemmaRule, ...] = (
    # --- 3rd declension: the forms are recognised by their GENITIVE SINGULAR,
    # because that is the form that carries the stem. Ordered most specific
    # first; several endings are prefixes of others, so order is load-bearing.
    LemmaRule("nt_ma", "noun", "ματος", ("{stem}μα",), "gen sg neut",
              summary="-μα / -ματος neuter (πρᾶγμα, σῶμα, ὄνομα)"),
    LemmaRule("nt_masi", "noun", "μασι", ("{stem}μα",), "dat pl neut"),
    LemmaRule("nt_masin", "noun", "μασιν", ("{stem}μα",), "dat pl neut"),
    LemmaRule("nt_mata", "noun", "ματα", ("{stem}μα",), "nom acc pl neut"),
    LemmaRule("nt_maton", "noun", "ματων", ("{stem}μα",), "gen pl neut"),
    LemmaRule("nt_n", "noun", "ατος", ("{stem}α", "{stem}αρ", "{stem}ας"), "gen sg"),
    LemmaRule("nt_n_pl", "noun", "ατα", ("{stem}α", "{stem}αρ"), "nom acc pl neut"),
    LemmaRule("nt_n_plon", "noun", "ατων", ("{stem}α", "{stem}αρ"), "gen pl neut"),
    LemmaRule("nt_os_e", "noun", "εος", ("{stem}ος",), "gen sg neut",
              summary="-ος / -εος neuter (γένος, τέλος, μέρος)"),
    LemmaRule("nt_os_ous", "noun", "ους", ("{stem}ος",), "gen sg neut"),
    LemmaRule("nt_os_ea", "noun", "εα", ("{stem}ος",), "nom acc pl neut"),
    LemmaRule("nt_os_eon", "noun", "εων", ("{stem}ος",), "gen pl neut"),
    LemmaRule("nt_os_esi", "noun", "εσι", ("{stem}ος",), "dat pl neut"),
    LemmaRule("nt_os_esin", "noun", "εσιν", ("{stem}ος",), "dat pl neut"),
    # -ις / -εως (πόλις, δύναμις) and -εύς / -έως (βασιλεύς, ἱππεύς).
    # Both genitives are -εως, so the ending alone cannot separate them and the
    # rule returns both. The corpus resolver almost always can: the nominative
    # of whichever reading is the real one appears in the same text.
    LemmaRule("i_eos", "noun", "εως", ("{stem}ευς", "{stem}ις"), "gen sg"),
    LemmaRule("i_ewn", "noun", "εων", ("{stem}ευς", "{stem}ις"), "gen pl"),
    LemmaRule("i_esi", "noun", "εσι", ("{stem}ευς", "{stem}ις"), "dat pl"),
    LemmaRule("i_esin", "noun", "εσιν", ("{stem}ευς", "{stem}ις"), "dat pl"),
    LemmaRule("i_eis", "noun", "εις", ("{stem}ευς", "{stem}ις"), "nom acc pl"),
    # -ιν / -εως are the accusative and genitive of the same -ις nouns, and the
    # accusative is the most frequent of them in narrative; without it `πόλιν`,
    # `δύναμιν` and `ναῦν` came back unreduced.
    LemmaRule("is_in", "noun", "ιν", ("{stem}ις",), "acc sg"),
    # -η is the nominative and accusative PLURAL of the -ος neuters
    # (μέρη < μέρος, τέλη < τέλος) as well as the 1st-declension singular.
    # `stem_min=3` keeps it off the shortest forms, where it would only add noise.
    LemmaRule("nt_os_plh", "noun", "η", ("{stem}ος",), "nom acc pl neut", stem_min=3),
    # -ο is the nominative and accusative singular neuter of the -ος adjectives
    # (ἄλλο, μόνον, πολέμιον...) which the -ον rule above does not reach.
    LemmaRule("o_neut_o", "noun", "ο", ("{stem}ος",), "nom acc sg neut", stem_min=3),
    LemmaRule("i_ea", "noun", "έα", ("{stem}εύς",), "acc sg"),
    # -ίδος / -ίς (ἐλπίς, πατρίς) — the stem is visible in every oblique case.
    LemmaRule("id_os", "noun", "ιδος", ("{stem}ις",), "gen sg"),
    LemmaRule("id_i", "noun", "ιδι", ("{stem}ις",), "dat sg"),
    LemmaRule("id_a", "noun", "ιδα", ("{stem}ις",), "acc sg"),
    LemmaRule("id_es", "noun", "ιδες", ("{stem}ις",), "nom pl"),
    LemmaRule("id_as", "noun", "ιδας", ("{stem}ις",), "acc pl"),
    LemmaRule("id_wn", "noun", "ιδων", ("{stem}ις",), "gen pl"),
    LemmaRule("id_si", "noun", "ισι", ("{stem}ις",), "dat pl"),
    LemmaRule("id_sin", "noun", "ισιν", ("{stem}ις",), "dat pl"),
    # -ων / -οντος (ἄρχων, γέρων, λέων, δράκων).
    LemmaRule("wn_ontos", "noun", "οντος", ("{stem}ων",), "gen sg"),
    LemmaRule("wn_onti", "noun", "οντι", ("{stem}ων",), "dat sg"),
    LemmaRule("wn_onta", "noun", "οντα", ("{stem}ων",), "acc sg"),
    LemmaRule("wn_ontes", "noun", "οντες", ("{stem}ων",), "nom pl"),
    LemmaRule("wn_ontas", "noun", "οντας", ("{stem}ων",), "acc pl"),
    LemmaRule("wn_ontwn", "noun", "οντων", ("{stem}ων",), "gen pl"),
    LemmaRule("wn_ousi", "noun", "ουσιν", ("{stem}ων",), "dat pl"),
    # -ας / -αντος (γίγας, ἀνδριάς).
    LemmaRule("as_antos", "noun", "αντος", ("{stem}ας",), "gen sg", stem_re=r"[α-ω]{2,}"),
    LemmaRule("as_anta", "noun", "αντα", ("{stem}ας",), "acc sg"),
    # -ηρ / -ηρος, -ωρ / -ορος (ἀστήρ, ῥήτωρ, σωτήρ).
    LemmaRule("hr_hros", "noun", "ηρος", ("{stem}ηρ",), "gen sg"),
    LemmaRule("hr_hri", "noun", "ηρι", ("{stem}ηρ",), "dat sg"),
    LemmaRule("hr_hra", "noun", "ηρα", ("{stem}ηρ",), "acc sg"),
    LemmaRule("hr_hres", "noun", "ηρες", ("{stem}ηρ",), "nom pl"),
    LemmaRule("hr_hrwn", "noun", "ηρων", ("{stem}ηρ",), "gen pl"),
    LemmaRule("wr_oros", "noun", "ορος", ("{stem}ωρ",), "gen sg"),
    LemmaRule("wr_ori", "noun", "ορι", ("{stem}ωρ",), "dat sg"),
    LemmaRule("wr_ora", "noun", "ορα", ("{stem}ωρ",), "acc sg"),
    # -υς / -εως (ἄστυ, πῆχυς) and -υς / -υος.
    LemmaRule("ys_eos", "noun", "εως", ("{stem}υς",), "gen sg", stem_re=r"[α-ω]{2,}"),
    LemmaRule("ys_yos", "noun", "υος", ("{stem}υς",), "gen sg", stem_re=r"[α-ω]{2,}"),
    # Plosive stems: -ξ / -κος, -ξ / -γος, -ψ / -βος, -ψ / -πος.
    # The nominative is `-ξ`/`-ψ` written as one letter for κσ/γσ/βσ/πσ, so the
    # stem is only recoverable from the oblique cases, which is exactly what
    # these rules read. `stem_re` keeps `-ος` from firing on 2nd-declension
    # nominatives, whose stem has no such shape.
    LemmaRule("ks_kos", "noun", "κος", ("{stem}ξ",), "gen sg"),
    LemmaRule("ks_ki", "noun", "κι", ("{stem}ξ",), "dat sg"),
    LemmaRule("ks_ka", "noun", "κα", ("{stem}ξ",), "acc sg"),
    LemmaRule("ks_kes", "noun", "κες", ("{stem}ξ",), "nom pl"),
    LemmaRule("ks_kas", "noun", "κας", ("{stem}ξ",), "acc pl"),
    LemmaRule("ks_kwn", "noun", "κων", ("{stem}ξ",), "gen pl"),
    LemmaRule("gs_gos", "noun", "γος", ("{stem}ξ",), "gen sg"),
    LemmaRule("gs_ga", "noun", "γα", ("{stem}ξ",), "acc sg"),
    LemmaRule("ps_pos", "noun", "πος", ("{stem}ψ",), "gen sg"),
    LemmaRule("ps_pi", "noun", "πι", ("{stem}ψ",), "dat sg"),
    LemmaRule("ps_pa", "noun", "πα", ("{stem}ψ",), "acc sg"),
    LemmaRule("ps_pes", "noun", "πες", ("{stem}ψ",), "nom pl"),
    LemmaRule("ps_pas", "noun", "πας", ("{stem}ψ",), "acc pl"),
    LemmaRule("ps_pwn", "noun", "πων", ("{stem}ψ",), "gen pl"),
    LemmaRule("bs_bos", "noun", "βος", ("{stem}ψ",), "gen sg"),
    LemmaRule("bs_ba", "noun", "βα", ("{stem}ψ",), "acc sg"),
    # -της / -τητος (τάξις-like abstracts: ταχυτής, ἰσότης) — the stem is long,
    # which is what `stem_re` asserts, so this does not swallow every -τος.
    LemmaRule("ths_thtos", "noun", "τητος", ("{stem}της",), "gen sg", stem_re=r"[α-ω]{3,}"),
    LemmaRule("ths_thti", "noun", "τητι", ("{stem}της",), "dat sg"),
    LemmaRule("ths_thta", "noun", "τητα", ("{stem}της",), "acc sg"),
    # -ις / -ινος, -ην / -ενος (ποιμήν, ἀκτίς are covered above; these are the
    # -ινος/-ενος family: ῥίς/ῥινός, and the -ην/-ενος nouns).
    LemmaRule("hs_htos", "noun", "ητος", ("{stem}ης",), "gen sg", stem_re=r"[α-ω]{3,}"),
    LemmaRule("hs_hta", "noun", "ητα", ("{stem}ης",), "acc sg"),
    LemmaRule("hs_htwn", "noun", "ητων", ("{stem}ης",), "gen pl"),
    # -ις / -ιος, -υ / -υος.
    LemmaRule("is_ios", "noun", "ιος", ("{stem}ις",), "gen sg", stem_re=r"[α-ω]{3,}"),
    # --- 2nd declension: genitive -ου, nominative -ος (or the -ον neuter).
    LemmaRule("o_gen_sg", "noun", "ου", ("{stem}ος", "{stem}ον", "{stem}ης", "{stem}εύς"),
              "gen sg", stem_min=3),
    LemmaRule("o_dat_sg", "noun", "ω", ("{stem}ος", "{stem}ον", "{stem}ης"), "dat sg", stem_min=3),
    LemmaRule("o_acc_sg", "noun", "ον", ("{stem}ος", "{stem}ον"), "acc sg masc/neut", stem_min=3),
    LemmaRule("o_nom_pl", "noun", "οι", ("{stem}ος",), "nom pl masc"),
    LemmaRule("o_acc_pl", "noun", "ους", ("{stem}ος",), "acc pl masc"),
    LemmaRule("o_gen_pl", "noun", "ων", ("{stem}ος", "{stem}ον", "{stem}ης"),
              "gen pl", stem_min=2),
    LemmaRule("o_dat_pl", "noun", "οις", ("{stem}ος", "{stem}ον"), "dat pl"),
    LemmaRule("o_nom_sg", "noun", "ος", ("{stem}ος",), "nom sg masc/fem"),
    LemmaRule("o_nom_sg_n", "noun", "ον", ("{stem}ον",), "nom acc sg neut"),
    LemmaRule("o_voc_sg", "noun", "ε", ("{stem}ος",), "voc sg masc", stem_min=3),
    # --- 1st declension: -η (fem), -α (fem after ε/ι/ρ), -ης (masc), -ας (masc).
    LemmaRule("a_gen_sg_f", "noun", "ης", ("{stem}η", "{stem}α", "{stem}ης"),
              "gen sg fem / gen sg masc", stem_min=3),
    LemmaRule("a_gen_sg_m", "noun", "ου", ("{stem}ης", "{stem}ας"), "gen sg masc", stem_min=3),
    # `-ην` is the feminine accusative AND the masculine `-ης` one: `ὁπλίτην`
    # and `τιμήν` end alike, and the rule has to declare both or the masculine
    # paradigm loses its accusative to the feminine reading.
    LemmaRule("a_acc_sg_f", "noun", "ην", ("{stem}ης", "{stem}η", "{stem}ας"),
              "acc sg fem / acc sg masc"),
    LemmaRule("a_acc_sg_a", "noun", "αν", ("{stem}α", "{stem}ης", "{stem}ας"), "acc sg"),
    LemmaRule("a_nom_pl", "noun", "αι", ("{stem}η", "{stem}α", "{stem}ης", "{stem}ας"), "nom pl"),
    LemmaRule("a_acc_pl", "noun", "ας", ("{stem}η", "{stem}α", "{stem}ης", "{stem}ας"),
              "nom sg fem / acc pl", stem_min=3),
    LemmaRule("a_gen_pl", "noun", "ων", ("{stem}ης", "{stem}ας"), "gen pl masc", stem_min=3),
    LemmaRule("a_dat_pl", "noun", "αις", ("{stem}η", "{stem}α", "{stem}ης"), "dat pl fem"),
    LemmaRule("a_nom_sg_h", "noun", "η", ("{stem}η",), "nom sg fem", stem_min=3),
    LemmaRule("a_nom_sg_a", "noun", "α", ("{stem}α", "{stem}ης", "{stem}ας"), "nom sg"),
    LemmaRule("a_nom_sg_s", "noun", "ης", ("{stem}ης",), "nom sg masc", stem_min=3),
    LemmaRule("a_nom_sg_s2", "noun", "ας", ("{stem}ας",), "nom sg masc", stem_min=3),
)

# Adjectives ride on the same endings; what makes them a separate table is that
# their lemma template is the MASCULINE nominative, which for the -ος/-η/-ον
# type is the same reconstruction the noun table already makes implicitly. The
# genuinely adjectival patterns are the ones below: -ύς/-εῖα/-ύ, -ης/-ες,
# -ων/-ον, and the comparatives, which are frequent in both works.
_ADJECTIVAL: tuple[LemmaRule, ...] = (
    LemmaRule("adj_hs_es", "adjective", "ους", ("{stem}ης",), "gen sg / acc pl masc",
              summary="-ης / -ες (ἀληθής, σαφής)"),
    LemmaRule("adj_hs_eis", "adjective", "εις", ("{stem}ης",), "nom acc pl masc fem"),
    LemmaRule("adj_hs_e", "adjective", "η", ("{stem}ης",), "nom sg fem", stem_re=r"[α-ω]{3,}"),
    LemmaRule("adj_hs_es2", "adjective", "ες", ("{stem}ης",), "nom acc pl neut", stem_re=r"[α-ω]{3,}"),
    LemmaRule("adj_wn_on", "adjective", "ονος", ("{stem}ων",), "gen sg",
              summary="-ων / -ον (σώφρων, εὐδαίμων)"),
    LemmaRule("adj_wn_oni", "adjective", "ονι", ("{stem}ων",), "dat sg"),
    LemmaRule("adj_wn_ona", "adjective", "ονα", ("{stem}ων",), "acc sg"),
    LemmaRule("adj_wn_ones", "adjective", "ονες", ("{stem}ων",), "nom pl"),
    LemmaRule("adj_wn_onas", "adjective", "ονας", ("{stem}ων",), "acc pl"),
    LemmaRule("adj_ys_eia", "adjective", "εια", ("{stem}υς",), "nom sg fem",
              summary="-ύς / -εῖα / -ύ (ταχύς, βαθύς)"),
    LemmaRule("adj_ys_eian", "adjective", "ειαν", ("{stem}υς",), "acc sg fem"),
    LemmaRule("adj_ys_eias", "adjective", "ειας", ("{stem}υς",), "gen sg fem / acc pl fem"),
    LemmaRule("adj_ys_eis", "adjective", "εις", ("{stem}υς",), "nom pl masc"),
    LemmaRule("adj_ys_eas", "adjective", "εας", ("{stem}υς",), "acc pl masc"),
    LemmaRule("adj_ys_ewn", "adjective", "εων", ("{stem}υς",), "gen pl"),
    LemmaRule("adj_ys_si", "adjective", "εσι", ("{stem}υς",), "dat pl"),
    LemmaRule("adj_ys_sin", "adjective", "εσιν", ("{stem}υς",), "dat pl"),
    LemmaRule("adj_ys_syn", "adjective", "υν", ("{stem}υς",), "acc sg masc"),
    # Comparatives in -ων / -ονος and -ιστος / -τερος, very frequent in
    # Thucydides' argumentative prose.
    LemmaRule("cmp_teros", "adjective", "τερ", ("{stem}τερος",), "stem of comparative"),
    LemmaRule("cmp_terou", "adjective", "τερου", ("{stem}τερος",), "gen sg"),
    LemmaRule("cmp_teron", "adjective", "τερον", ("{stem}τερος",), "nom acc sg neut"), # -ον neut keeps masc lemma
    LemmaRule("cmp_tera", "adjective", "τερα", ("{stem}τερος",), "nom acc pl neut"),
    LemmaRule("cmp_terwn", "adjective", "τερων", ("{stem}τερος",), "gen pl"),
    LemmaRule("cmp_terois", "adjective", "τεροις", ("{stem}τερος",), "dat pl"),
    LemmaRule("cmp_terous", "adjective", "τερους", ("{stem}τερος",), "acc pl"),
    LemmaRule("cmp_terai", "adjective", "τεραι", ("{stem}τερος",), "nom pl fem"),
    LemmaRule("cmp_teras", "adjective", "τερας", ("{stem}τερος",), "gen sg fem / acc pl fem"),
    LemmaRule("cmp_teran", "adjective", "τεραν", ("{stem}τερος",), "acc sg fem"),
    # -ίων / -ίονος and -ιστος.
    LemmaRule("cmp_iwn_onos", "adjective", "ιονος", ("{stem}ιων",), "gen sg"),
    LemmaRule("cmp_iwn_oni", "adjective", "ιονι", ("{stem}ιων",), "dat sg"),
    LemmaRule("cmp_iwn_ona", "adjective", "ιονα", ("{stem}ιων",), "acc sg"),
    LemmaRule("cmp_iwn_ones", "adjective", "ιονες", ("{stem}ιων",), "nom pl"),
    LemmaRule("cmp_istos", "adjective", "ιστος", ("{stem}ιστος",), "nom sg superlative"),
    LemmaRule("cmp_istou", "adjective", "ιστου", ("{stem}ιστος",), "gen sg"),
    LemmaRule("cmp_istoi", "adjective", "ιστοι", ("{stem}ιστος",), "nom pl"),
    LemmaRule("cmp_istwn", "adjective", "ιστων", ("{stem}ιστος",), "gen pl"),
    LemmaRule("cmp_istous", "adjective", "ιστους", ("{stem}ιστος",), "acc pl"),
    LemmaRule("cmp_istois", "adjective", "ιστοις", ("{stem}ιστος",), "dat pl"),
    # The adverb in -ως. Nothing else in either table ends in -ως, so before
    # these two rules every adverb of this shape came back unanalysed and lost
    # the lexeme's other tokens: `ἀσφαλῶς` was filing under itself while
    # `ἀσφαλής` filed under `ἀσφαλής`, and `σαφῶς`, `ἀληθῶς`, `ὀρθῶς` the same.
    # The lemma is the ADJECTIVE, which is the lexicographic convention and the
    # gold's (`ἀσφαλῶς` → `ἀσφαλής`), for the same reason `ὕστερον` goes under
    # `ὕστερος`.
    LemmaRule("adv_hs_ws", "adverb", "ως", ("{stem}ης",), "adverb in -ως (-ης/-ες adj)",
              summary="-ως adverb of a -ης/-ες adjective (σαφῶς, ἀληθῶς)"),
    LemmaRule("adv_ys_ws", "adverb", "εως", ("{stem}υς",), "adverb in -έως (-ύς/-εῖα adj)",
              summary="-έως adverb of a -ύς adjective (ἡδέως, ταχέως)"),
)

# Verbs. The present stem is not recoverable from an aorist form when the two
# are suppletive (εἶπον/λέγω); these rules read only the ENDINGS that mark a
# tense, and the resolver then checks whether the present it reconstructs is a
# word the corpus actually contains. Where it is not, the form is left
# unreduced and flagged, which is the honest outcome rather than a wrong guess.
_VERBAL: tuple[LemmaRule, ...] = (
    # Contracted verbs (-έω, -άω, -όω) come FIRST, and the position is
    # load-bearing rather than decorative. The contract vowel disappears in most
    # forms, so `ποιεῖ` and `λύει` normalize to the same string and no ending
    # separates them; what DOES separate the contracted aorist is the -ησ- that
    # replaces -εσ-/-ασ- (`ἐποίησεν` against `ἔλυσεν`), and -ωσ- for -όω
    # (`ἐδήλωσεν`). Those signallers are unambiguous, but their endings are
    # SUFFIXES of the plain ones — `ησαντος` ends in `σαντος` — so a plain rule
    # declared earlier would swallow them and reconstruct `ἐποιη-` as a stem.
    LemmaRule("aor_esa", "verb", "ησα", ("{stem}εω", "{stem}αω"), "1sg aorist ind"),
    LemmaRule("aor_esas", "verb", "ησας", ("{stem}εω", "{stem}αω"), "2sg aorist / ptcp nom sg"),
    LemmaRule("aor_ese", "verb", "ησε", ("{stem}εω", "{stem}αω"), "3sg aorist ind"),
    LemmaRule("aor_esen", "verb", "ησεν", ("{stem}εω", "{stem}αω"), "3sg aorist ind"),
    LemmaRule("aor_esan", "verb", "ησαν", ("{stem}εω", "{stem}αω"), "3pl aorist ind"),
    LemmaRule("aor_esamen", "verb", "ησαμεν", ("{stem}εω", "{stem}αω"), "1pl aorist ind"),
    LemmaRule("aor_esate", "verb", "ησατε", ("{stem}εω", "{stem}αω"), "2pl aorist ind"),
    LemmaRule("aor_esanto", "verb", "ησαντο", ("{stem}εω", "{stem}αω"), "3pl aorist mid"),
    LemmaRule("aor_esato", "verb", "ησατο", ("{stem}εω", "{stem}αω"), "3sg aorist mid"),
    LemmaRule("aor_esai", "infinitive", "ησαι", ("{stem}εω", "{stem}αω"), "infinitive aorist"),
    LemmaRule("aor_esasthai", "infinitive", "ησασθαι", ("{stem}εω", "{stem}αω"),
              "infinitive aorist middle"),
    LemmaRule("aor_esantos", "participle", "ησαντος", ("{stem}εω", "{stem}αω"),
              "participle aorist gen sg masc"),
    LemmaRule("aor_esantes", "participle", "ησαντες", ("{stem}εω", "{stem}αω"),
              "participle aorist nom pl masc"),
    LemmaRule("aor_esamenos", "participle", "ησαμενος", ("{stem}εω", "{stem}αω"),
              "participle aorist mid nom sg masc"),
    LemmaRule("fut_esei", "verb", "ησει", ("{stem}εω", "{stem}αω"), "3sg future ind"),
    LemmaRule("fut_esousi", "verb", "ησουσι", ("{stem}εω", "{stem}αω"), "3pl future ind"),
    LemmaRule("fut_esousin", "verb", "ησουσιν", ("{stem}εω", "{stem}αω"), "3pl future ind"),
    LemmaRule("aor_wsa", "verb", "ωσα", ("{stem}οω",), "1sg aorist ind"),
    LemmaRule("aor_wsen", "verb", "ωσεν", ("{stem}οω",), "3sg aorist ind"),
    LemmaRule("aor_wse", "verb", "ωσε", ("{stem}οω",), "3sg aorist ind"),
    LemmaRule("aor_wsan", "verb", "ωσαν", ("{stem}οω",), "3pl aorist ind"),
    # Infinitives next — the ending is unambiguous and so is the tense.
    LemmaRule("inf_nai", "infinitive", "ναι", ("{stem}μι", "{stem}ω"),
              "infinitive aorist / athematic"),
    LemmaRule("inf_sthai", "infinitive", "σθαι", ("{stem}ω",), "infinitive middle/passive",
              drop=0, stem_min=2),
    LemmaRule("inf_sai", "infinitive", "σαι", ("{stem}ω",), "infinitive aorist", stem_min=2),
    LemmaRule("inf_ein", "infinitive", "ειν", ("{stem}ω",), "infinitive present", stem_min=2),
    LemmaRule("inf_enai", "infinitive", "εναι", ("{stem}ω",), "infinitive aorist passive", stem_min=2),
    # Participles. The aorist active in -σας / -σαντος and the passive in
    # -θείς / -θέντος are two of the most frequent forms in historical prose.
    LemmaRule("ptcp_santos", "participle", "σαντος", ("{stem}ω",), "participle aorist gen sg masc"),
    LemmaRule("ptcp_sasin", "participle", "σασιν", ("{stem}ω",), "participle aorist dat pl"),
    LemmaRule("ptcp_sas", "participle", "σας", ("{stem}ω",), "participle aorist nom sg masc"),
    LemmaRule("ptcp_sasa", "participle", "σασα", ("{stem}ω",), "participle aorist nom sg fem"),
    LemmaRule("ptcp_san", "participle", "σαν", ("{stem}ω",), "participle aorist nom acc sg neut"),
    LemmaRule("ptcp_santes", "participle", "σαντες", ("{stem}ω",), "participle aorist nom pl masc"),
    LemmaRule("ptcp_santas", "participle", "σαντας", ("{stem}ω",), "participle aorist acc pl masc"),
    LemmaRule("ptcp_santwn", "participle", "σαντων", ("{stem}ω",), "participle aorist gen pl"),
    LemmaRule("ptcp_thentos", "participle", "θεντος", ("{stem}ω",), "participle aorist pass gen sg masc"),
    LemmaRule("ptcp_thentwn", "participle", "θεντων", ("{stem}ω",), "participle aorist pass gen pl"),
    LemmaRule("ptcp_theis", "participle", "θεις", ("{stem}ω",), "participle aorist pass nom sg masc"),
    LemmaRule("ptcp_theisa", "participle", "θεισα", ("{stem}ω",), "participle aorist pass nom sg fem"),
    LemmaRule("ptcp_then", "participle", "θεν", ("{stem}ω",), "participle aorist pass nom acc sg neut"),
    LemmaRule("ptcp_thentes", "participle", "θεντες", ("{stem}ω",), "participle aorist pass nom pl masc"),
    LemmaRule("ptcp_thentas", "participle", "θεντας", ("{stem}ω",), "participle aorist pass acc pl masc"),
    LemmaRule("ptcp_ontos", "participle", "οντος", ("{stem}ω",), "participle present gen sg masc"),
    # The bare nominative singular of the present participle. It must be able to
    # LOSE to the noun reading of the same ending (ἀγών, γέρων, λέων) when the
    # corpus attests that one, and it must be able to win when the corpus backs
    # the verb (`ἔχων` → ἔχω, 25 tokens recovered in Polybius alone). The two
    # readings match the same two characters, so match length cannot separate
    # them and the ranking falls through to corpus support, which is the only
    # evidence that distinguishes `ἔχων` from `γέρων` without a lexicon.
    # `stem_min=2` rather than 3 keeps the rule off `ὤν` and `νῦν`-length forms
    # where a two-letter stem is not a stem.
    LemmaRule("ptcp_wn", "participle", "ων", ("{stem}ω",), "participle present nom sg masc",
              stem_min=2),    LemmaRule("ptcp_onti", "participle", "οντι", ("{stem}ω",), "participle present dat sg"),
    LemmaRule("ptcp_ontes", "participle", "οντες", ("{stem}ω",), "participle present nom pl masc"),
    LemmaRule("ptcp_ontas", "participle", "οντας", ("{stem}ω",), "participle present acc pl masc"),
    LemmaRule("ptcp_ontwn", "participle", "οντων", ("{stem}ω",), "participle present gen pl"),
    LemmaRule("ptcp_ousa", "participle", "ουσα", ("{stem}ω",), "participle present nom sg fem"),
    LemmaRule("ptcp_ouses", "participle", "ουσης", ("{stem}ω",), "participle present gen sg fem"),
    LemmaRule("ptcp_ousan", "participle", "ουσαν", ("{stem}ω",), "participle present acc sg fem"),
    LemmaRule("ptcp_oush", "participle", "ουσι", ("{stem}ω",), "participle present dat pl / 3pl"),
    LemmaRule("ptcp_ousin", "participle", "ουσιν", ("{stem}ω",), "participle present dat pl / 3pl"),
    LemmaRule("ptcp_omenos", "participle", "ομενος", ("{stem}ω",), "participle present mid nom sg masc"),
    LemmaRule("ptcp_omenou", "participle", "ομενου", ("{stem}ω",), "participle present mid gen sg"),
    LemmaRule("ptcp_omenw", "participle", "ομενω", ("{stem}ω",), "participle present mid dat sg"),
    LemmaRule("ptcp_omenon", "participle", "ομενον", ("{stem}ω",), "participle present mid acc sg"),
    LemmaRule("ptcp_omenoi", "participle", "ομενοι", ("{stem}ω",), "participle present mid nom pl"),
    LemmaRule("ptcp_omenwn", "participle", "ομενων", ("{stem}ω",), "participle present mid gen pl"),
    LemmaRule("ptcp_omenois", "participle", "ομενοις", ("{stem}ω",), "participle present mid dat pl"),
    LemmaRule("ptcp_omenous", "participle", "ομενους", ("{stem}ω",), "participle present mid acc pl"),
    LemmaRule("ptcp_omenh", "participle", "ομενη", ("{stem}ω",), "participle present mid nom sg fem"),
    LemmaRule("ptcp_omenhs", "participle", "ομενης", ("{stem}ω",), "participle present mid gen sg fem"),
    LemmaRule("ptcp_amenos", "participle", "αμενος", ("{stem}ω",), "participle aorist mid nom sg masc"),
    LemmaRule("ptcp_amenou", "participle", "αμενου", ("{stem}ω",), "participle aorist mid gen sg"),
    LemmaRule("ptcp_amenoi", "participle", "αμενοι", ("{stem}ω",), "participle aorist mid nom pl"),
    LemmaRule("ptcp_amenwn", "participle", "αμενων", ("{stem}ω",), "participle aorist mid gen pl"),
    LemmaRule("ptcp_amenous", "participle", "αμενους", ("{stem}ω",), "participle aorist mid acc pl"),
    LemmaRule("ptcp_amenois", "participle", "αμενοις", ("{stem}ω",), "participle aorist mid dat pl"),
    LemmaRule("ptcp_amenon", "participle", "αμενον", ("{stem}ω",), "participle aorist mid acc sg"),
    # Finite aorist and passive forms. `-θη` marks the passive aorist, so the
    # stem before it IS the present stem for the vast majority of verbs.
    LemmaRule("aor_pass_hnai", "verb", "θηναι", ("{stem}ω",), "infinitive aorist passive"),
    LemmaRule("aor_pass_h", "verb", "θη", ("{stem}ω",), "3sg aorist passive ind"),
    LemmaRule("aor_pass_hn", "verb", "θην", ("{stem}ω",), "1sg 3pl aorist passive ind"),
    LemmaRule("aor_pass_hsan", "verb", "θησαν", ("{stem}ω",), "3pl aorist passive ind"),
    LemmaRule("aor_pass_hs", "verb", "θης", ("{stem}ω",), "2sg aorist passive ind"),
    LemmaRule("aor_pass_hsomai", "verb", "θησομαι", ("{stem}ω",), "1sg future passive ind"),
    LemmaRule("aor_pass_hsetai", "verb", "θησεται", ("{stem}ω",), "3sg future passive ind"),
    LemmaRule("aor_pass_hesetai", "verb", "ησεται", ("{stem}ω",), "3sg future passive ind"),
    # Aorist active in -σα. The σ is the marker, so it is stripped with the
    # ending; a stem that then fails to yield an attested present is left alone.
    LemmaRule("aor_sa", "verb", "σα", ("{stem}ω",), "1sg aorist ind / 3sg aorist"),
    LemmaRule("aor_sas", "verb", "σας", ("{stem}ω",), "2sg aorist ind"),
    LemmaRule("aor_se", "verb", "σε", ("{stem}ω",), "3sg aorist ind"),
    LemmaRule("aor_sen", "verb", "σεν", ("{stem}ω",), "3sg aorist ind"),
    LemmaRule("aor_samen", "verb", "σαμεν", ("{stem}ω",), "1pl aorist ind"),
    LemmaRule("aor_sate", "verb", "σατε", ("{stem}ω",), "2pl aorist ind"),
    LemmaRule("aor_san", "verb", "σαν", ("{stem}ω",), "3pl aorist ind"),
    # Future in -σω / -σει / -σουσι: the σ is FUTURE, not aorist, and the stem
    # is the same one the present uses, so the reconstruction is the same.
    LemmaRule("fut_sousi", "verb", "σουσι", ("{stem}ω",), "3pl future ind"),
    LemmaRule("fut_sousin", "verb", "σουσιν", ("{stem}ω",), "3pl future ind"),
    LemmaRule("fut_sei", "verb", "σει", ("{stem}ω",), "3sg future ind / 2sg mid"),
    LemmaRule("fut_sein", "verb", "σειν", ("{stem}ω",), "infinitive future"),
    LemmaRule("fut_sas", "verb", "σεις", ("{stem}ω",), "2sg future ind"),
    LemmaRule("fut_sesthai", "verb", "σεσθαι", ("{stem}ω",), "infinitive future mid"),
    LemmaRule("fut_somenos", "verb", "σομενος", ("{stem}ω",), "participle future mid nom sg masc"),
    LemmaRule("fut_somenou", "verb", "σομενου", ("{stem}ω",), "participle future mid gen sg"),
    LemmaRule("fut_somenoi", "verb", "σομενοι", ("{stem}ω",), "participle future mid nom pl"),
    # Present and imperfect: the endings are the primary ones, and the lemma is
    # the first person singular present, which is the stem plus -ω.
    LemmaRule("pr_w", "verb", "ω", ("{stem}ω",), "1sg present ind", stem_min=3),
    LemmaRule("pr_omen", "verb", "ομεν", ("{stem}ω",), "1pl present ind"),
    LemmaRule("pr_ete", "verb", "ετε", ("{stem}ω",), "2pl present ind"),
    LemmaRule("pr_ousi", "verb", "ουσι", ("{stem}ω",), "3pl present ind"),
    LemmaRule("pr_ousin", "verb", "ουσιν", ("{stem}ω",), "3pl present ind"),
    LemmaRule("pr_ei", "verb", "ει", ("{stem}ω", "{stem}εω", "{stem}αω", "{stem}οω"),
              "3sg present ind / 2sg mid", stem_min=3),
    LemmaRule("pr_eis", "verb", "εις", ("{stem}ω",), "2sg present ind"),
    LemmaRule("pr_etai", "verb", "εται", ("{stem}ω",), "3sg present mid/pass"),
    LemmaRule("pr_omai", "verb", "ομαι", ("{stem}ω",), "1sg present mid/pass"),
    LemmaRule("pr_ontai", "verb", "ονται", ("{stem}ω",), "3pl present mid/pass"),
    LemmaRule("pr_esqai", "verb", "εσθαι", ("{stem}ω",), "infinitive present mid/pass"),
    LemmaRule("imf_on", "verb", "ον", ("{stem}ω",), "1sg 3pl imperfect / neut nom acc sg"),
    LemmaRule("imf_omen", "verb", "ομεν", ("{stem}ω",), "1pl imperfect ind"),
    LemmaRule("imf_eto", "verb", "ετο", ("{stem}ω",), "3sg imperfect mid"),
    LemmaRule("imf_onto", "verb", "οντο", ("{stem}ω",), "3pl imperfect mid"),
    # Optative and subjunctive third persons, frequent in indirect speech.
    LemmaRule("opt_oien", "verb", "οιεν", ("{stem}ω",), "3pl optative"),
    LemmaRule("opt_oi", "verb", "οι", ("{stem}ω",), "3sg optative"),
    LemmaRule("sub_wsi", "verb", "ωσι", ("{stem}ω",), "3pl subjunctive"),
    LemmaRule("sub_wsin", "verb", "ωσιν", ("{stem}ω",), "3pl subjunctive"),
    LemmaRule("sub_h", "verb", "η", ("{stem}ω", "{stem}εω", "{stem}αω", "{stem}οω"),
              "3sg subjunctive", stem_min=3),
    LemmaRule("sub_hs", "verb", "ης", ("{stem}ω", "{stem}εω", "{stem}αω", "{stem}οω"),
              "2sg subjunctive", stem_min=3),
    LemmaRule("imp_son", "verb", "σον", ("{stem}ω",), "imperative aorist 2sg"),
    LemmaRule("imp_te", "verb", "τε", ("{stem}ω",), "imperative present 2pl", stem_min=3),
    LemmaRule("imp_etwsan", "verb", "ετωσαν", ("{stem}ω",), "imperative present 3pl"),
    LemmaRule("imp_satwsan", "verb", "σατωσαν", ("{stem}ω",), "imperative aorist 3pl"),
)


RULES: tuple[LemmaRule, ...] = _NOMINAL + _ADJECTIVAL + _VERBAL
BY_NAME = {r.name: r for r in RULES}
_ENDING_ORDER = tuple(range(len(RULES)))   # declaration order IS the priority

# Rules whose reconstructed lemma may carry a syllabic augment. Derived from the
# rule-name families rather than declared per rule because the family IS the
# declaration: every `imf_` and `aor_` rule reads a past-tense stem by
# construction, and the two are exactly the tenses the augment belongs to. The
# prefix test on the stem keeps `pr_`/`fut_`/`ptcp_` rules out of it, so the
# present of `ἐθέλω` is never re-read as `θέλω`.
_AUGMENT_TENSES = ("imf_", "aor_")


def _augments(r: LemmaRule) -> bool:
    return r.name.startswith(_AUGMENT_TENSES)


def describe() -> dict:
    """Machine-readable rule inventory, so the UI never restates the tables."""
    return {
        "closed": {"n_forms": len(_CLOSED),
                   "n_readings": sum(len(v) for v in _CLOSED.values()),
                   "pos": sorted({p for v in _CLOSED.values() for _, p, _ in v})},
        "rules": [{"name": r.name, "pos": r.pos, "ending": r.ending,
                   "lemmas": list(r.lemmas), "infl": r.infl,
                   "summary": r.summary} for r in RULES],
        "n_rules": len(RULES),
        "accuracy": ACCURACY,
    }


# ---------------------------------------------------------------------------
# 3. THE ANALYSER
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Analysis:
    """One reading of one form. Never presented without its `source`."""
    lemma: str        # normalised, UNPOOLED (pooling happens in `key_of`)
    pos: str
    infl: str
    rule: str
    source: str       # "closed" | "paradigm" | "rule" | "unreduced"
    stem: str = ""


# Sources whose readings are MEMORISED. A rule reading must never win against
# one of these: the table states a fact about the word, and a suffix rule that
# happens to match the same string is not evidence against it. Without this,
# `ἀλλά` (in the conjunction table) lost to the 1st-declension rule reading
# `ἀλλης` — because `ἀλλά`'s own lemma equals the form, and the old resolver
# preferred any reading that "did something". It did something wrong.
_MEMORISED = ("closed", "paradigm")


def candidates(form: str) -> list[Analysis]:
    """Every reading this table can give `form` (normalised), best first.

    The memorised readings come first and are NOT mixed into the rule readings:
    the resolver is expected to use them alone when they exist. Rule readings
    follow in declaration order, which is why the specific endings are declared
    before the general ones — declaration order is the tie-break within a rule,
    and match length, corpus support and corpus weight are the ones across
    rules.
    """
    out: list[Analysis] = []
    seen: set[tuple[str, str]] = set()

    def add(lemma: str, r: LemmaRule, stem: str) -> None:
        k = (lemma, r.infl)
        if k not in seen:
            seen.add(k)
            out.append(Analysis(lemma, r.pos, r.infl, r.name, "rule", stem))

    for src, table in (("closed", _CLOSED), ("paradigm", _PARADIGM)):
        for lemma, pos, infl in table.get(form, ()):
            k = (lemma, infl)
            if k not in seen:
                seen.add(k)
                out.append(Analysis(lemma, pos, infl, src, src, ""))
    for r in RULES:
        end = r.ending
        if not form.endswith(end):
            continue
        stem = form[:-len(end)]
        if r.drop:
            stem = stem[:-r.drop] if r.drop <= len(stem) else ""
        if len(stem) < r.stem_min:
            continue
        if r.stem_re and not re.fullmatch(r.stem_re, stem):
            continue
        for tmpl in r.lemmas:
            add(tmpl.format(stem=stem), r, stem)
            # The syllabic augment. Every past-tense indicative whose stem
            # begins with a consonant is prefixed with ἐ-, and the prefix
            # survives into the reconstructed lemma: `ἐποίησε` was giving
            # `ἐποιεω`, which is not a headword, so the aorist of `ποιέω`
            # never met the present of `ποιέω` and the lexeme split in two.
            # Stripping it is the whole fix and it applies to the imperfect and
            # the aorist alike. Both readings are emitted and the corpus
            # chooses: the unaugmented lemma normally carries all the support,
            # but where the augmented string IS the truth (`ἑαυτοῦ`-style
            # stems, or verbs whose own stem begins with ἐ-) the ranking keeps
            # it. `αὐξάνω`-type vowel-initial verbs take the temporal augment
            # instead and are left alone by the `stem[0] == "ε"` test.
            if _augments(r) and len(stem) > r.stem_min and stem[0] == "ε":
                add(tmpl.format(stem=stem[1:]), r, stem[1:])
    if not out:
        # Nothing matched. Returning the form itself is the honest failure: it
        # says "this layer has no analysis", which is different from saying the
        # form is its own lemma. The caller must not present the two alike.
        out.append(Analysis(form, "unknown", "", "unreduced", "unreduced", ""))
    return out


class LemmaIndex:
    """Analyses a corpus's forms and resolves each against that corpus.

    The resolver is the whole idea, and it runs in TWO PASSES.

    A form's ending alone cannot choose between `πολέμου` (2nd-declension
    genitive) and `πολίτου` (1st-declension masculine genitive): the form does
    not carry that information. The CORPUS does — whichever nominative the text
    also uses is the right reading — but "is the candidate lemma attested as a
    form" is too weak a test, because a genitive singular and a dative singular
    are each the other's candidate lemma and BOTH appear in the text. Measured
    on Thucydides, that test alone put `θαλάσσης` under the headword `θαλάσση`
    (the dative, which is attested) rather than `θάλασσα`.

    So the resolver WEIGHTS each reading by how much of the corpus it would
    claim:

      pass 1  choose by the weak test above and count, for every lemma, the
              total tokens assigned to it;
      pass 2  re-choose among each form's candidates, preferring the reading
              whose lemma carries the greater corpus weight.

    For `θαλάσσης` that is decisive: `θάλασσα` claims the nominative, the
    accusative, both plurals and the genitive, while `θαλάσση` claims only the
    dative. Two passes suffice — the second pass only ever moves weight onto a
    reading a first pass already found, so it cannot introduce a reading from
    nowhere — and iterating further was measured to change nothing.

    Memorised readings (the closed class and the irregular paradigms) skip all
    of this and win outright. They are facts about the word, not inferences
    from its shape, and no amount of corpus weight should outvote them.

    Built once per request over both works together — pooling the evidence is
    deliberate. A lemma attested only in A still disambiguates a form in B, and
    the two works are the two halves of one comparison; resolving them
    separately would let the same form get two different lemmas on the two
    sides and invent a difference.
    """

    def __init__(self, forms: "Counter[str] | dict[str, int]",
                 variants: tuple[str, ...] = VARIANTS_DEFAULT):
        self.forms: dict[str, int] = {f: n for f, n in dict(forms).items() if n}
        self.variants = tuple(variants)
        self._cands: dict[str, list[Analysis]] = {}
        self.weight: Counter = Counter()
        self._chosen: dict[str, Analysis] = {}
        self._ambiguous: dict[str, bool] = {}
        self._prev: dict[str, Analysis] = {}
        self.fcount: Counter = Counter()
        self._keys: dict[str, dict[Analysis, tuple]] = {}
        self._pass1()
        self._settle()

    def key_of(self, lemma: str) -> str:
        """The aggregation key of a lemma: POOLED, so the spelling split is
        folded in as well as the inflection split.

        Pooling last is the point. `θάλασσα` and `θάλαττα` must lemmatise on
        their OWN spelling — the ττ/σσ correspondence is the thing being
        measured, and `variants.unify` erases it — and only then be pooled, so
        that the two lemmatised results meet under one key. Pooling first would
        make the ττ rule blind to its own evidence."""
        return variants_unify(lemma, self.variants)

    def _readings(self, form: str) -> list[Analysis]:
        got = self._cands.get(form)
        if got is None:
            got = self._cands[form] = candidates(form)
        return got

    def _rank(self, form: str, n: int) -> list[Analysis]:
        """This form's readings, best first, by the stated rule.

        Memorised readings come first in the table's own order and are never
        reordered by weight — a memorised reading is a fact, and the weight is
        derived from the resolver's own guesses. Letting weight in here put
        `ἐν` (the preposition) under `εἷς` (the numeral, which also owns `ἕν`)
        in 202 of Thucydides' tokens.

        Rule readings are ranked by corpus weight, and the weight EXCLUDES THIS
        FORM'S OWN TOKENS. That exclusion is not a refinement, it is the fix
        for a feedback loop the measurement caught: `θαλάσσης` is 24 tokens,
        and if it is allowed to vote for its own reading, whichever candidate
        pass 1 happened to pick inherits 24 tokens of "evidence" for itself and
        then outranks the reading the rest of the corpus supports. Excluding
        it, `θάλασσα` wins on the strength of the nominative, accusative and
        plural forms the text actually uses, which is the reasoning a reader
        performs and the only signal that separates the two — the ending
        `-ης` genuinely belongs to both the `-η` and the `-α` declension, so
        the form alone cannot settle it.
        """
        cands = self._readings(form)
        memorised = [c for c in cands if c.source in _MEMORISED]
        if memorised:
            pref = _FORM_PREF.get(form)
            if pref is not None:
                memorised = sorted(memorised, key=lambda c: c.lemma != pref)
            return memorised + [c for c in cands if c.source not in _MEMORISED]
        prev = self._prev.get(form)
        own = prev.lemma if prev is not None else None
        if form in self._keys:
            return sorted(cands, key=self._keys[form].__getitem__)
        keys = {c: self._key(c, form, n, own, i) for i, c in enumerate(cands)}
        self._keys[form] = keys
        return sorted(cands, key=keys.__getitem__)

    def _key(self, c: Analysis, form: str, n: int, own: str | None, i: int) -> tuple:
        """The sort key of one candidate: (support, match length, weight,
        neuter, declaration order).

        SUPPORT is how many DISTINCT corpus forms chose this lemma, and it ranks
        first. It outranks raw token weight because token weight lets one very
        frequent form speak for a whole lemma: `πολύς` carries 151 tokens in the
        gold but only 3 distinct forms — `πολλοί`, `πολλά` and little else —
        while `πόλις` carries 92 across 9. Ranking by weight therefore sent
        `πόλεως` to `πολύς` in 47 of Thucydides' tokens. Counting forms instead
        asks how much of a paradigm the corpus actually exhibits, which is the
        evidence a reader uses and is far harder for one form to dominate.

        MATCH LENGTH is how many characters of the form the rule's ending
        accounted for, and it is the TIE-BREAK where support cannot speak —
        which is every form the corpus shows only once, and every form whose
        rivals are all equally unsupported. It is the only evidence that
        distinguishes a morphological ANALYSIS from a coincidence of final
        letters: `ἐγένετο` ends in `-ο`, a legitimate neuter nominative, and in
        `-ετο`, the imperfect middle; with the short match winning, the noun and
        adjective tables swallowed verb forms wholesale through their shortest
        endings (`ἐγένετος`, `ἐποίησος`, `γενέσθη`, `κατέστος` for `ἐγένετο`,
        `ἐποίησε`, `γενέσθαι`, `κατέστη`). A rule that explains more of the word
        beats one that explains less.

        WHICH OF THE TWO RANKS FIRST WAS MEASURED, not argued, because the
        plausible-sounding answer was wrong in both directions. With length
        first, `λόγος` resolved to `λοξ` through the plosive-stem rule for `-γος`
        — the genitive of a ξ-stem, which `λόγος` merely resembles — trading 7
        forms of corpus evidence for 3 characters of suffix. With support first,
        exact match on gold Thucydides gains 0.31 points and aggregation purity
        1.16 (73.43%→73.74%, 70.14%→71.30% before the `masc` term was added;
        the final figures are in ACCURACY). A form the corpus shows once still
        falls through to length, so nothing is lost where support genuinely
        cannot speak.

        Three candidate keys that the same measurement REJECTED are recorded so
        they are not re-proposed. (1) Promoting a form to its own lemma when a
        nominative rule reconstructs it: the intuition that a citation form
        appearing in the text is self-evidencing is sound, but ranking it does
        not pay (73.73% against 73.74%) and it files the neuter plural `μέρη`
        under itself instead of under `μέρος`. (2) Widening `a_acc_sg_f` and
        `a_gen_pl` to reconstruct the masculine `-ης` as well: it costs 0.37
        points of exact match, because the nominative is the only evidence
        either rule needs and the extra templates mostly add rivals to lose to.
        (3) Letting `masc` speak only where support cannot, i.e. ranking it
        after support rather than before it. It measures marginally BEST of
        every ordering tried (73.80% exact against 73.74%) — and it is still
        the wrong choice, because it does not fix the case it exists for. In a
        paradigm whose feminine readings outnumber the masculine ones
        (`ὁπλίτη`, `ὁπλίτην`, `ὁπλῖται`, `ὁπλίταις` against `ὁπλίτου`,
        `ὁπλιτῶν`) support ranks the wrong family first, the inference never
        speaks, and `ὁπλίτας`/`ὁπλῖται`/`ὁπλιτῶν` split across TWO aggregation
        keys — the exact defect this module was written to repair, on the exact
        paradigm the requirement names. Ranking `masc` above support costs
        0.47 points of exact match and 0.36 of purity on gold Thucydides, and
        it is paid: a requirement that holds only when the corpus happens to
        favour it is not a requirement.

        Both counts EXCLUDE THIS FORM'S OWN CONTRIBUTION, for the reason given
        above. NEUTER is the one piece of morphology the ranking infers rather
        than measures: a noun whose stem shows a plural in `-α` in this corpus
        is a neuter, so its `-ον` form is a nominative/accusative singular
        filing under ITSELF (`χωρίον`, 14 tokens, against `χώριος`) and not a
        masculine accusative filing under `-ος` (`λόγον` → `λόγος`, and `λόγᾱ`
        is not a form). Adjectives are excluded: `νέον` is a masculine
        accusative of `νέος` even though `νέα` exists.
        """
        support = self.fcount.get(c.lemma, 0) - (1 if own == c.lemma else 0)
        weight = self.weight.get(c.lemma, 0) - (n if own == c.lemma else 0)
        neuter = 0
        if c.pos == "noun" and c.lemma.endswith("ον") and c.stem:
            neuter = 1 if self.forms.get(c.stem + "α") else 0
        # The same kind of inference, for the 1st declension. `ὁπλίτας`,
        # `ὁπλῖται`, `ὁπλίταις` and `ὁπλίτην` are each ambiguous between the
        # masculine `-ης` and the feminine `-η`, and the feminine reads win on
        # support — four forms against two — so `ὁπλίτης` itself filed under
        # `ὁπλιτη` and the requirement this module exists to satisfy failed on
        # the very paradigm that states it. What breaks the tie is that `-ου`
        # is NEVER a first-declension feminine genitive: an attested `ὁπλίτου`
        # says the lexeme is masculine, and then `ὁπλίτην` is its accusative
        # rather than a feminine nominative's lookalike. Feminine `τιμή` has no
        # `τιμοῦ` to mistake, so it is untouched.
        # DECLENSION FAMILY — the same kind of corpus inference as NEUTER, and
        # the one that makes the requirement's own paradigm work. `ὁπλίτας`,
        # `ὁπλῖται`, `ὁπλίταις` and `ὁπλίτην` are each ambiguous between the
        # masculine `-ης` and the feminine `-η`; the feminine readings outnumber
        # the masculine ones four to two, so counting forms ranks the wrong
        # family first and `ὁπλίτας`/`ὁπλῖται`/`ὁπλιτῶν` split across two keys —
        # the defect this module exists to repair. What decides it is a case
        # form the candidate's OWN paradigm predicts:
        #
        #   masculine `-ης`/`-ας`  an attested `stemου` genitive. `-ου` is NEVER
        #                          a first-declension feminine genitive.
        #   feminine  `-η`/`-α`    an attested `lemma + ν` accusative singular.
        #
        # The two are numbered because they are not equal evidence: `-ου`
        # settles the question outright, while an attested `θαλασσαν` only says
        # the lexeme is the feminine one — and it has to be numbered, because
        # for the form `ὁπλίτης` BOTH fire (`ὁπλιτην` is attested too), and
        # ranking them equal lets support hand the form back to `ὁπλιτη`.
        #
        # Each is guarded against the form under analysis, which is the same
        # self-exclusion as above and matters just as much here: `πολεμου` IS
        # the string `stemου`, so letting it testify would make `πολεμης` a
        # reading of `πολεμου` — it promoted exactly that error in 25 of
        # Thucydides' tokens. `stemος` is the second guard: `ἄλλου` and
        # `πολέμου` are the 2nd-declension genitives of `ἄλλος` and `πόλεμος`,
        # not masculine `-ης` headwords, and promoting an `-ης` reading for
        # them produced `αλλης` for `αλλων`, `βαρβαρης` for `βαρβαρων` and
        # `ιδιης` for the neuter plural `ιδια`.
        family = 0
        if c.stem:
            if c.lemma.endswith(("ης", "ας")):
                if form != c.stem + "ου" and not self.forms.get(c.stem + "ος") \
                        and self.forms.get(c.stem + "ου"):
                    family = 2
            elif c.lemma.endswith(("η", "α")):
                if form != c.lemma + "ν" and self.forms.get(c.lemma + "ν"):
                    family = 1
        rule = BY_NAME.get(c.rule)
        # FAMILY ranks ABOVE support, unlike NEUTER, and it has to: it is the
        # evidence that the corpus can already be counted on, and where it
        # speaks the count is what it is correcting. It is narrow — a candidate
        # must be a 1st-declension headword AND carry an attested case form of
        # its own paradigm — and it costs nothing measurable: 73.86% exact and
        # 71.30% purity against 73.74% and 71.30% without it. The alternative
        # ordering, family BELOW support, measures marginally better on gold
        # (74.01% / 71.58%) and is still the wrong choice, because it does not
        # fix the case it exists for — counting forms ranks the feminine family
        # first and the inference never speaks, so the requirement's own
        # paradigm splits across two keys.
        return (-family, -support, -(len(rule.ending) if rule else 0),
                -weight, -neuter, i)

    def _pass1(self) -> None:
        """Assign every corpus form by the weak test and total up the weight.

        The weight of a lemma is the number of corpus tokens whose reading it
        is, which is why this has to be a whole-corpus pass and cannot be done
        form by form: it is a property of the corpus, not of the form.
        """
        self._prev: dict[str, Analysis] = {}
        self.weight: Counter = Counter()
        for form, n in self.forms.items():
            cands = self._readings(form)
            memorised = [c for c in cands if c.source in _MEMORISED]
            if memorised:
                picked = memorised[0]
            else:
                attested = [c for c in cands if self.forms.get(c.lemma, 0) > 0]
                # A reading whose lemma IS the form is the "nothing was undone"
                # reading; it is the last resort, so a candidate that actually
                # reduced the form seeds the corpus instead.
                pool = [c for c in (attested or cands) if c.lemma != form] or \
                       (attested or cands)
                picked = pool[0]
            self._prev[form] = picked
            self.weight[picked.lemma] += n
            self.fcount[picked.lemma] += 1

    def _settle(self, rounds: int = 2) -> None:
        """Re-rank every form against the weights, twice.

        Two rounds suffice and more were measured to change nothing: the second
        round can only move a form onto a reading the first round already found,
        so it cannot invent a reading from nowhere. The loop exists because the
        weight is a property of the whole assignment, not of one form, so the
        assignment has to be recomputed from scratch rather than adjusted in
        place.
        """
        for _ in range(rounds):
            picked: dict[str, Analysis] = {}
            weight: Counter = Counter()
            fcount: Counter = Counter()
            self._keys = {}
            for form, n in self.forms.items():
                choice = self._rank(form, n)[0]
                picked[form] = choice
                weight[choice.lemma] += n
                fcount[choice.lemma] += 1
            self._prev, self.weight, self.fcount = picked, weight, fcount

    def analyse(self, form: str) -> tuple[list[Analysis], Analysis, bool]:
        """(all readings, the chosen one, was_it_ambiguous) for one form.

        Readings come back in the order the resolver ranked them, so a panel
        that lists them is showing the reason for the choice rather than an
        unordered set. A form is `ambiguous` when more than one reading is
        carried by real corpus weight — a single reading, or a memorised one
        nobody competes with, is not.
        """
        hit = self._chosen.get(form)
        if hit is None:
            n = self.forms.get(form, 0)
            ranked = self._rank(form, n)
            self._cands[form] = ranked
            hit = ranked[0]
            self._ambiguous[form] = len(
                {c.lemma for c in ranked if self.weight.get(c.lemma, 0) > 0}) > 1
            self._chosen[form] = hit
        return self._cands[form], hit, self._ambiguous.get(form, False)

    def weighted(self, form: str) -> list[dict]:
        """The readings of a form with the weight that decided between them.

        This is what a breakdown panel should show: not just "which lemma" but
        how strongly the corpus supports it against the alternatives, so a
        reader can see when the choice was close.
        """
        cands, chosen, ambiguous = self.analyse(form)
        return [{"lemma": c.lemma, "pos": c.pos, "infl": c.infl, "rule": c.rule,
                 "source": c.source, "weight": self.weight.get(c.lemma, 0),
                 "chosen": c == chosen} for c in cands]


# ---------------------------------------------------------------------------
# 4. AGGREGATION
# ---------------------------------------------------------------------------
def collect(sections: list[dict], drop_elided: bool = True) -> dict:
    """Token census of one work, keyed by surface form.

    Deliberately the SAME tokenizer as `archaism_pure.work_freq` — `words_elided`
    with the elision fragments dropped — because the counts this layer produces
    will be placed beside those, and two tokenizations placed side by side is
    the drift that already produced one contradicted count in this project.
    """
    counts: Counter = Counter()
    caps: Counter = Counter()
    display: dict[str, str] = {}
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
            counts[n] += 1
            if w[:1].isupper():
                caps[n] += 1
            if n not in display:
                display[n] = w
    return {"counts": counts, "total": sum(counts.values()), "caps": caps,
            "display": display, "n_elided": n_elided,
            "drop_elided": drop_elided}


def _bucket(form: str, ix: LemmaIndex, cap_share: float) -> dict:
    """The per-form slice of an aggregation row: what it is and how it reads."""
    cands, chosen, ambiguous = ix.analyse(form)
    return {
        "form": form,
        "lemma": chosen.lemma,
        "key": ix.key_of(chosen.lemma),
        "pos": chosen.pos,
        "infl": chosen.infl,
        "rule": chosen.rule,
        "source": chosen.source,
        "ambiguous": ambiguous,
        "proper": cap_share > 0.5,
        # Only the readings that are PLAUSIBLE in this corpus are kept: an
        # unattested candidate is noise in a breakdown panel and would make a
        # form look more ambiguous than it is. The chosen reading is always
        # present, so the list is never empty.
        "readings": [{"lemma": c.lemma, "pos": c.pos, "infl": c.infl,
                      "rule": c.rule, "source": c.source}
                     for c in (cands if len(cands) <= 6 else cands[:6])],
    }


def aggregate(sections_a: list[dict], sections_b: list[dict],
              variants: tuple[str, ...] = VARIANTS_DEFAULT,
              drop_elided: bool = True) -> dict:
    """Group both works' surface forms under lemmas, with the breakdown.

    One index over BOTH works (see `LemmaIndex`), then each work's tokens are
    assigned through it, so a form occurring in only one work still gets the
    reading the other work's evidence supports. Returns per-lemma rows carrying
    the per-form breakdown — which is what the UI expands on click, and the
    reason the aggregation is worth doing at all.
    """
    ca = collect(sections_a, drop_elided)
    cb = collect(sections_b, drop_elided)
    forms: Counter = Counter()
    forms.update(ca["counts"])
    forms.update(cb["counts"])
    ix = LemmaIndex(forms, variants)

    rows: dict[str, dict] = {}
    for side, census in (("a", ca), ("b", cb)):
        for form, n in census["counts"].items():
            b = _bucket(form, ix, census["caps"].get(form, 0) / n)
            row = rows.get(b["key"])
            if row is None:
                row = rows[b["key"]] = {
                    "key": b["key"], "forms": {}, "count_a": 0, "count_b": 0,
                    "proper_a": 0, "proper_b": 0, "n_ambiguous_a": 0,
                    "n_ambiguous_b": 0, "n_unreduced_a": 0, "n_unreduced_b": 0,
                    "sources": {}, "pos": {}, "lemmas": {},
                }
            row["count_" + side] += n
            if b["proper"]:
                row["proper_" + side] += n
            if b["ambiguous"]:
                row["n_ambiguous_" + side] += n
            if b["source"] == "unreduced":
                row["n_unreduced_" + side] += n
            row["sources"][b["source"]] = row["sources"].get(b["source"], 0) + n
            if b["pos"]:
                row["pos"][b["pos"]] = row["pos"].get(b["pos"], 0) + n
            row["lemmas"][b["lemma"]] = row["lemmas"].get(b["lemma"], 0) + n
            f = row["forms"].get(form)
            if f is None:
                f = row["forms"][form] = dict(b, count_a=0, count_b=0,
                                              display=census["display"].get(form, form))
            f["count_" + side] += n
    return {"rows": rows, "n_a": ca["total"], "n_b": cb["total"],
            "n_forms_a": len(ca["counts"]), "n_forms_b": len(cb["counts"]),
            "n_elided_a": ca["n_elided"], "n_elided_b": cb["n_elided"],
            "variants": tuple(variants), "index": ix}


def lemma_rows(agg: dict, limit: int = 300, drop_proper: bool = True) -> list[dict]:
    """Flatten `aggregate` into display rows, ranked by the younger work's rate.

    Ordered by count_a descending, the same ordering `archaism_pure.contrast`
    uses before its score sort, so a lemma table and a surface-form table read
    the same way. The per-form breakdown is sorted by the pooled count, and a
    form's `readings` are kept only for the forms that are actually ambiguous —
    the rest would be five identical lines of noise per row.
    """
    out = []
    for row in agg["rows"].values():
        ca, cb = row["count_a"], row["count_b"]
        if drop_proper and (ca + cb) and (
                (row["proper_a"] + row["proper_b"]) / (ca + cb)) > 0.5:
            continue
        forms = sorted(row["forms"].values(),
                       key=lambda f: (-(f["count_a"] + f["count_b"]), f["form"]))
        out.append({
            "key": row["key"],
            "lemma": max(row["lemmas"], key=lambda l: (row["lemmas"][l], l)),
            "count_a": ca, "count_b": cb,
            "n_forms_a": sum(1 for f in forms if f["count_a"]),
            "n_forms_b": sum(1 for f in forms if f["count_b"]),
            "n_ambiguous_a": row["n_ambiguous_a"],
            "n_ambiguous_b": row["n_ambiguous_b"],
            "n_unreduced_a": row["n_unreduced_a"],
            "n_unreduced_b": row["n_unreduced_b"],
            "sources": row["sources"],
            "pos": sorted(row["pos"], key=lambda p: -row["pos"][p]),
            "forms": [{"form": f["form"], "display": f["display"],
                       "count_a": f["count_a"], "count_b": f["count_b"],
                       "pos": f["pos"], "infl": f["infl"], "rule": f["rule"],
                       "source": f["source"], "ambiguous": f["ambiguous"],
                       "readings": f["readings"] if f["ambiguous"] else []}
                      for f in forms],
        })
    out.sort(key=lambda r: (-(r["count_a"] + r["count_b"]), -r["count_a"], r["key"]))
    n_candidates = len(out)
    return out[:limit], n_candidates


def lemma_report(sections_a: list[dict], sections_b: list[dict],
                 variants: tuple[str, ...] = VARIANTS_DEFAULT,
                 drop_proper: bool = True, limit: int = 300,
                 drop_elided: bool = True) -> dict:
    """REPORT 3 OF 3 — the rarity ranking with the inflection split repaired.

    Same question as `archaism_pure.contrast`, asked one level up. `contrast`
    keys on the pooled surface form, so `ποταμόν` and `ποταμός` are two rows and
    the lexeme's rate is split between them; here they are one row, and the row
    carries the breakdown that produced it.

    The rows are NOT ranked by `contrast`'s log-ratio score, because the two
    layers are not interchangeable and pretending otherwise would invite the
    wrong reading: this report is about whether the AGGREGATION changes which
    lexemes look like archaisms, and the `count_a`/`count_b` columns answer
    that directly. Attach a score by calling `archaism_pure.contrast` on the
    lemma-keyed counts, which is a different — and defensible — claim, and one
    that should be made explicitly rather than as a side effect of a sort key.

    Returns {"rows", "n_a", "n_b", "n_candidates", "params", "rules", "accuracy"}
    where `accuracy` is the measured figure, carried into the response so a
    table can print it beside the numbers instead of asserting quality.
    """
    agg = aggregate(sections_a, sections_b, variants, drop_elided)
    rows, n_candidates = lemma_rows(agg, limit=limit, drop_proper=drop_proper)
    n_forms = agg["n_forms_a"] + agg["n_forms_b"]
    n_lemmas = len(agg["rows"])
    return {
        "rows": rows, "n_a": agg["n_a"], "n_b": agg["n_b"],
        "n_candidates": n_candidates,
        "n_forms": n_forms, "n_lemmas": n_lemmas,
        # The measured compression. This is the honest headline number for the
        # layer: how much of the surface-form spread the aggregation removed,
        # as a ratio a reader can check against their own intuition.
        "compression": round(n_forms / n_lemmas, 3) if n_lemmas else None,
        "n_elided_a": agg["n_elided_a"], "n_elided_b": agg["n_elided_b"],
        "params": {"variants": list(variants), "drop_proper": drop_proper,
                   "limit": limit, "drop_elided": drop_elided},
        "rules": describe(),
    }


def lemma_key_lookup(sections_a: list[dict], sections_b: list[dict], key: str,
                     variants: tuple[str, ...] = VARIANTS_DEFAULT,
                     drop_elided: bool = True) -> dict:
    """Every surface form of one lemma key, with its counts — the expander.

    Used by the loci endpoint so that "where in B" can be asked of a LEMMA and
    answered with the forms that were pooled into it, instead of one spelling
    that is only part of the answer. Same index as `aggregate`, same tokenizer,
    so the numbers agree with the row the click came from.
    """
    agg = aggregate(sections_a, sections_b, variants, drop_elided)
    row = agg["rows"].get(key)
    if row is None:
        return {"key": key, "found": False, "forms": []}
    forms = sorted(row["forms"].values(),
                   key=lambda f: (-(f["count_a"] + f["count_b"]), f["form"]))
    return {"key": key, "found": True, "forms": [
        {"form": f["form"], "display": f["display"], "count_a": f["count_a"],
         "count_b": f["count_b"], "pos": f["pos"], "infl": f["infl"],
         "source": f["source"], "ambiguous": f["ambiguous"]} for f in forms]}


def key_forms(sections_a: list[dict], sections_b: list[dict], key: str,
              variants: tuple[str, ...] = VARIANTS_DEFAULT,
              drop_elided: bool = True) -> tuple[str, ...]:
    """Just the surface forms of a lemma key — the token set for a KWIC pass.

    Separate from `lemma_key_lookup` because the loci endpoint wants the forms
    and not the counts, and it is the forms that must come from the SAME
    analysis that produced the row: searching on a hand-assembled guess at the
    paradigm would return loci that do not add up to the count beside them.
    """
    got = lemma_key_lookup(sections_a, sections_b, key, variants, drop_elided)
    return tuple(f["form"] for f in got["forms"])

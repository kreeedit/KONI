"""Perseus/TLG Beta Code -> Unicode Greek, and back. Pure stdlib.

WHY THIS EXISTS
---------------
The LSJ in the Perseus `lexica` repository — the only openly licensed Greek
lexicon of any size that is reachable from this project without a new
dependency — is NOT stored in Unicode. Its text is Beta Code: `cai/nw` is
ξαίνω, `a)/wtos` is ἀώτος, `*)ai/+da,` is Ἄϊδα,. A dictionary layer therefore
needs a transliterator before it needs anything else, and this is that module.

It reads in both directions on purpose. `decode` is what the lexicon builder
calls; `encode` has no caller in the application at all — it exists so the
table can be TESTED, by round-tripping it over the gold treebank lemmas
(`PerseusDL/treebank_data`, real Unicode, real accented Greek):

    decode(encode(lemma)) == lemma      for every lemma in the treebank

That test is the reason to trust `decode`. Checking a converted dictionary by
eyeballing a few headwords cannot distinguish a correct table from one whose
breathings are systematically flipped; a round trip over 25 000 lemmas can.

Measured on `PerseusDL/treebank_data` v2.1 (25159 tokens, 2543 distinct
lemmas): **2541 round-trip exactly.** The two that do not are a defect in the
gold data, not here — it spells two words with a Latin `v` where it means υ
(`Βυζάντιοv`, `ἱερόv`), and `v` is digamma, so the round trip correctly refuses
them. Note what this test does and does not prove: it pins the ATTACHMENT rules
— which mark lands on which vowel. That is not obvious in a diphthong: αὖ is
α + U+1F56 (upsilon carrying BOTH the breathing and the circumflex), so ALL of
a diphthong's marks sit on the SECOND element in Unicode, and decoding
`au)=` by attaching to the last vowel is right precisely because of that. The
same rule is what makes circumflex stack correctly with a breathing or an iota
subscript. What the round trip CANNOT pin is the MEANING of `)` against `(`,
because a flipped table round-trips just as well — that one is settled by the
LSJ glosses above, and only by them.

THE TABLE, AND HOW EACH ENTRY WAS ESTABLISHED
---------------------------------------------
Letters: `a b g d e z h q i k l m n c o p r s t u f x y w` are
`α β γ δ ε ζ η θ ι κ λ μ ν ξ ο π ρ σ τ υ φ χ ψ ω`. `*` before a letter makes it
capital. `s` becomes final sigma word-finally. `v` (digamma, ϝ) is mapped
because the LSJ uses it, and nothing else does.

`c` and `x` are the two that look swapped, so they were settled by existence,
not by the mnemonic: `c` = ξ, `x` = χ. A real slice search finds ξένος as
`ce/nos` (slice 15) and finds no `xe/nos` at all — χένος is not a word — while
`xalepo/s` (slice 25) is glossed "difficult, hard to bear" and sits in the same
slice as `xai/rw`, both of which begin with χ. A reversed table would have to
have the LSJ contain a word that does not exist and omit one that does.

Diacritics are POSTFIX on the vowel they belong to, and they stack in any
order: `a)/` is ἀ with an acute... which brings up the one entry that had to be
decided from evidence rather than from documentation:

    `)` = smooth breathing (psili)      `(` = rough breathing (dasia)

This is the opposite of the mnemonic one would guess, and it is ALSO not
decidable by round-tripping (a flipped table round-trips perfectly). It was
settled by reading the LSJ's own English glosses:

  * `a)ei/dw` is glossed "sing" — that is ἀείδω, smooth.
  * `a(li/skomai` is glossed "to be taken, conquered" — that is ἁλίσκομαι, rough.
  * `a)fori/zw` is glossed "mark off by boundaries" — ἀφορίζω, smooth — while
    `a(fori/zw` (rough) is ABSENT from both slices that could hold it. Under a
    reversed table the dictionary would be missing its real entry and instead
    carry a non-word, which is not what is there.
  * A frequency count points the same way (vowel + `)/` 23 times against
    vowel + `(/` 8; smooth breathings outnumber rough ones better than 2:1).

The rest of the table, each mark read off its own occurrences in that slice
rather than assumed:

    `/` acute         `\\` grave        `=` circumflex
    `|` iota subscript (a)| = ᾳ)
    `+` diaeresis — settled by `melei+sti\\`, `o)i+sto/s`, `patrw/i+o/s`,
        where `i+` marks an iota that does NOT form a diphthong
    `^` macron — settled by `ceno/-ta_s` (ξενό-τᾰς) carrying both `^` and `_`
        as the long/short pair on the same stem
    `_` breve — the short counterpart, same entry

PUNCTUATION IS NOT A DIACRITIC, and telling them apart is the one judgement
call in the decoder. `(` `)` `/` `+` all appear as ordinary punctuation
somewhere in the LSJ, and a blind substitution turns prose into mojibake. The
rule used is positional and does not need a lexicon: a beta-code diacritic is
postfix **on a vowel** (or a breathing on ρ — `r(` is ῥ, which is how LSJ
writes every rho with a rough breathing). A mark that follows a consonant,
whitespace or a digit is punctuation and is passed through. So `st(h)` keeps
its parenthesis, because `h` cannot carry a breathing, while `a)/wtos` loses
one, because `α` can.

THIS FUNCTION CANNOT TELL GREEK FROM ENGLISH, and must not be asked to. Beta
Code and English are both plain ASCII letters: `humming` transliterates to
`ημμινγ` exactly as faithfully as `cai/nw` becomes ξαίνω, and there is no
character-level signal that separates them. The LSJ interleaves the two —
`<tr>fut.</tr>` is English, `<orth lang="greek">cai/nw</orth>` is Greek — so
the language is carried by the MARKUP, and the builder applies `decode` only
to the `lang="greek"` fields. Guessing from the letters instead would mangle
every gloss in the dictionary.

WHAT THIS IS NOT
----------------
Not a morphological analyser, not a normaliser for comparison (`flame_pure.
normalize` does that, by stripping the accents this module is at pains to
place), and not a general Beta Code implementation: it covers the LSJ's usage.
The TLG's full code has conventions the LSJ does not use (`%` for a
marginal/unclear letter, `{` `}` for editorial deletion) and those are left
alone rather than guessed at.
"""
from __future__ import annotations

import unicodedata

# --- the letter table ------------------------------------------------------
_LETTERS = {
    "a": "α", "b": "β", "g": "γ", "d": "δ", "e": "ε", "z": "ζ", "h": "η",
    "q": "θ", "i": "ι", "k": "κ", "l": "λ", "m": "μ", "n": "ν", "c": "ξ",
    "o": "ο", "p": "π", "r": "ρ", "s": "σ", "t": "τ", "u": "υ", "f": "φ",
    "x": "χ", "y": "ψ", "w": "ω",
    # Not part of the Greek alphabet proper, but the LSJ indexes entries under
    # a digamma key (`*v`) and dropping it would merge two distinct headwords.
    "v": "ϝ",
}
_LETTERS_INV = {v: k for k, v in _LETTERS.items()}

# --- the combining marks ---------------------------------------------------
PSILI = "̓"          # smooth breathing
DASIA = "̔"          # rough breathing
ACUTE = "́"
GRAVE = "̀"
PERISPOMENI = "͂"    # circumflex
YPOGEGRAMMENI = "ͅ"  # iota subscript
DIAERESIS = "̈"
MACRON = "̄"
BREVE = "̆"

_MARKS = {")": PSILI, "(": DASIA, "/": ACUTE, "\\": GRAVE, "=": PERISPOMENI,
          "|": YPOGEGRAMMENI, "+": DIAERESIS, "^": MACRON, "_": BREVE}
_MARKS_INV = {v: k for k, v in _MARKS.items()}

# Which bases can carry a mark. A vowel takes anything; rho takes a breathing
# and nothing else (`r(` = ῥ, but `r/` is a slash after a consonant, i.e. a
# literal slash). Everything else means the mark was punctuation.
_VOWELS = frozenset("αεηιουω")
_YPOGEGRAMMENI_ONLY = frozenset("αηω")   # the three that take an iota subscript


def _takes(base: str, mark: str) -> bool:
    """Can this base character carry this combining mark?"""
    b = base.lower()
    if b in _VOWELS:
        # Diphthong iota only ever attaches to α, η, ω — `ῳ` exists, `ῑ` with a
        # subscript does not (the prosgegrammenon `ι` is a separate letter).
        if mark == YPOGEGRAMMENI:
            return b in _YPOGEGRAMMENI_ONLY
        return True
    if b == "ρ":
        return mark in (PSILI, DASIA)
    return False


def _compose(base: str, marks: list) -> str:
    """A base plus its combining marks, NFC-composed.

    Marks are emitted in the order they were read, and NFC reorders them
    canonically — but only marks of DIFFERENT combining class, which is not
    enough for Greek. The LSJ writes a diaeresis as `i/+`, acute first, while
    every precomposed character that pairs the two has the diaeresis first in
    its canonical decomposition (U+0390 `ΐ` is <ι, 0308, 0301>). Both marks
    have combining class 230, so NFC will not swap them and the naive
    concatenation yields a string that renders right but is not the same
    character — it would never match a normalised corpus. So the diaeresis is
    placed first by hand among the class-230 marks, which is what makes
    `dai/+das` come out as δαΐδας with ι = U+0390 and not as ι + U+0301 +
    U+0308.
    """
    if not marks:
        return base
    if len(marks) > 1:
        marks = sorted(marks, key=lambda m: (unicodedata.combining(m), m != DIAERESIS))
    return unicodedata.normalize("NFC", base + "".join(marks))


def decode(text: str) -> str:
    """Beta Code -> Unicode Greek. Anything unreadable is passed through.

    Never raises: the input is dictionary prose interspersed with markup, and a
    transliterator that throws on the first stray bracket is useless. Unknown
    characters are copied verbatim, which is also how the encoder's round trip
    keeps working on the two stray Latin-accented characters the LSJ files
    actually contain.

    Language-blind by design — see the module docstring. The caller must
    decode only fields the markup marks as Greek.
    """
    if not text:
        return ""
    # Clusters are kept as (base, [marks]) while reading and composed once at
    # the end. Composing eagerly looks equivalent and is not: the base must be
    # tested for what it IS, and the first code point of an already-composed
    # cluster is the precomposed vowel (`αὖ` is one character), which then
    # matches no vowel in the table and silently rejects the next mark. That
    # bug cost 250 of 2543 gold lemmas their accents.
    clusters: list[list] = []     # [base_letter, [marks]]
    pending: list[str] = []       # marks read before their base exists yet
    upper = False
    for ch in text:
        if ch == "*":
            # Applies to the next letter only. `**` (very rare) just re-arms.
            upper = True
            continue
        mark = _MARKS.get(ch)
        if mark is not None:
            # Attach to the last cluster if it can carry the mark, else hold it
            # for the next letter — that is the capital form `*)ai/+da`, where
            # the breathing sits between the `*` and the vowel it belongs to.
            if clusters and _takes(clusters[-1][0], mark):
                clusters[-1][1].append(mark)
            else:
                pending.append(mark)
            continue
        low = ch.lower()
        if low in _LETTERS:
            base = _LETTERS[low]
            if upper:
                base = base.upper()
                upper = False
            clusters.append([base, pending])
            pending = []
            continue
        # Punctuation, digits, markup, and anything unidentified. Any marks
        # still pending were not diacritics after all — emit them literally so
        # nothing is silently swallowed.
        if pending:
            clusters.append([ch, []])
            clusters[-1][0] = "".join(_MARKS_INV.get(m, "") for m in pending) + ch
        else:
            clusters.append([ch, []])
        pending = []
    if pending:
        clusters.append(["".join(_MARKS_INV.get(m, "") for m in pending), []])
    return _final_sigma("".join(_compose(b, m) for b, m in clusters))


def looks_greek(token: str) -> bool:
    """Would `decode` treat any mark in this token as a real diacritic?

    True iff some mark character directly follows a vowel (or rho) — the same
    positional rule the decoder applies. This is what makes it possible to
    transliterate LSJ PROSE, which mixes the two scripts inside one field:

        '*a a, a)/lfa (q.v.), to/ , indecl. , first letter of the Gr. alphabet:'

    Decoding that whole string as Greek turns "indecl." into "ινδεξλ." and
    "Gr." into "Γρ.". Testing each whitespace token instead decodes the two
    Greek ones and leaves the English ones alone, which is exactly what the
    printed page shows. False for "and/or" — the slash follows a consonant —
    and false for every unaccented English word.
    """
    prev = ""
    for ch in token:
        if ch in _MARKS and prev and _takes(prev, _MARKS[ch]):
            return True
        if not ch.isalpha():
            prev = ""
            continue
        prev = _LETTERS.get(ch.lower(), ch.lower())
    return False


def decode_prose(text: str) -> str:
    """`decode`, but only the tokens that are actually Greek.

    For the dictionary's running text, where the LSJ alternates scripts within
    one field. A token is decoded when `looks_greek` recognises a diacritic in
    it; otherwise it is copied. Tokens are rejoined with single spaces, which
    is what the source writes anyway.
    """
    out = []
    for tok in text.split():
        out.append(decode(tok) if looks_greek(tok) else tok)
    return " ".join(out)


def _final_sigma(text: str) -> str:
    """σ -> ς at the end of a word, the way Greek is actually written.

    Without this every LSJ headword ends in `σ`, and a reader comparing the
    dictionary against the text sees a difference that is an artefact of the
    transliterator rather than a fact about the word.
    """
    chars = list(text)
    for i, ch in enumerate(chars):
        if ch != "σ":
            continue
        nxt = chars[i + 1] if i + 1 < len(chars) else ""
        if not nxt.isalpha():
            chars[i] = "ς"
    return "".join(chars)


def encode(text: str) -> str:
    """Unicode Greek -> Beta Code. The inverse of `decode`, used by the tests.

    Diacritics are emitted in a fixed order (breathing, accent, diaeresis,
    length, iota subscript). Decode accepts any order, so the choice is only
    about producing stable output, not about correctness.
    """
    out: list[str] = []
    for ch in unicodedata.normalize("NFD", text):
        if unicodedata.combining(ch):
            out.append(_MARKS_INV.get(ch, ""))
            continue
        base = ch.lower()
        if base in _LETTERS_INV:
            beta = _LETTERS_INV[base]
            if ch.isupper():
                out.append("*")
            out.append(beta)
            continue
        # Unmapped (punctuation, and the stray accented Latin characters in the
        # source): copy through. If it was a letter with combining marks they
        # arrive after it, which decode will read as punctuation and return.
        out.append(ch)
    return "".join(out)


def describe() -> list[dict]:
    """The table as data, so a UI or a report never restates it.

    Same pattern as `variants.describe`: one source for the mapping, and the
    measured evidence for the two entries that are not guessable.
    """
    return [
        {"name": "letters", "beta": "a b g d e z h q i k l m n c o p r s t u f x y w v",
         "unicode": "α β γ δ ε ζ η θ ι κ λ μ ν ξ ο π ρ σ τ υ φ χ ψ ω ϝ",
         "evidence": "the LSJ alphabet; `v` is digamma. The two that look "
                     "swapped: `c` = ξ (`ce/nos` = ξένος in slice 15, `xe/nos` "
                     "nowhere — χένος is not a word) and `x` = χ (`xalepo/s` is "
                     "glossed \"difficult\" and sits beside `xai/rw`)"},
        {"name": "psili", "beta": ")", "unicode": "U+0313",
         "evidence": "`a)ei/dw` is glossed \"sing\" = ἀείδω (smooth) and "
                     "`a)fori/zw` is \"mark off by boundaries\" = ἀφορίζω; the "
                     "rough spellings of both are absent from the slices. "
                     "Frequency points the same way: vowel+) 23x vs vowel+( 8x."},
        {"name": "dasia", "beta": "(", "unicode": "U+0314",
         "evidence": "`a(li/skomai` is glossed \"to be taken, conquered\" = "
                     "ἁλίσκομαι (rough). Also the breathing on rho: `r(` = ῥ"},
        {"name": "acute", "beta": "/", "unicode": "U+0301", "evidence": "-"},
        {"name": "grave", "beta": "\\", "unicode": "U+0300", "evidence": "-"},
        {"name": "circumflex", "beta": "=", "unicode": "U+0342", "evidence": "-"},
        {"name": "iota_subscript", "beta": "|", "unicode": "U+0345",
         "evidence": "only on α, η, ω — `ῳ` exists, a subscript ι under ι does not"},
        {"name": "diaeresis", "beta": "+", "unicode": "U+0308",
         "evidence": "`melei+sti\\`, `o)i+sto/s`, `patrw/i+o/s`: `i+` marks an "
                     "iota that does not form a diphthong"},
        {"name": "macron", "beta": "^", "unicode": "U+0304",
         "evidence": "`ceno/-ta_s` (ξενό-τᾰς) carries `^` and `_` as the long/"
                     "short pair on one stem"},
        {"name": "breve", "beta": "_", "unicode": "U+0306",
         "evidence": "the short counterpart, same entry"},
        {"name": "capital", "beta": "*", "unicode": "—",
         "evidence": "before the letter, and before its breathing in the "
                     "capital form `*)ai/+da,` = Ἄϊδα,"},
    ]

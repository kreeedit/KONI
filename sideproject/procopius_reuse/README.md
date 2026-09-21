# Procopius reuse study — source TEI corpus

A side-project growing out of KONI: studying how Procopius reworks Thucydides
and Herodotus. This folder holds the open **source TEI** for the three authors,
saved into the repo (not under `data/`, which is gitignored) so the side-project
has a stable, redistributable corpus of its own.

## Contents

| File | Author / work | CTS URN | Print edition (TEI sourceDesc) |
| :--- | :--- | :--- | :--- |
| `tei/tlg0003/tlg0003.tlg001.perseus-grc2.xml` | Thucydides, *Historiae* | `urn:cts:greekLit:tlg0003.tlg001` | ed. Henry Stuart Jones, Oxford UP 1910/1942 (Internet Archive) |
| `tei/tlg0016/tlg0016.tlg001.perseus-grc2.xml` | Herodotus, *Historiae* | `urn:cts:greekLit:tlg0016.tlg001` | ed. A.D. Godley, Loeb Classical Library, Harvard UP / Heinemann 1920–25 (Internet Archive) |
| `tei/tlg4029/tlg4029.tlg001.perseus-grc2.xml` | Procopius, *de Bellis* | `urn:cts:greekLit:tlg4029.tlg001` | ed. Henry Bronson Dewing, Loeb Classical Library, Heinemann / Putnam 1914–28 (Internet Archive) |

Only Procopius *de Bellis* is included (not the *Anecdota*, `tlg4029.tlg002`),
per the study scope. Thucydides and Herodotus are confirmed open texts
(`cts_confirmed=true` in the KONI canon); Procopius *de Bellis* is in the
PerseusDL/canonical-greekLit repo but flagged `cts_confirmed=false` in the KONI
canon because the modern CTS GetCapabilities inventory does not list it — the
file nonetheless exists in the repo and is included here.

## Provenance & license

These files are verbatim copies from the
[`PerseusDL/canonical-greekLit`](https://github.com/PerseusDL/canonical-greekLit)
GitHub repository, fetched at:

```
https://raw.githubusercontent.com/PerseusDL/canonical-greekLit/master/data/tlg<aid>/tlg<wid>/<file>
```

The filenames (`tlg<aid>.tlg<wid>.perseus-grc2.xml`) are the canonical-greekLit
source names, kept for traceability. The TEI `publicationStmt` credits the
publisher as **Trustees of Tufts University / Perseus Digital Library Project**.

**License: CC BY-SA 4.0** (Creative Commons Attribution-ShareAlike 4.0
International), as stated in each file's TEI `availability` element. This
**overrides** the repository's MIT code license for these three files
specifically: any derivative of *these texts* must also be CC BY-SA 4.0,
with attribution to the Perseus Digital Library and the print editors named
above. KONI's own code, schema, and docs remain MIT/CC0 as in the root
`LICENSE`/`NOTICE`.

## Important caveat — no critical apparatus in the open TEI

These are **reading texts, not critical editions**. Verification (counting
TEI apparatus elements) shows:

- Procopius *de Bellis* (Dewing): **0** `<app>`/`<lem>`/`<rdg>` elements — no
  critical apparatus.
- Thucydides (Jones): 0 apparatus elements.
- Herodotus (Godley): the 86 `<note>` elements are scan-provenance notes
  ("Text scanned at U. Chicago in 1988-9…"), **not** a scholarly apparatus; 0
  mention Thucydides or Herodotus.

The real critical apparatus for Procopius (the Teubner Haury–Wirth edition)
lives in printed/subscription editions, not the open TEI.

For the record, the one in-text mention of Herodotus in Procopius *de Bellis*
is the author's **own explicit citation** at **8.6.12** —
*"ὁ τοίνυν Ἁλικαρνασεὺς Ἡρόδοτος ἐν τῇ τῶν ἱστοριῶν τετάρτῃ φησί…"*
("the Halicarnassian Herodotus in the fourth of his Histories says…") — the
continents-naming passage, the same example used in the KONI README's Flame
worked example (de Bellis 8.6 ↔ Herodotus 4.45).

## Apparatus recovered from local PDFs (`raw_pdfs/`, gitignored)

The originally-blocked plan — counting how often Procopius's apparatus cites
Thucydides/Herodotus, and listing correspondences researchers already noted —
**can now be carried out** from local copyright-protected scans kept in
`raw_pdfs/` (not committed):

- the **Haury–Wirth Teubner** critical edition, *Procopius Caesariensis Opera
  Omnia* (de Gruyter reissue) — Vol. I de Bellis I–IV, Vol. II de Bellis
  V–VIII, Vol. III Historia Arcana, Vol. IV De Aedificiis;
- the **Kaldellis** translation, *The Wars of Justinian* (HUP 2014), whose
  footnotes are a modern scholar's explicit list of Procopius↔classical
  parallels.

`scripts/extract_apparatus_citations.py` extracts both with `pdftotext` and
writes `reports/procopius_classical_citations.md`. Because the Haury OCR
mangles Greek and splits Roman numerals, the Haury lines are emitted verbatim
for manual review (with *Herodianos* — a Gothic commander, not Herodotus —
filtered out), while the clean Kaldellis footnotes are parsed. Headline
counts:

- **Kaldellis**: 52 Thucydides + 10 Herodotos footnote citations with explicit
  book/section references — the richest "correspondences already noted" list.
- **Haury apparatus**: de Bellis I–IV (5 Thuc. / 4 Hdt.), de Bellis V–VIII
  (4 / 4), Historia Arcana (0 / 0 — its apparatus cites Suidas, not the
  classical historians), De Aedificiis (4 / 3, refs truncated by OCR).
- Haury's prolegomena also records the prior scholarship (Braun 1885; Duwe) —
  the studies of Procopius's imitation of Thucydides/Herodotus.

Only **factual citations** (author + reference) leave `raw_pdfs/`; the PDFs
and verbatim apparatus text are gitignored (`.gitignore`).

## How these texts *can* still serve the study

Since the apparatus is absent, the viable path is **direct text reuse** on the
Greek itself — which is what KONI's Flame engine is built for. Running Flame on
Procopius *de Bellis* against Thucydides and Herodotus surfaces
correspondences from the primary text, independently of what any editor chose
to annotate. That analysis is intentionally left out of this save step; it is
the next stage of the side-project.
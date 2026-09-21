#!/usr/bin/env python3
"""Extract Thucydides / Herodotus citations from the Procopius apparatus PDFs.

The Procopius-reuse side-project originally could not count how often
Procopius's *apparatus* cites Thucydides/Herodotus, because the open TEI
reading text has no critical apparatus (see ../README.md). This script works
from the local `raw_pdfs/` instead — the Haury-Teubner critical edition
(de Gruyter reissue, 4 vols.) and the Kaldellis translation of the *Wars*
(HUP 2014), extracted with `pdftotext`.

Two source layers, two confidence levels:

* **Kaldellis (procopius2014.pdf)** — clean English footnotes of the form
  "Thucydides, History 2.65.6" / "Herodotos, Histories 1.80". OCR is good, so
  references are parsed into (work, book, section) and listed directly.

* **Haury apparatus (the four de Gruyter PDFs)** — Latin abbreviations
  ("Thuc.", "Thucyd.", "Herod.", "Hdt.", "Herodoto/Herodotum/Herodoti"). The
  pdftotext OCR mangles Greek badly and splits Roman numerals ("VII" -> "V I I"),
  so references are *not* parsed; the matched lines are emitted verbatim, flagged
  for manual review, and Herodianos (a Gothic commander in Procopius, *not*
  Herodotus) is filtered out.

IMPORTANT — copyright: the PDFs and the pdftotext output are copyrighted
(Haury/de Gruyter; Kaldellis/HUP). They are gitignored (see ../.gitignore).
This script emits only **derived factual citations** (author + reference), not
verbatim apparatus prose beyond the short matched fragment needed to identify
a citation. Do not commit the cache or the PDFs.

Pure stdlib. Run from anywhere:

    python3 scripts/extract_apparatus_citations.py

Writes ../reports/procopius_classical_citations.md.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PDF_DIR = ROOT / "raw_pdfs"
CACHE = ROOT / ".cache_pdftotext"
REPORT = ROOT / "reports" / "procopius_classical_citations.md"

# ---------------------------------------------------------------------------
# PDF -> text
# ---------------------------------------------------------------------------

def ensure_text(pdf: Path) -> str:
    if not pdf.exists():
        sys.exit(f"missing PDF: {pdf}")
    txt = CACHE / (pdf.stem + ".txt")
    if not txt.exists():
        CACHE.mkdir(exist_ok=True)
        subprocess.run(["pdftotext", str(pdf), str(txt)], check=True,
                       stderr=subprocess.DEVNULL)
    return txt.read_text(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Volume identification (probe the title page)
# ---------------------------------------------------------------------------

HAURY_VOLS = {
    "I": ("DE BELLIS LIBRI I - I V", "de Bellis I–IV"),
    "II": ("DE Β ELLIS LIBRI V - Vili", "de Bellis V–VIII"),
    "III": ("HISTORIA QVAE DICITVR ARCANA", "Historia Arcana (Anecdota)"),
    "IV": ("ΠΕΡΙ ΚΤΙΣΜΑΤΩΝ", "De Aedificiis"),
}


def identify_haury(text: str) -> str:
    head = "\n".join(text.splitlines()[:120])
    for key, (sig, _label) in HAURY_VOLS.items():
        if sig in head:
            return key
    # fall back on fuzzy: just look for the roman numerals + DE BELLIS / ARCANA / AEDIFICIIS
    h = head.upper()
    if "ARCANA" in h:
        return "III"
    if "AEDIFICIIS" in h or "KTISMATWN" in text[:4000].upper():
        return "IV"
    if "DE BELLIS LIBRI V" in h:
        return "II"
    if "DE BELLIS LIBRI I" in h:
        return "I"
    return "?"


# ---------------------------------------------------------------------------
# Kaldellis (clean English) — parsed citations
# ---------------------------------------------------------------------------

THUC_REF = re.compile(r"History\s+(\d+\.\d+(?:\.\d+)?(?:[-–]\d+)?)")
HEROD_REF = re.compile(r"Histories\s+(\d+\.\d+(?:\.\d+)?(?:[-–]\d+)?(?:\.\d+)?)")


def kaldellis_citations(text: str) -> list[tuple[str, str, int]]:
    """Return (author, reference, line_no) for parsed footnote citations."""
    out: list[tuple[str, str, int]] = []
    for i, line in enumerate(text.splitlines(), 1):
        if "Thucydides" in line:
            for m in THUC_REF.finditer(line):
                out.append(("Thucydides", m.group(1), i))
        if "Herodotos" in line:
            for m in HEROD_REF.finditer(line):
                out.append(("Herodotos", m.group(1), i))
    return out


# ---------------------------------------------------------------------------
# Haury (Latin, OCR-noisy) — raw matched lines, Herodianos filtered
# ---------------------------------------------------------------------------

# Match Herodotus/Thucydides in Latin apparatus forms, but NOT Herodianos/us.
# Use bare stems with word boundaries: a trailing dot (Thuc., Hdt.) is matched
# by the stem + \b, since '.' is a word boundary after a word char.
HAURY_THUC = re.compile(r"\b(Thucydides?|Thucydidem|Thucyd|Thuc)\b", re.IGNORECASE)
HAURY_HEROD = re.compile(r"\b(Hdt|Herodotum|Herodoto|Herodotos|Herodoti|Herodotis|Herod)\b", re.IGNORECASE)
HERODIANOS = re.compile(r"Herodian(os|us|o|um|am)?", re.IGNORECASE)


def haury_lines(text: str, author: str) -> list[tuple[int, str]]:
    rx = HAURY_THUC if author == "Thucydides" else HAURY_HEROD
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        if not rx.search(line):
            continue
        if author == "Herodotos" and HERODIANOS.search(line):
            # only drop if the match is actually the Herodianos person and no
            # genuine Herodot* form is present outside it
            cleaned = HERODIANOS.sub("", line)
            if not HAURY_HEROD.search(cleaned):
                continue
        hits.append((i, line.strip()))
    return hits


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def main() -> int:
    if not PDF_DIR.exists():
        sys.exit(f"raw_pdfs/ not found at {PDF_DIR}")
    CACHE.mkdir(exist_ok=True)

    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    if not pdfs:
        sys.exit("no PDFs in raw_pdfs/")

    kaldellis_pdf = next((p for p in pdfs if p.stem == "procopius2014"), None)
    haury_pdfs = [p for p in pdfs if p.stem.startswith("10.1515")]

    lines: list[str] = []
    lines.append("# Procopius — apparatus citations of Thucydides & Herodotus\n")
    lines.append(
        "Derived from the local `raw_pdfs/` (gitignored, under copyright):\n"
        "the Haury–Wirth Teubner critical edition (de Gruyter reissue) and the\n"
        "Kaldellis translation of the *Wars* (HUP 2014). Extracted with "
        "`pdftotext`.\n"
    )
    lines.append(
        "> Only **factual citations** (author + reference) are reported here.\n"
        "> The PDFs and verbatim apparatus text are not committed (see "
        "`.gitignore`).\n\n"
    )

    # ---- Kaldellis -------------------------------------------------------
    if kaldellis_pdf:
        kt = ensure_text(kaldellis_pdf)
        kc = kaldellis_citations(kt)
        thuc = [c for c in kc if c[0] == "Thucydides"]
        herod = [c for c in kc if c[0] == "Herodotos"]
        lines.append("## 1. Kaldellis translation (procopius2014.pdf) — parsed\n")
        lines.append(
            "Kaldellis's own footnotes explicitly cite the classical model for "
            "Procopius's *Wars*. OCR is clean, so references are parsed. These "
            "are the 'correspondences researchers already noted' that the open "
            "TEI could not supply.\n"
        )
        lines.append(f"- Thucydides citations: **{len(thuc)}**")
        lines.append(f"- Herodotos citations: **{len(herod)}**\n")
        lines.append("### Thucydides\n")
        lines.append("| # | Thucydides ref | note line |")
        lines.append("|---|---|---|")
        for n, (_a, ref, ln) in enumerate(thuc, 1):
            lines.append(f"| {n} | History {ref} | {ln} |")
        lines.append("\n### Herodotos\n")
        lines.append("| # | Herodotos ref | note line |")
        lines.append("|---|---|---|")
        for n, (_a, ref, ln) in enumerate(herod, 1):
            lines.append(f"| {n} | Histories {ref} | {ln} |")
        lines.append("")

    # ---- Haury -----------------------------------------------------------
    lines.append("## 2. Haury–Wirth Teubner apparatus — manual-review lines\n")
    lines.append(
        "The apparatus cites parallels in Latin abbreviations "
        "(*Thuc.*, *Thucyd.*, *Herod.*, *Hdt.*, *Herodoto/Herodotum/Herodoti*). "
        "The pdftotext OCR mangles Greek and splits Roman numerals "
        "(e.g. `VII` → `V I I`), so references are **not** parsed here; the "
        "matched lines are listed verbatim for manual review. "
        "*Herodianos* — a Gothic/Byzantine commander in Procopius, **not** "
        "Herodotus — has been filtered out of the Herodotus set.\n"
    )
    haury_vols = []
    for p in haury_pdfs:
        t = ensure_text(p)
        vol = identify_haury(t)
        haury_vols.append((vol, p, t))

    # sort by volume roman
    order = {"I": 0, "II": 1, "III": 2, "IV": 3, "?": 9}
    haury_vols.sort(key=lambda x: order.get(x[0], 9))

    for vol, p, t in haury_vols:
        label = HAURY_VOLS.get(vol, ("?", "?"))[1]
        thuc_h = haury_lines(t, "Thucydides")
        herod_h = haury_lines(t, "Herodotos")
        lines.append(f"### Vol. {vol} — {label} (`{p.name}`)\n")
        lines.append(f"- Thucydides hits: **{len(thuc_h)}**")
        lines.append(f"- Herodotos hits: **{len(herod_h)}** (Herodianos filtered)\n")
        for author, hits in (("Thucydides", thuc_h), ("Herodotos", herod_h)):
            if not hits:
                continue
            lines.append(f"**{author}:**\n")
            for ln, txt in hits:
                # trim very long lines
                show = txt if len(txt) <= 160 else txt[:157] + "..."
                lines.append(f"- `l.{ln}` {show}")
            lines.append("")

    # ---- Bibliography note ------------------------------------------------
    lines.append("## 3. Prior scholarship recorded in Haury's prolegomena/indices\n")
    lines.append(
        "Haury's front matter records the earlier studies of Procopius's "
        "imitation of the classical historians, recovered here from the OCR:\n"
    )
    bib = [
        "Braun, H., *Procopius Caesariensis quatenus imitatus sit Thucydidem*, "
        "Diss. Erlangen 1885.",
        "Braun, H., *Die Nachahmung Herodots durch Prokop*, Progr. (cf. also "
        "*Die Nachahmung Thucydides' durch Prokop*).",
        "Duwe, A., *Quatenus Procopius Thucydidem imitatus sit*, Progr.",
    ]
    for b in bib:
        lines.append(f"- {b}")
    lines.append(
        "\nThese are exactly the 'correspondences researchers already noted' "
        "that the README's original plan wanted to list.\n"
    )

    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
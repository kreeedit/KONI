# Contributing to KONI

KONI is an open cross-reference and authority layer for the classical-philology
canon, built from public sources. You do **not** need to produce TLG-compatible
TEI to contribute — the point of KONI is to provide the *linking layer* that
lets any open TEI edition slot into the wider digital-classics ecosystem. If
you publish an open TEI edition, KONI can connect it.

## The two kinds of contribution

### 1. Close a gap (open-data work)

Run `python scripts/build_gaps_report.py` and read `reports/gaps_report.md`.
Each entry is a place where open metadata, an open text, or an authority link
is missing. The most useful kinds of contribution:

- **A Wikidata `P3576` (TLG author ID) statement** for an author currently
  unmatched (`### No Wikidata match` in the gaps report). This is a one-line
  edit on Wikidata (CC0) and it immediately gives that author a
  `skos:exactMatch` to Wikidata in the next KONI build.
- **A VIAF reconciliation** for an author with no VIAF id. VIAF is currently
  0% coverage in KONI because it relies on the sparse Wikidata `P214` property;
  adding `P214` on Wikidata, or pointing KONI at an alternative open VIAF
  source, raises authority-graph coverage.
- **An open TEI edition** for a work flagged `proposed` (`### Works with no
  open text yet`). Publishing the edition and registering its CTS URN closes
  the gap: the work moves from `koni:proposed` to a dereferenceable
  `skos:exactMatch` in the next build. *You need not open the underlying text
  of a subscription edition* — a freshly produced open TEI edition is ideal.

### 2. Report a missing link / correction

If you notice a wrong or missing identifier (Wikidata Q, VIAF, CTS URN,
edition), the lightest way to contribute is to open an issue titled
`gap: <TLG id or author>` describing the missing link and a public source for
it. A maintainer will fold it into the next build.

## What KONI will *not* accept

- TLG-derived data from the subscription service, or scraped from the TLG
  website. KONI rebuilds locally on a machine with lawful access and does not
  redistribute TLG-derived canon data (see `NOTICE`). Do not submit such data.
- Editions or metadata that are not openly licensed. The publishable
  `canon-links.nt` subset is CC0 Wikidata/VIAF/Scaife edges only.

## How a contribution flows

1. You add the open statement (Wikidata / VIAF) or publish the open TEI edition.
2. A maintainer reruns the ETL pipeline (`fetch_sources.py` → `build_canon.py`
   → `build_jsonld.py --links` → `build_gaps_report.py`).
3. Your contribution appears as a closed gap in `reports/gaps_report.md` and as
   a new `skos:exactMatch` in `canon-links.nt`.

This is the self-reinforcing cycle KONI is designed around: signal the gap → a
contributor closes it → KONI reflects the closed gap.
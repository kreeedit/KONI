# KONI — Open TLG Canon

**KONI** = *Koiné Online Nexus of Integration* — the open TLG canon and Greek
text reader (formerly OPENtgl).

> **Full overview (what it does and how it works): [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)**

An open, machine-readable reconstruction of the **TLG (Thesaurus Linguae Graecae)
canon**: the author/work index that assigns every author a 4-digit identifier
(Homer = `0012`) and every work a 3-digit identifier (Iliad = `001`).

The official TLG exposes this master list freely and without subscription, but
only as HTML pages — not as a downloadable database. KONI scrapes those
public pages and the authoritative Perseus CTS inventory, normalizes them, and
exports the canon as `canon.json` (tree) and `canon.csv` (flat) so that tools
like Diogenes or Perseus and the wider digital classics community can use it
directly.

## Sources

| Source | URL | What it gives |
|---|---|---|
| TLG classic canon | `https://stephanus.tlg.uci.edu/tlgauthors/cd.authors.php` | 1823 authors (ID + Latin name + epitheton) — **no works** |
| TLG post-E canon | `https://stephanus.tlg.uci.edu/tlgauthors/post_tlg_e.php` | post-E/Byzantine authors **and works** |
| Perseus CTS inventory | `https://cts.perseids.org/api/cts?request=GetCapabilities` | 473 authors / 2482 works with CTS URNs + Greek (`grc`) titles |
| bcdavasconcelos list | `https://github.com/bcdavasconcelos/Greek-Authors-and-Works-in-TLG` (`main_list.md`) | secondary classic-works supplement |

The classic canon's works are **not** in the public TLG HTML; they are
reconstructed from the Perseus CTS inventory (primary) and bcdavasconcelos
(secondary, for works beyond the Perseus subset).

## Data model

`canon.json` is keyed by 4-digit author ID; each author has a `works` map keyed
by 3-digit work ID. See `schema/canon.schema.json`. Highlights:

- `cts_urn` — always `urn:cts:greekLit:tlg{AUTHOR4}.tlg{WORK3}` (synthesized).
- `cts_confirmed` — `true` if the work exists in the Perseus CTS inventory
  (real text), `false` if it only comes from TLG. Honest provenance.
- `author_name_greek` / `title_greek` — from CTS `grc` labels, where available.
- `era` — best-effort from Wikidata (P569/P570 + P2348); covers ~35% of authors.
- `viaf_id` — VIAF identifier from Wikidata P214 (no direct VIAF API call).
- `source` — list of origins for each author (auditability).

## Usage

```bash
# No dependencies — Python stdlib only.
python scripts/fetch_sources.py            # download + cache sources to data/raw/
python scripts/build_canon.py             # parse + enrich + Diogenes export -> canon.json/csv, build_report.md
python scripts/validate_canon.py          # validate against schema
```

`fetch_sources.py` caches; pass `--refresh` to re-download. `build_canon.py`
runs the whole pipeline from cache if present.

## Limitations

- **Classic canon works** are not in the public TLG HTML. Coverage depends on
  the CTS inventory (473 authors / 2482 works) + bcdavasconcelos; gaps are
  reported in `reports/build_report.md`, never silently dropped.
- **VIAF is blocked** from this environment (Cloudflare 403), so author era
  enrichment uses Wikidata P214/P569/P570/P2348 (no VIAF API). `era` covers ~35% of authors (best-effort).
- **Greek author names** appear only where the CTS inventory provides a `grc`
  groupname/label; otherwise `null`.
- TLG epitheta (e.g. "Epic.", "Phil.") are **genre**, not era.

## Layout

```
scripts/         fetch + parse + enrich + build + validate
app/             reader web app (stdlib backend + static frontend)
data/raw/        cached source files
data/intermediate/  parsed per-source JSON
data/texts/      downloaded Greek texts (tlg<auth>/tlg<work>.xml|.json)
schema/          canon.schema.json
reports/         build_report.md coverage statistics
```

## Reader web app

A zero-dependency browser for the canon. Python **stdlib only** (no FastAPI /
pip needed) — runs instantly:

```bash
python scripts/serve.py            # http://127.0.0.1:8000
# open the URL in a browser
```

- **Home / search** (`#/`): live filter by Latin or Greek name, work title, or
  TLG ID. Each result shows the author, epitheton, era, and `readable / total`
  work counts.
- **Author page** (`#/author/<aid>`): era, epitheton, and the works list. 📖
  marks readable works (`cts_confirmed=true`); 🔒 marks works with no open text.
- **Reader** (`#/read/<aid>/<wid>`): two-pane layout — chapter navigation left,
  Greek text center. Controls in the top bar: font size (A−/A+), line height
  (⇕), dark mode (◐). Settings persist via `localStorage`.
- **Typography**: Google Fonts **Cardo** + **Noto Serif Greek** for full polytonic
  Greek support.
- **Text loading**: the backend lazy-fetches each readable work on first open
  and caches under `data/texts/`. Three tiers, tried in order:
  1. **PerseusDL/canonical-greekLit repo** (primary): a `(author,work) → Greek
     TEI filename` map is built from the repo tree (`scripts/build_repo_map.py`,
     auto-built on first start) so the **clean** Greek text is fetched directly —
     this covers works on Perseus that are **NOT** in the modern CTS inventory
     (e.g. TLG 4029 Procopius, *de Bellis*).
  2. **CTS `GetValidReff` + `GetPassage`** via `cts.perseids.org` — First1K /
     CTS-inventory works not in the repo above.
  3. **Perseus Hopper** (`perseus.tufts.edu/hopper`) HTML — a slow fallback for
     anything the repo/CTS lack; chapter text extracted from morph-link anchors,
     cached on disk.
  TEI is parsed to chapters → paragraphs (prose) or numbered lines (verse).

### App files

```
app/
  server.py    stdlib HTTP server + API routes
  canon.py     canon/cts_index loader + search
  tei.py       TEI XML / TXT -> sections/blocks
  texts.py     3-tier lazy text download + cache (repo/CTS/Hopper)
  repo.py      PerseusDL/canonical-greekLit Greek-edition map
  hopper.py    Perseus Hopper HTML fallback
  sources.py   9-source discovery (links)
  static/
    index.html  SPA shell (search / author / reader views)
    app.js      vanilla JS router + rendering + reading controls
    styles.css  premium typography, dark mode, responsive
scripts/
  serve.py            entrypoint (sets up sys.path, runs app.server)
  export_diogenes.py  Diogenes CSV + SQLite export
  build_repo_map.py   rebuild the Perseus repo map
```
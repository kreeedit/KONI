# KONI-LA — Latin feasibility note

This is a *scoping* note, not a build plan. It maps the open Latin source
landscape and identifies the points in the KONI codebase that are currently
Greek/TLG-specific and would need to change for a second corpus module
(`KONI-LA`). No Latin corpus is built here; the goal is to decide whether the
modular extension is realistic and what it would cost.

## Why Latin is the natural next module

Greek and Latin digital infrastructure runs partly in parallel —
TLG / CTS / Wikidata on one side, other Latin canons / CTS / Wikidata on the
other — yet late-antique, Byzantine-reception, and humanist research constantly
crosses the two. A KONI that covers both would be a genuine classical-philology
interoperability layer rather than a single-corpus cross-reference. The
data model (authority list of authors + works, LOD-anchored, gap-signaling) is
corpus-agnostic in principle; only the identifiers, URN namespace, and source
parsers are Greek-specific.

## Open Latin source landscape (candidate sources)

| Source | Role | Open? | Notes |
| :--- | :--- | :--- | :--- |
| **PerseusDL/canonical-latinLit** (CTS `latinLit` namespace) | Primary text + CTS catalogue | Yes (CC BY-SA-ish) | Direct analogue of `canonical-greekLit`; the `parse_cts.py` parser should adapt with a namespace switch. |
| **Scaife** (`scaife.perseus.org`) | Dereferenceable text URIs | Yes | Already used for `exactMatch` on confirmed works; works for Latin CTS URNs unchanged. |
| **PHI / DDP** (Digital Packet on inscriptions/epigraphy) | Epigraphic canon | Partial | Different identifier scheme; not a drop-in CTS source. Lower priority. |
| **Wikidata** | Authority links (Q, VIAF, era) | Yes (CC0) | Latin authors use different Wikidata properties — there is **no** `P3576` equivalent that is uniformly populated. Candidate matching keys to investigate: Latin author VIAF (`P214`), CTS URN (`P11492`? verify), or name+era reconciliation. **This is the central unknown.** |
| **VIAF** | Authority cross-ref | Yes (via `id.loc.gov` JSON; direct API 403s) | Same caveat as the Greek side. |
| **LLT / Brepols** | Critical editions | **No** (subscription) | Excluded, like TLG subscription content. |

The decisive question is **Wikidata reconciliation**: the Greek module's
clean `P3576` exact match is what makes the whole pipeline cheap. Latin has no
single comparable property uniformly populated. Until a reliable open match
key is identified, `KONI-LA` cannot reach the same authority-link coverage as
`KONI-GR` without substantially more reconciliation logic.

## Codebase points that are Greek/TLG-specific (rewrite targets)

These are the concrete places a second module would touch. Listed so the cost
is visible, not as a TODO:

- **`schema/canon.schema.json:41`** — URN pattern
  `^urn:cts:greekLit:tlg[0-9]{4}\.tlg[0-9]{3}$` is hardcoded to the `greekLit`
  CTS namespace and the `tlg` prefix. A modular schema needs a per-corpus URN
  pattern + ID alphabet (Latin works use `phi`-style IDs in some canons).
- **`schema/canon.schema.json`** author-key pattern `^[0-9]{4}$` — TLG's 4-digit
  scheme. A second corpus needs its own ID space (no collision with TLG).
- **`schema/context.jsonld:99` (`build_jsonld.py`)** — `"koni":
  "https://w3id.org/koni/tlg/"` pins the `koni:` URI base to `/tlg/`. A modular
  graph wants per-corpus bases, e.g. `https://w3id.org/koni/la/`.
- **`scripts/build_jsonld.py:153,277`** — synthesized URNs
  `urn:cts:greekLit:tlg{aid}.tlg{wid}` and `koni:{aid}.{wid}` assume greekLit +
  TLG formatting. Must be parameterised by corpus namespace and ID format.
- **`scripts/build_canon.py`** — the pipeline stages (`parse_tlg_cd`,
  `parse_tlg_post`, `parse_cts`, `parse_bcdavasconcelos`) are TLG/Greek
  parsers. A Latin module needs analogous Latin parsers (CTS `latinLit`
  catalogue; a Latin author list). `build_canon.py` would dispatch by corpus.
- **`scripts/wikidata.py`** — the SPARQL query keys on `wdt:P3576`. A Latin
  module needs a different reconciliation query (see the unknown above).
- **`reports/build_report.md`** and the new `build_gaps_report.py` — coverage
  metrics are TLG-flavoured ("Greek name form", `cts_confirmed` semantics).
  Per-corpus sections would replace the single global rollup.

## Proposed modular layout (not built)

```
data/gr/  data/la/                 # per-corpus canon.json, canon.jsonld, links
schema/gr.canon.schema.json  schema/la.canon.schema.json
scripts/build_canon.py --corpus gr|la
scripts/build_jsonld.py --corpus gr|la --links
koni:https://w3id.org/koni/gr/   koni:https://w3id.org/koni/la/
```

`KONI-GR` / `KONI-LA` naming, with later `KONI-SYR` (Syriac), `KONI-COP`
(Coptic), and medieval Latin as longer-term vision.

## Open questions / risks

1. **Wikidata match key for Latin** — the gating unknown. Without a clean
   exact-match property, `KONI-LA` needs fuzzy name+era reconciliation, which
   the Greek module deliberately avoids. This is the single biggest cost
   difference between the two modules.
2. **Canon choice** — which Latin canon is "the" canon? There is no single
   TLG-equivalent authority for Latin; Perseus CTS is a text catalogue, not a
   canon. KONI-LA may need to *construct* its canon from several open lists,
   which is a harder provenance story than the Greek side.
3. **Identifier collision** — TLG 4-digit IDs and any Latin ID scheme must not
   collide in the shared `koni:` namespace; per-corpus URI bases solve this.
4. **Licensing** — Latin open editions are mostly CC BY-SA (Perseus);
   `canon-links.nt`-equivalent CC0 edges come from Wikidata/VIAF as on the
   Greek side. No new licensing risk expected, but `NOTICE` needs a Latin
   section.

## Recommendation

Proceed in two steps, not as a single build:

1. **Reconciliation spike** — resolve the Wikidata match-key question on a
   sample of ~50 well-known Latin authors. If a clean exact-match key exists,
   `KONI-LA` is roughly the same cost as `KONI-GR`; if not, it is materially
   more expensive and should be re-scoped.
2. **Parser + schema spike** — adapt `parse_cts.py` to `latinLit` on one
   sample author and relax the schema URN pattern to be parameterised. This
   validates the mechanical cost independently of the reconciliation question.

Until both spikes pass, `KONI-LA` stays a vision documented here, not a
workstream.
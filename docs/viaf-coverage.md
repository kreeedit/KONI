# VIAF coverage investigation (T3.1)

`reports/build_report.md` reports **VIAF id coverage: 0/3274 (0.0%)**. At face
value this undermines KONI's "Linked Open Data authority graph" framing, so the
cause was investigated rather than assumed.

## Finding: the gap is a stale cache, not a Wikidata gap and not a query bug

1. **The query requests VIAF correctly.** `scripts/wikidata.py` issues, per TLG
   id:
   ```sparql
   ?item wdt:P3576 ?tlg .
   OPTIONAL { ?item wdt:P214 ?viaf }
   ```
   `wdt:P214` is the correct truthy VIAF property, and `P214` has been present
   in the query since the first commit (`ef272a8`).

2. **Wikidata actually holds VIAF for these authors.** A live SPARQL query for
   `0059` (Plato), `0012` (Homer), `0007` (Pindar) returns multiple `P214`
   values each (e.g. Plato → `108159964`, …). Independently confirmed via the
   Wikidata REST entity endpoint: `Q859` carries six `P214` statements and
   `P3576 = "0059"`.

3. **The cache is stale.** `data/intermediate/wikidata_era.json` has mtime
   **2026-06-25**, which *predates the first commit* (2026-06-29). It was built
   during development with an earlier query version that did not yet request
   `P214`, committed as-is, and later git-ignored (`01a763c`). It has never been
   refreshed against the current query, so `viaf_id` is `None` for all 1924
   matched authors despite Wikidata holding the data.

## Fix (recommended next action)

```bash
python scripts/wikidata.py --refresh      # re-query; merge preserves era/greek
python scripts/enrich_canon.py            # propagate viaf_id into canon.json
python scripts/build_canon.py             # rebuild canon + build_report
python scripts/build_jsonld.py --links     # refresh LOD links
python scripts/build_gaps_report.py       # refresh gaps (VIAF column should drop)
```

`wikidata.py --refresh` is merge-safe: only successfully (re)queried IDs are
overwritten, so a partial run (Wikidata WDQS rate-limits to ~1 req/min during
outages) never drops prior era/greek data. Expect ~10 batches × ~62 s.

## Why this matters for the project framing

The "Open Classical Authority Graph" repositioning is only credible if the
authority links are actually populated. VIAF at 0% is not a data-coverage limit
of the source — it is a stale-build artifact. Refreshing it is the single
highest-leverage data-quality action available, and it turns a framing
weakness into a strength. Until the refresh is run, the README/gaps report
should continue to present VIAF coverage as an open gap (which it is, in the
*current* build), not as a fundamental limitation.

## Alternative open sources (if refresh still leaves gaps)

- **Wikidata `P214` back-fill**: for authors matched to a Q but lacking P214 on
  Wikidata, the VIAF cluster id can be looked up via `id.loc.gov` (Library of
  Congress name authority, public) and proposed as a Wikidata `P214` statement.
- **VIAF directly**: the VIAF web API is Cloudflare-403 for scripted access
  (already noted in `build_report.md`), so it is not a viable automated source;
  `id.loc.gov` JSON is the practical open proxy.
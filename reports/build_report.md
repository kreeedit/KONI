# KONI build report

## Summary
- Authors: **3274**
- Works: **8815**
- Authors with at least one work: 2523 (77.1%)

## Coverage
- Works confirmed in the Perseus CTS inventory (`cts_confirmed=true`): 1622/8815 (18.4%)
- Greek editions indexed in the PerseusDL/canonical-greekLit repo: **821**
- Authors with a Greek name (Wikidata P3576): 604/3274 (18.4%)
- Authors with an era (Wikidata P569/P570 + P2348): 1153/3274 (35.2%)
- Authors with a VIAF id (Wikidata P214): 0/3274 (0.0%)
- Works with a Greek title (Perseus CTS): 613/8815 (7.0%)

## Authors by source
- TLG classical canon (cd.authors.php): 1823
- TLG post-E canon (post_tlg_e.php): 1483
- bcdavasconcelos work list: 1904
- Perseus CTS inventory: 349
- Wikidata (P3576): 1924

## Known limitations
- The classical TLG canon (cd.authors.php) lists only authors, not works. The classical works are supplied by the bcdavasconcelos list (broad) and the Perseus CTS inventory (authoritative, with Greek titles).
- `cts_confirmed=false`: the cts_urn is synthesized (`urn:cts:greekLit:tlg<author>.tlg<work>`); the work is in the canon, but the Perseus CTS catalog has no published text (the reader then tries the repo map, CTS, and finally the Hopper).
- The VIAF API cannot be called directly (Cloudflare 403); the VIAF id and the era come from the Wikidata **P214 / P569 / P570 / P2348** properties (P3576 exact matching). The era is best-effort: some authors are `null`.
- The post-E author names keep the TLG mixed lower/upper casing (e.g. `DIONYSIUS HALICARNASSENSIS`) — faithful to the source.
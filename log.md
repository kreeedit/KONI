# Projekt Log

## 2026-07-16 — Bootstrap inicializálva

- Létrehozva: CLAUDE.md, .claudesignore, log.md
- Projekt: KONI — ókori görög szövegek kánon- és korpuszkezelő rendszere (Flame keresőmotorral)
- **TODO:** Következő session: olvasd el a .claudesignore fájlt, majd a log.md-t a munka folytatásához.

## 2026-09-21 — validate_canon.py: 0 hiba helyreállítva (schema/generator mismatch)

**Kiindulás:** a feladat egy „hapax/archaizmus detektor" és egy `view_i/j` ablakozás
hibáinak javítása volt. Ellenőrzés után ezek **nem léteznek a kódban** — nem javítani
kellett, hanem megállapítani, hogy a kiindulás téves:
- `app/flame_pure.py:18` explicit tervezési megjegyzés: `NO agglomerative chaining. NO hapax/archaism.`
- Nincs `is_archaism` / `archaism_count` / `archaism_words` a kódban, a JSON-kimenetben, a TSV-exportőrben, sem a `.bak` mentésekben.
- `grep view_i|view_j` → 0 találat. `SequenceMatcher` sincs; a `git log --follow app/flame_pure.py` egyetlen commitot mutat (`ef272a8`), a `.bak` lánc (12:01→12:34) csak `CAP_SECTIONS 40→20000` és a `compare()`→`compare_iter()` streaming refaktort tartalmazza — nincs visszaállítható „eredeti".
- A Token→Word index map (`s2w`) **már létezik** (`flame_pure.py:69-74`), és a Phase 2 nem is használja: a `_fuzzy_blocks` szólistákon fut, így a blokk-indexek eleve valós szó-indexek → nincs elcsúszás.
- A `CAP_WORDS = 400` vágás a gyakorlatban nem lép be: 5 valós művön mérve 5085 fejezet / 345 265 szó, max fejezet 142 szó → 0 levágott fejezet.

**Valódi hiba, amit találtam:** `validate_canon.py` 1 hibát adott —
`Additional properties are not allowed ('source' was unexpected)` a `canon['1115']['works']['001']`-en.

**Kiváltó ok:** a `apply_supplement.py` work szinten is ír `source` mezőt (skalár provenance-tier),
és a `check_no_restricted.py:27` + `build_jsonld.py:114-120` is `isinstance(src, str)`-ként olvassa —
de a `schema/canon.schema.json` a work blokkban `additionalProperties: false` mellett **nem
definiálta** a `source`-ot (csak author szinten, listaként). A két szint szándékosan tér el:
author = forráskulcsok listája, work = egyetlen tier-string.

**Javítás (2 fájl):**
- `schema/canon.schema.json` — work szintű `source` property hozzáadva:
  `{"type":"string","minLength":1,"pattern":"^(local:curated|restricted:.+)$"}`
- `scripts/apply_supplement.py` — új `_as_source_list()` helper; a `list(sa.get("source") or [...])`
  helyett. A régi kód egy puszta stringet karaktertömbbé aprított (`list("local:curated")`),
  amit a séma (`type:array,items:string`) nem tudott elkapni.

**Verifikáció:** 9 ágenstes független workflow (5 végrehajtó lencse + 3 adversarial cáfoló +
s síntézis), 0 ágenshiba. 2 cáfolat landolt:
- A `source` leírása `'local:curated'`/`'restricted:*'` szókincset hirdetett, de csak
  `minLength`-et kényszerített → `source='restriced:tlg'` (elgépelve) átment a validáción,
  a firewall őrhalmaza üres lett, a `_work_publishable()` `True`-t adott → **a firewall
  helyesírás-függő volt**. Ezt a `pattern` zárja be.
- A `merge()` work szinten listát is elfogadott volna csendben.

**Tesztek (14/14 + round-trip):** valid `'local:curated'`/`'restricted:tlg'` elfogadva;
elgépelt tier, üres string, tömb, int, ismeretlen work/author kulcs, üres author `source`,
hiányzó `cts_confirmed` mind elutasítva. `_as_source_list` mind a 4 esetben helyes.
Round-trip: valós supplement merge → `source='local:curated'`, új author puszta string
`source`-ból → `['local:curated']`, a mutált kánon séma-valid, az ismételt merge idempotens.

**Végállapot:** `validate_canon.py` → `errors: 0 | warnings: 0`, exit 0 (3274 author / 8816 work).
`check_no_restricted.py` → exit 0.

**Módosult fájlok:** `schema/canon.schema.json`, `scripts/apply_supplement.py`

**TODO:**
- A `log.md` 2026-07-16 óta elavult volt — a json-ld / curation / firewall self test /
  `compare_iter` streaming refaktor munkáról nincs bejegyzés. (Ez okozta a téves kiindulást.)
- `build_canon.py` puszta újrafuttatása csendben eldobja a work szintű `source`-t
  (`source` nincs a `required`-ban) → a `1115.001` kiesne a kiadott gráfból. Ez a
  dokumentált pipeline-szemantika (`build_canon` → `apply_supplement`), de érdemes
  megfontolni egy figyelmeztetést a `build_canon.py`-ba.
- `data/canon.csv` / `canon.jsonld` / `.nt` artifactok újragenerálása a javított sémával.
- A work szintű `source` írási útvonala (`apply_supplement.py:56,64`) listát is átenged —
  a séma most elkapja, de egy write-time clamp szimmetrikusabb lenne.
- `.claude-isolated-config/` (8.4M) nincs a `.gitignore`-ban — `git add -A` esetén a
  session-history/backup bekerülne a nyilvános repóba.

## 2026-09-21 — UX: „tudós kiadás" irány (fejléc + paletta + tipográfia)

**Kérés:** a felület „claude szagú", legfőképpen a fejléc; egyszerű, letisztult,
szép tipográfia kell. Irány: **tudós kiadás** (választva), fontok: **Cardo + rendszer**.

**Feltárt okok (a „claude szag" konkrét forrásai):**
- **35 sor halott CSS** a `.archaism-hl` / `.archaism-info` / `.arch-cnt` / `.arch-line`
  szabályokból (`styles.css:388-408`, lila `#6a3d9a`) — **nulla felhasználás** az
  `app.js`-ben és az `index.html`-ben. A stílus túlélte a hapax/archaizmus logika
  eltávolítását; innen eredhetett a korábbi téves premissza.
- **Tailwind-színek szivárogtak be**, figyelmen kívül hagyva a saját CSS-változókat:
  `#3b82f6` (blue-500) a progress baron, `#f59e0b`/`#1f2937` (amber-500/gray-800) a
  recompute gombon.
- **`var(--muted, #6b7280)` latens bug:** `--muted` **soha nem volt definiálva**, tehát
  a fallback mindig érvényesült.
- 3 külső Google Fonts család (Inter a legárulkodóbb), `box-shadow` minden felületen,
  8–16px radiusok, hover-lift.

**Változtatások:**
- `app/static/styles.css` — **teljes újraírás** (~490 sor). Papír/tinta/oxblood paletta,
  `--rule` hajszálvonalak shadow helyett, `--radius: 2px`, minden `box-shadow` törölve
  (egy szándékos `inset` gyűrű maradt a `.cmp-hl.cmp-active`-on). Három fontszerep:
  `--font-greek` (Cardo, görög), `--font-ui` (rendszer serif, próza), `--font-meta`
  (rendszer sans, kiskapitális apparatus: címkék, URN-ek, id-k, számok tabular-nums-szal).
- `app/static/index.html` — fejléc masthead: ritkított kiskapitális wordmark, a
  brand-alcím kivéve (a footerben már szerepel), nav jobbra igazítva `data-nav`
  attribútummal, ikongombok doboz nélkül. Google Fonts: 3 kérés → **1** (csak Cardo).
- `app/static/app.js` — `route()` megjelöli az aktív nav-szekciót (`classList.toggle("active")`)
  a dispatch előtt, mert a render-függvények early return-ölnek.

**Verifikáció:**
- Nincs unstyled osztály: minden `app.js`/`index.html`-ben használt osztály definiált.
  (`clickable`, `highlight` már az eredeti CSS-ből is hiányzott — nem regresszió, hanem
  régi maradvány.)
- Halott CSS: `archaism-*`, `--shadow`, `--muted` → **0 előfordulás**.
- Hardcode-olt szín a token-blokkon kívül: **0**.
- Külső fontkérés: `family=Cardo:ital,wght@0,400;0,700;1,400`.
- **Kontraszt: mind a 16 pár átmegy WCAG AA-n (>4.5:1), világos és sötét témában is.**
  Legszorosabb: bridge `#8a6a3a` papíron 4.71:1, apparatus `#6f6a5e` 5.07:1.
- Smoke test: szerver indul, `/`, `/static/styles.css`, `/static/app.js` mind 200.

**Módosult fájlok:** `app/static/styles.css`, `app/static/index.html`, `app/static/app.js`

**TODO:**
- A `clickable` és `highlight` osztályok használatlanok az `app.js`-ben — érdemes
  kivenni őket a markup-generálásból.
- A `.cmp-hl.cmp-active` inset gyűrűje az egyetlen megmaradt `box-shadow`; ha a
  puritás a cél, `outline`-ra cserélhető.

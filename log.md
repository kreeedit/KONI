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

## 2026-09-21 — Flame architektúra: a Phase 1 (BPE/TF-IDF/cosine) DEKORATÍV

**Kiváltó ok:** 5 fejlesztési irány érkezett a BPE-re (diacritic-folding, morféma-BPE,
subword-IDF, dense embedding, toposz-klaszterezés). A premisszák ellenőrzése közben
kiderült valami, ami mindegyik 1–4. irányt átértékeli.

**Döntő lelet — a Phase 1 nem hat semmire:**
- `compare_iter`-ben `sel = 0.0` (default), és `chosen = [(s,i,j) for ... if s >= sel]`
  → **a cosine semmit nem szűr**. Empirikusan: `n_candidates == n_chosen` (218/218).
- A kibocsátás sorrendje **nem** cosine szerint csökkenő — a `ranked` (szó-bigram átfedés)
  sorrendjét örökli, a cosine pontszámot csak kiírja.
- A `compare()` **`chain_len` szerint rendez** (`flame_pure.py:464`), nem cosine szerint.
- Tehát a BPE → leave-n-out rolling hash → TF-IDF → cosine lánc **0 recall-t, 0 rendezést**
  ad; egy megjelenített számot és a `mean`-t. **És olcsó:** 0.030s, míg a Phase 2
  (szó-szintű Levenshtein blokkillesztés) **19.2s** 2580 párra.
- A szűk keresztmetszet a Phase 2 O(n1×n2) blokkmátrix, nem a BPE.

**További premissza-korrekciók:**
- **`vocab: 2703` félreértelmezés:** nem a BPE modell szókincse, hanem a `len(vocab)` —
  a két összehasonlított műben előforduló **különböző subword-típusok** száma
  (`flame_pure.py:414`). 120+120 fejezet Thuküdidészből és Euripidészből már 1940 típust ad,
  tehát a 2703 egyáltalán nem „szokatlanul alacsony".
- **Elavult komment:** `app/server.py:220` szerint `# deprecated (BPE removed); ignored` —
  de a BPE **él**: `is_trained() == True`, stop-lista 50, a `_units` a BPE-ágat veszi.
  (Ez a harmadik eset, hogy elavult komment/memória téves premisszát szült.)
- **1. irány (accent-agnostic BPE) MÁR MEGVAN:** `bpe_pure.normalize()` = NFKD + combining
  drop + lower, a `_word_freqs_from_corpus` normalizálva számol, a `_encode_word(normalize(w))`
  így kódol; a subword-dump is ékezet nélküli (`αθηναι`, `πολεμον</w>`), az eredeti szavak
  külön maradnak megjelenítésre. Nincs teendő.
- **2. irány diagnózisa fordított:** a jelzett hiba az „összeolvasztja a tövet a raggal"
  (over-merge), a tényleges viszont **tő-szétesés** (under-merge): `Θουκυδίδης` →
  `θ|ουκ|υ|διδ|ης</w>`, a `θουκυδιδ` tő 4 darabra esik, egybetűs `υ`-vel.
- **3. irány kategóriahiba:** a láncszűrő **szavakat** számol (`b["core"] >= ngram`,
  `b["n"] >= min_chain_words` a `_fuzzy_blocks`-ból, ami szólistákon fut). A BPE subword
  **soha nem ér el a Phase 2-be** — a `compare_iter` az `u1[i]`-ből csak a `norm_i`-t
  használja, a `subs`-ot eldobja. Nincs mit újrasúlyozni.
- **4. irány (GreBERTa/PhiloBERTa) ellentmond a projekt saját kényszerének** — a kérés
  maga írta elő a „szigorúan zero-dependency (stdlib + vanilla JS)" feltételt; egy
  transzformer PyTorch + több száz MB súly. Ez nem növelés, hanem más projekt.

**Nem változott kód.** A fenti csak feltárás; a döntés a felhasználónál.

**TODO:** az 5. irány (toposz-klaszterezés) az egyetlen, amely független a téves
premisszáktól és stdlib-ben megvalósítható; lásd még `sideproject/procopius_reuse/`.

## 2026-09-21 — Toposz-klaszterezés (5. fejlesztési irány) — implementálva

**Cél:** a találati lista ne 20–30 közel azonos sort mutasson ugyanarra a formulára,
hanem egy aggregált „toposz" sort előfordulásszámmal és kinyitható taglistával.

**Motor (`app/flame_pure.py`):**
- `_core_sequence(blocks, words)` — a pár legerősebb blokkjának **leghosszabb folytonos
  egyező szófutása** = a formula magja. (Ellenőrizve: a `_fuzzy_blocks` a `matches`-et
  növekvő `wi` szerint adja, tehát a futásdetektálás érvényes.)
- `cluster_pairs(sigs, threshold, min_size, max_lev)` — union-find a hasonlósági gráfon.
  Három fokozat: (1) **azonos** magok egy dict-passban (pontos, teljes, nem veszít recall-t);
  (2) a **különböző** magok összehasonlítása — nem a párok egymás ellen: méréssel
  igazolva a páronkénti összehasonlítások **93%-a redundáns ismétlés** volt
  (max multiplicitás 56), ez a lev-hívásokat 3222 → 127-re vitte **nulla recall-költséggel**;
  (3) hossz-ablak + 4-gram Jaccard kapu a Levenshtein DP előtt.
- `compare_iter` paraméterek: `cluster_threshold` (0.85), `cluster_min` (2). Új események:
  `{"t":"phase","phase":"clustering"}` majd `{"t":"clusters","clusters":[...],"stats":{...}}`
  **a `done` előtt**. A tagok indexei a **kibocsátás sorrendjére** mutatnak.
- **Adverzariális review utáni javítások (a saját docstringem számait visszavontam):**
  az eredeti docstring „2746 vs 2749 unió, ~0.1%, 9× gyorsulás" állítása **nem reprodukálható**
  és kategóriahibás volt: a próbám `unions` számlálója valójában *sikeres pár-szintű
  összehasonlításokat* számolt, nem union-find összevonásokat (a 3966 páros listán ugyanaz a
  mag-pár sokszor ismétlődik), a „9×" pedig egy **befejezett** futást hasonlított egy olyanhoz,
  amely elérte a saját `max_lev` sapkáját. A docstring most csak azt állítja, amit mértem:
  a páronkénti ciklus 3222 Levenshtein-hívást végzett **215 különböző mag-párra**
  (3007 ismétlés, 93%) — ezt a redundanciát szünteti meg a mag-alapú összehasonlítás.
  Új `gate_skips` számláló a statsban (a self-compare-n 2 262 939), hogy a kapu szűrése
  **látható** legyen, ne csendes. A `_shingles` **degenerált volt `len(s) == k`-ra**
  (`'abcd'`/`'abce'`: arány 0.875, de 0 közös 4-gramm → kiesett); javítva `k-1`-re váltással
  azon az ágon. A `max_lev` csak a DP-t korlátozza, a kapuciklus O(U²) — dokumentálva.
- `compare()` (nem-streaming): a párok `chain_len` szerint rendeződnek át, ezért a
  tagindexeket `rank` szerint **újra képzi** — különben rossz sorra mutatnának.
- A pár kap egy `core_text` mezőt (ékezetes, 24 szóra vágva) a klaszter-fejléchez.

**Szerver (`app/server.py`):** `cluster_threshold`, `cluster_min` query paraméter mindkét
végponton. Az elavult `vs = q.get("vocab", "")  # deprecated (BPE removed); ignored` sor
törölve (a BPE él — ez volt a harmadik téves premissza forrása).

**UI (`app/static/app.js`, `styles.css`):** `_cmpPairHtml` / `_cmpGroupHtml` /
`_cmpClusterHtml` / `_cmpRefs`; `<details>`-alapú klaszter-sor (`N×` jelvény, mag-szöveg,
toposz-címke), a klaszter teste behúzva hajszálvonallal; `CMP_CLUSTER_INLINE = 12` felett
beágyazott „maradék N előfordulás" `<details>`. Új csúszka: `slider-cl` (szerveroldali,
⟳ Recompute), új azonnali kapcsoló: `cmp-group` checkbox. A `phase` esemény kiírja, hogy
„grouping toposz…" — a klaszterezés a stream végén egy globális menet, és egy néma szünet
100%-nál akadásnak látszana. TSV export új oszlopokkal: `cluster_id`, `cluster_size`,
`topos_core`.

**Valós eredmény — Prokopios `de Bellis` (4029.001) × Thuküdidész (0003.001):**
- 852 pár → **82 klaszter (701 pár) + 151 szingli = 233 egység** a 852 sor helyett.
- A találatok **82%-a formulaismétlés**, nem önálló találat.
- A legnagyobb toposzok: `Ὑπὸ δὲ τοὺς αὐτοὺς χρόνους` (83×),
  `σφᾶς τε αὐτοὺς καὶ` (50×),
  **`καὶ δέκατον ἔτος ἐτελεύτα τῷ πολέμῳ τῷδε ὃν` (48×)** ← pontosan az „évzáró formula",
  amit a felhasználó példaként hozott, `Ἐν τούτῳ δὲ οἱ ἐν` (43×),
  `ἐκ τοῦ ἐπὶ πλεῖστον` (39×).

**Mérések / elvetett optimalizálás:**
- A klaszterezés önköltsége 3966 páros ön-összehasonlításnál **~11–17 s** (gépi terheléstől
  függően; a `cluster_threshold` 1.00-nál 0.35 s); a valós kereszt-szerzős esetben
  (Prokopios × Thuküdidész, 852 pár) elhanyagolható. Az idő **~96%-a a kapuciklus**, nem a
  Levenshtein DP — a DP csak 123 összehasonlítás.
- A 4-gram Jaccard kapu **heurisztikus**, és ezt a docstring kimondja. A korábbi „~0.1%"
  veszteség-állítás **visszavonva** — két okból:
  1. *Módszertani hiba:* a „9× gyorsulás" és a „2746 vs 2749 unió" összehasonlítás egy
     **befejezett** futást mért egy olyanhoz képest, amely a saját `max_lev` sapkájába futott.
     A „nem fejeződik be" állítás **utólag megcáfolva**: a hang-bizonyítható multiset-L1
     referencia sapka nélkül *lefut* — az adversary lefuttatta (~14 perc CPU a 3966 páros
     eseten). Az én saját próbálkozásom viszont **nem** futott le 34 perc CPU alatt: ezt a
     *saját* implementációm páronkénti konstans faktora okozta (2.68M párra `set(ca)|set(cb)`
     unió + abszolút-diff összegzés), nem a korlát eredendő lassúsága. A tanulság kettős:
     a korlát *nem* használhatatlan, de a naiv implementációja igen, és a sandbox
     wall-clock-ja megbízhatatlan (a DP-szám determinisztikus, az az idézhető).
  2. *A veszteség input-függő, és az általam mért inputon nulla volt.* Az **alapértelmezett**
     `max_candidates=4000` sapkával vett 3966 páros inputon a Jaccard kapu mérten **nullát**
     veszít: a két kapu eredménye azonos (81 klaszter / 365 klaszterezett pár / 56 unió).
     A **csonkítatlan** jelölt-halmazon (16287 jelölt → 8009 pár) viszont az adversary mérése
     szerint 596 unió helyett 564 (727 vs 701 klaszter) — azaz a kapu vesztesége ott ~5%.
     ⚠ **Ezt a számot én nem tudtam lefuttatni** (lásd fent: a saját L1 próbám 30 perces
     `timeout`-tal, 124-es kilépéssel állt le), így **az adversary mérését idézem, nem a
     sajátomat**. Amit *magam* igazoltam: ugyanazon az inputon a Jaccard-oldal **pontosan**
     az ő számát adja (564 unió / 727 klaszter / 4401 klaszterezett pár / 2470 DP), és a
     bemenet is eggyezik (8009 pár, 4899 különböző mag) — a két harness tehát ugyanazt az
     inputot és ugyanazt a Jaccard-eredményt adja, ami az L1-oldalt valószínűsíti, de nem
     igazolja. A tanulság nem a szám, hanem hogy a kapu vesztesége **nem általánosítható**
     arról az inputról, amin mértem. A `gate_skips` számláló ezért is fontos: input-függő,
     és láthatónak kell lennie.
- **Elvetve:** Bloom-sketch kapu (4096 bit, `crc32`) a Jaccard elé. Bizonyítottan
  recall-semleges (azonos klaszterek, 0 téves disjoint 3000 random páron), de a mért
  gyorsulás **1.0×** volt — a nagy-int AND annyiba kerül, amennyit megtakarít. Kivéve.
- **Elavult-checkout félrejelzés:** az adversary addendumában szereplő
  „`cluster_pairs(['abcd','abce'], 0.85)` → `[]`" észrevétel a **javítás előtti** kódra
  vonatkozik. A jelenlegi kódon ez **1 klaszter 2 taggal** (ellenőrizve). Az ok: `'abcd'`
  `k=3`-ra `{'abc','bcd'}` (2 gramm), `'abce'`-re `{'abc','bce'}`, így `2·1/(2+2) = 0.5 ≥ 0.425`
  — átmegy. Ez nem a `_shingles` javítás gyengéje, hanem a review pillanatképe.

**Módosult fájlok:** `app/flame_pure.py`, `app/server.py`, `app/static/app.js`,
`app/static/styles.css`, `log.md`.

**Tesztelve:** 27 egységteszt a `cluster_pairs`-re és a `compare()` index-újraképzésére
(0 hiba); node-harness a valódi renderelő függvényeken valódi stream-elt adaton
(minden pár pontosan egyszer, tagek kiegyensúlyozottak, `data-size` egyezik);
HTTP végpont-teszt (stream + nem-streaming); `validate_canon.py` 0 hiba / 0 figyelmeztetés;
`check_no_restricted.py` OK.

**⚠ BIZTONSÁGI LELET (nem a klaszterezéshez tartozik, de menet közben találtuk):**
- A `kreeedit/KONI` GitHub-repo **nyilvános** (`"private": false` az API szerint).
- A `.claude-isolated-config/` **benne van a HEAD-ben**: **520 követett fájl**, köztük
  **4 `.key` fájl** (`sessions/*.key` ×3 + `daemon/control.key`), 228 `.md`, 93 `.json`,
  17 `.jsonl` — session-átiratok, job-állapot, file-history mentések. A könyvtár **60 MB**.
- A `.gitignore` **nem fedi le**, és a fájlok **már fel vannak pusholva** az `origin/main`-re
  (legutóbb a `cbe04db ux` commit érintette).
- A `.key` fájlok nagy valószínűséggel lokális daemon/IPC kulcsok, nem API-hitelesítő adatok,
  de nyilvános repóban a helyük nem ott van; az átiratok pedig beszélgetéstartalmat hordoznak.
- **Javítás szándékosan NEM történt:** a history-ból való eltávolítás `git filter-repo` /
  force-push, azaz destruktív és kifelé ható művelet — a felhasználó döntése kell hozzá.

**TODO:**
- `app/__pycache__/`: a `__pycache__/` szerepel a `.gitignore`-ban, de **10 `.pyc` már követve
  van**, ezért a szabály nem hat rájuk (a gitignore csak nem követett fájlokra vonatkozik) —
  a kódmódosítás így 2 `.pyc`-t piszkít. `git rm --cached app/__pycache__/*` kellene.
- A klaszter `<details>` nyitva/zárva állapota nem marad meg újrarendereléskor.
- `check_no_restricted.py`: „Restricted works to guard: 0" — az őrhalmaz üres, mert egyetlen
  mű sem visel `restricted:*` provenance-t. Nem regresszió, de a firewall így nem bizonyított.
- Nincs perzisztált tesztsuite a repóban; a fenti tesztek a job tmp-könyvtárában élnek.
- A klaszterezés ~15 s a legrosszabb esetben (3966 páros ön-összehasonlítás); Bloom-sketch
  kapuval próbáltuk gyorsítani, 1.0× lett, elvetve. Valódi index (invertált shingle-tábla)
  kellene hozzá, ha ez zavaró lesz.

## 2026-09-21 — Flame 500: `could not convert string to float: 'undefined'` — javítva

**Tünet (felhasználói bejelentés):** a Flame összehasonlítás minden kattintásra 500-at adott:
`GET /api/compare_stream?...&cluster_threshold=undefined` → `Error: could not convert string to
float: 'undefined'`. A kérés el sem jutott a motorig.

**Gyökérok (kliens):** `app/static/app.js`-ben a `_cmpState` default-jai **két helyen** voltak
kiírva. A compare-nézet inicializálója `_cmpState = { p1, p2, ngram, n_out, chain, fuzz }` —
**`cluster` nélkül** —, ami felülírta a modul szintű initializer `cluster: 0.85`-jét. Így
`_cmpState.cluster` `undefined` lett, a template-literal pedig a `"undefined"` **stringet** küldte.

**Javítás:**
- `const CMP_DEFAULTS = { ngram: 4, n_out: 1, chain: 2, fuzz: 0.75, cluster: 0.85 };` — egyetlen
  forrás; mindkét hely `{ ...CMP_DEFAULTS }`-tal épül. A duplikált literál volt a hibaosztály,
  ezért nem csak a hiányzó mezőt pótoltam.
- **Szerver (`app/server.py`), ugyanaz a hibaosztály:** mindkét végpont védtelenül hívott
  `int()`/`float()`-ot a query paramétereken (nem csak `cluster_threshold`-on — `ngram`,
  `n_out`, `chain`, `fuzz`, `cluster_min`, `similarity_threshold` és a `/api/authors?limit=`
  is 500-at dobott volna szemétre). Új `_qnum(q, key, cast)` helper: hiányzó **vagy**
  értelmezhetetlen értékre `None`-t ad → a motor default-ja érvényesül.
  Finomság: `None`-t ad vissza `0` helyett, hogy az **`n_out=0`** (szigorú, összefüggő n-gramm
  egyeztetés — ennek megvan a jelentése) megkülönböztethető maradjon a „nem küldték"-től.
  A `limit=0` szintén megmarad 0-ként (nem esik 50-re).
- **Nem-finite védelem:** `float('nan')`/`float('inf')` **szabályosan parse-olódik**, de szemét
  hyper-paraméter — a `nan` ráadásul minden range-klampot megmérgez (minden összehasonlítása
  `False`). A `_qnum` ezért `math.isfinite`-tel elutasítja őket.
- **A motor most a klampolt értéket jelenti:** a `meta` esemény megkapta a
  `cluster_threshold` / `cluster_min` mezőt. Eddig a TSV-fejléc a **kért** értéket írta; egy
  kézzel szerkesztett URL (`cluster_threshold=0.2`) a motorban 0.5-re klampolódott, de a fejléc
  0.2-t állított. A kliens a `meta`-ból felülírja a sajátját, ha az megvan.

**Tesztelve (éles end-to-end, stubolt repo-val, `serve_test.py`):**
- a **pontos** hiba-URL (`cluster_threshold=undefined`): **HTTP 500 → 200**, végigfut
  (908 pár, 78 klaszter, `done` esemény).
- `NaN`, `inf`, `-inf`, `abc`, `''`, hiányzó → mind a default-ra esik, 500 nélkül.
- `n_out=0` → **0-ként megy át** (nem veszik el); hiányzó → 1.
- `/api/authors`: `limit=undefined`/`abc` → 50; `limit=0` → 0; `limit=5` → 5.
- `validate_canon.py`: 0 hiba / 0 figyelmeztetés · `check_no_restricted.py` OK ·
  `test_cluster.py` / `test_align.py`: 0 failure · `node --check app.js` OK ·
  `test_group.js`: minden egyezik (3682 egység, 3966 pár, 81 klaszter, tagek kiegyenlítve).

**Módosult fájlok:** `app/static/app.js`, `app/server.py`, `app/flame_pure.py`, `log.md`.

**TODO:** a `limit` negatív értéke (`limit=-1` → `[:-1]`, az utolsó elem elvész) megmaradt,
meglévő latens csípés, nem ehhez a hibához tartozik.

## 2026-09-21 — Archaizáló-detektor (új funkció) — implementálva

**Kérdés a felhasználótól:** működik-e az archaizáló-detektor (fiatalabb műben felbukkanó szó,
ami a koráribban többször szerepelt, a fiatalabban ritka vagy hapax)?

**Válasz: nem létezett.** Ellenőrizve: `hapax`/`archai*`/`archaiz*` egyetlen találat az
`app/`+`scripts/` alatt — `app/flame_pure.py:18`, ami *kizárja* (`NO hapax/archaism`).
`Counter` csak Phase 1 BPE-hash + IDF. Frekvencia-végpont nem volt. A Flame kizárólag
**szöveg-újrafelhasználást** keres; a gyakoriság-eltolódás más kérdés.

**Ez a feltevés MÁSODSZOR került elő** (korábban egy „hibás `Counter`-alapú detektor" téves
riasztásai — az a kód sem létezett). A motor fejlécébe is beírtam, hogy a jelenlét hiánya
ne tűnjön néma hibának.

### Amit építettem — `app/archaism_pure.py` (új, stdlib-only)

`work_freq(sections)` → `{counts, total, display, caps}` · `occurrences(sections, wanted)` ·
`contrast(fa, fb, ...)` · `report(sections_a, sections_b, ...)`.

Jel: `count_A(w) >= min_a` (3) ÉS `count_B(w) <= max_b` (1) ÉS
`score = log2( ((c_A+0.5)/N_A) / ((c_B+0.5)/N_B) ) >= min_score` (2.0). A **+0.5 add-half
(Haldane–Anscombe) prior** azért kell, hogy a `count_B == 0` eset véges legyen a végtelen
arány helyett. A és B **irányát a hívó mondja meg** — a modul nem tippel dátumot; megfordítva
más kérdésre válaszol.

### ⚠ A nyers rangsorolást a TÉMA uralja — a `drop_proper` ezért default ON

Az első futás élén **csupa népnév/toponima**: `Ἀθηναῖοι` (502→0), `Λακεδαιμόνιοι` (213→0),
`Συρακόσιοι`, `Πελοποννήσιοι`, `Κορίνθιοι`. Ez **nem archaizálás, hanem téma**: Thukydidész
tárgya a peloponnészoszi háború, Prokopiosé Iustinianus háborúi. Ezt semmilyen
gyakoriság-statisztika nem tudja megkülönböztetni — csak a tulajdonnevek eldobása.

A szűrő: **többségi nagybetűség** az EREDETI alakokon, a **két művet együtt** számolva
(az ifjabb műben a szó a konstrukció szerint ritka, így az ottani arányt 1-2 token döntené el).
Mérés: Thukydidésznél **397 szó 100%-ban**, **2637 szó 0%-ban** nagybetűs, a kettő közt
gyakorlatilag üres a sáv → tiszta szétválasztás. Real adaton **709 tulajdonnév** esik ki.
Robusztusság: `count_A >= min_a = 3` miatt EGY nagybetűs előfordulás sosem billenti át a
szűrőt (max 1/(3+1) = 0.25 < 0.5) — vagyis egy mondatkezdő nagybetű nem jelöl meg tévesen.

**Amit a szűrő helyesen MEGTART — philológiailag valódi jel:**
`αἰεί` (ionikus/epikus „mindig") 128×→0 · `ξυμμάχοις` — a **ξυμ-** (attikai) vs köznyelvi
**συν-** · `ἐπιγιγνομένου` — a **-γιγν-** (attikai) vs koiné **-γινν-** · `ὁπότε` ionikus
„valahányszor". Thukydidésznél az attikai `ἀεί` **egyszer sem** szerepel, csak az ionikus
`αἰεί` — pontosan a keresett jelenség.

### Kényszerítő mellékváltozások

- `app/texts.py`: `section_texts(aid, wid, window=True)` — az archaizmus **`window=False`**-szal
  hív. Az engine ablaka **25 szóval átfed** (`step = 140-25 = 115`), így a windowelt kimeneten
  számolva minden határ duplán számítana, mégpedig a levél hosszától függő — azaz **változó —
  arányban**, ami a két mű között NEM esik ki. Frekvenciaméréshez kötelező a teljes szöveg.
- `app/flame_pure.py`: új public `words(text)` helper. A szó-regex **egy helyen** él — pont az
  a duplikáció okozta a mai `cluster_threshold=undefined` hibát.
- `app/server.py`: `GET /api/archaism/<aid1>/<wid1>/<aid2>/<wid2>` (work1 = korábbi,
  work2 = fiatalabb). Paraméterek `_qnum`-mal (szemét → default), `drop_proper` külön parse-olva.
- UI: új **Archaism** nav-füzet, `#/archaism` route, `renderArchaism` (két `makePicker`),
  `_archHtml` táblázat, `.arch-*` CSS a meglévő apparátus-hangon. `dim` helyett a meglévő
  `muted`/`warn` konvenció.

### Hibák, amiket a saját tesztjeim okoztak (nem a kód)

1. `3 → 1` előfordulás azonos korpuszméretnél csak 2.3× arány → helyesen kiszűri a 4×-es
   `min_score`. Nagyobb esést kellett adnom a teszt-inputnak.
2. `toLocaleString()` a sandbox `hu-HU` locale-jában `99 999`-et ad, nem `99,999`-et — a
   tesztem hard-kódolt elválasztója volt rossz. Digits-only összehasonlításra írtam át.
3. **Valódi hiba a kódban, amit él-eset talált meg:** `limit=0`-nál a UI azt írta volna, hogy
   „No candidates at these thresholds", pedig **11 804 jelölt** volt — csak a limit vágta el
   mindet. Az üres állapot így félrevezette volna a felhasználót (a rossz irányba küldte volna:
   „lazíts a küszöbökön"). Javítva: szétválik a „nincs találat" és a „a limit elrejtette".

### Tesztelve

`test_arch.py`: 33 állítás, 0 failure — a kézzel számolt `log2(7) = 2.81` pontszám, `count_B=0`
végessége, irány-aszimmetria, `min_a`/`max_b`/`min_score`/`limit` szűrők, determinisztikus
rendezés, `occurrences` cimke-dedup és cap, ékezet-normalizálás, tulajdonnév-szűrő (pooled
arány, `n_dropped_proper`, robusztusság). `test_arch_view.js`: 22 állítás, 0 failure — valódi
végpont-válaszon renderelés, tag-egyensúly, `undefined`/`NaN` hiánya, XSS-escape a szó- és
címke-cellában, üres állapotok. Él-esetek a végponton: önmagával (üres), nem létező mű (404),
szemét paraméterek, negatív értékek, `limit=5`. Regresszió: `test_cluster.py`,
`test_align.py`, `test_group.js` mind 0 failure · `validate_canon.py` 0 hiba / 0 figyelmeztetés ·
`check_no_restricted.py` OK.

**Módosult:** `app/archaism_pure.py` (új), `app/texts.py`, `app/flame_pure.py`, `app/server.py`,
`app/static/app.js`, `app/static/index.html`, `app/static/styles.css`, `log.md`.

**TODO / ismert korlátok:**
- **Alak-alapú, nem lemma-alapú.** `ποταμόν` és `ποταμός` két külön sor; itt a „hapax" az ADOTT
  ALAK hapaxja, nem a lexémáé. A lemma-csoportosítás morfológiai analizátort igényelne (azaz
  dependency-t) — szemben a zero-dependency szabállyal.
- A tulajdonnév-szűrő **nagybetűség-heurisztika**; olyan kiadáson, amely nem nagybetűz
  konzisztensen, gyengébben működik. A kimutatott bimodalitás ezekre a kiadásokra igaz.
- A `limit` negatív értéke 0-ra klampolódik (nem default-ra) — szándékos, de kézzel szerkesztett
  URL-nél üres táblát ad; a UI ezt most már helyesen címkézi.

---

## 2026-09-16 — Archaizmus-detektor: két szemantikai javítás + a `δ` maradék

Felhasználói észrevétel: *„Ez így nem jó, hiszen azokat is megjeleníti amelyek a b-ben
egyáltalán nincsenek jelen."* Igaz — a `max_b=1` átengedte a `count_B = 0` esetet is, és
ezek elnyomták a listát. Két külön hiba volt a háttérben, a másodikat él-adaton, a
javítás után vettem észre.

### 1. `min_b` — a szónak tényleg SZEREPELNIE kell a fiatalabb műben

- `MIN_B = 1` konstans, `min_b` végigfűzve: `contrast` → `report` → `server.py` → UI (`arch-minb`
  input) → URL (`&min_b=`).
- Szemantika: `count_B ∈ [min_b, max_b]`. `min_b=1, max_b=1` → pontosan **hapax**;
  `min_b=1, max_b=3` → „néhányszor". `min_b=0` visszaadja a régi, hibás viselkedést — csak
  kézzel, kifejezetten.
- Él-adaton: jelöltek **1663 → 330**, és minden sor `B=1` (pl. `ναυτικὸν A=69 B=1`,
  `ὁπλίτας A=65 B=1`, `τρόπαιον A=51 B=1`).

### 2. Elíziós töredékek — és a bennük maradt korónisz

A `min_b` javítás után egy szemétsor maradt: `δ A=42 B=1`. Utánamentem a nyers szövegnek:
`οἱ δ’ οὖν`, `σημεῖον δ’ ἐστί` — vagyis **elízió**. A `\b\w+\b` a `δ’`-t kettévágja: `δ` + `’`,
és a `δ` nem szó, hanem az elidélt `δέ` farka. Ugyanez `τ’` (τε), `ἀλλ’` (ἀλλά), `ἐπ’/ἐφ’` (ἐπί),
`καθ’/κατ’` (κατά), `οὐδ’`, `δι’`, `μετ’`.

- `flame_pure.py`: új `words_elided(text) -> [(word, is_elided), ...]`. A `words()`-hoz
  **nem nyúltam** — a text-reuse illesztésre a töredék ártalmatlan (mindkét oldal ugyanúgy
  hordozza, a core/chain szűrők amúgy is kidobják), a frekvenciakontrasztra viszont **végzetes**.
- `archaism_pure.py`: `work_freq(drop_elided=True)` kihagyja őket, és visszaadja `n_elided`-et;
  a `contrast` eredménye `n_elided_a`/`n_elided_b`; a UI kiírja, hogy a darabszámok a kizárás
  UTÁNI értékek.

**Miért nem esik ki a torzítás magától:** mert szerzőnként MÁS. Mérés (teljes mű, `window=False`):
Thukydidész **2468 / 150161 = 1.64%**, Prokopiosz **1829 / 224528 = 0.81%**. A ráta kétszeres
különbsége nem cancelling bias, hanem hamis jel.

**A korónisz (U+1FBD):** az első javítás után a `δ` sor **még mindig ott volt** (`A=34`). Kiderült,
hogy a Perseus-féle politonikus szöveg az elíziójelet **nem mindig U+2019-cel** írja:
Thukydidésznél **151 db U+1FBD GREEK KORONIS** áll 2401 db U+2019 mellett — Prokopiosznál
**0 db**. Vagyis a maradék szivárgás maga is szerző-specifikus, pontosan az a fajta, ami nem esik
ki. `_APOSTROPHE_RE` bővítve `[’ʼ´`'᾽᾿΄]`-re. A `δ` sor eltűnt; a szűrő minden sorra
`len(labels_b) <= count_b`.

### 3. A hely-megjelölés hazudott a darabszámról

Él-adaton észrevettem: `δ A=34 B=1`, de `labels_b` **12 szakaszt** sorolt fel. A `count_b=1`
mellett 12 hely logikailag lehetetlen. Ok: az `occurrences()` **sima `words()`-szal** tokenizált,
míg a `work_freq` `words_elided`-dal — a hely-lista olyan szakaszokat is mutatott, ahol az
egyetlen találat egy töredék volt. A bizonyíték-panel cáfolta a saját darabszámát.
Javítva: `occurrences(drop_elided=...)`, és a `work_freq` az eredményében visszaadja a
`drop_elided` flaget, hogy a `contrast` **ugyanazzal** a tokenizálással futtassa a második
pásztát, ne default-feltevéssel. Él-adaton most minden sor `len(labels_b) == count_b`.

### 4. `_archHtml` opts: ne írjon ki `undefined`-ot

A nézet-teszt elhasalt (`no literal 'undefined'`), mert a teszt fixture-e egy mezővel rövidebb
opts-ot adott, és `${opts.minB}` a string `"undefined"`-ot renderelte. A produkciós hívóhely
helyes volt — de ez **pontosan a `cluster_threshold=undefined` hiba alakja**, ezért nem a
tesztet igazítottam a kézzel írt fixture-höz, hanem a renderelőt: `opts.minX ?? ARCH_DEFAULTS.*`.
Egy hiányzó mező most a valódi default-ot írja, nem lyukat. A teszt ezt külön állításként
rögzíti (rövid opts-objektum → nincs `undefined`, a fallback érték jelenik meg), és a
sandbox az `ARCH_DEFAULTS`-ot **a forrásból** olvassa ki, nem újraírja.

### Módosult

`app/flame_pure.py` (`_APOSTROPHE_RE`, `words_elided` docstring), `app/archaism_pure.py`
(`MIN_B`, `min_b`, `drop_elided`, `occurrences`, `n_elided_*`), `app/server.py` (`min_b`),
`app/static/app.js` (`ARCH_DEFAULTS.min_b`, `arch-minb` input, `opts ?? default`, elízió-sor).

### Tesztelve

`test_arch.py`: 0 failure — +12 új állítás (elízió zászló a következő/előző szón nem billen,
`δ’`/`τ’` kihagyva a számolásból, `drop_elided=False` visszahozza, `total` a kizárás utáni,
`n_elided` a riportban, a töredék nem lesz jelölt-sor; korónisz-ág: `οἱ δ’ οὖν` → `δ` elided,
a szomszédok nem). `test_arch_view.js`: 0 failure — friss végpont-válaszon, +2 állítás a
rövid opts-objektumra. Regresszió: `test_cluster.py`, `test_align.py`, `test_group.js` 0 failure ·
`validate_canon.py` 0 hiba / 0 figyelmeztetés · `check_no_restricted.py` OK ·
`compare_stream` él-adaton 908 pár / 939 NDJSON sor, `done`-ig fut (az engine érintetlen,
`words()` változatlan).

Él-végpont: `GET /api/archaism/0003/001/4029/001` → HTTP 200, 327 jelölt, 37 tulajdonnév
kizárva, `n_elided_a=2468`, `n_elided_b=1829`, egyetlen elíziós töredék sincs a sorok közt.
Szemét paraméter (`min_a=undefined&min_b=NaN&max_b=inf&limit=abc`) → mind a default · nem
létező mű → 404 · `drop_proper=0` megmarad.

**TODO:**
- `scripts/serve.py` (PID 549513) **régi kódon fut** — a felhasználónak újra kell indítania.
- A `max_b` felső korlátja a CANDIDATE szintjén dől el, nem a megjelenítésnél: `max_b=3`-nál
  a `min_score` gyengébb eséseket is átenged, ezért a sorok „lágyabbak". Küszöb-finomhangolás
  valódi philológusi visszajelzés után.

---

## Archaizmus #4. pont: variáns-összevonás + stílusregiszter (pooling & register)

A felhasználói módszertani kritika 4. pontja: a nézet jelenleg **témakülönbséget és
szókincskopást** mér, nem archaizmust. A javítás két, egymástól független réteg.

### 1. Új modul: `app/variants.py` (stdlib-only, külső függőség nélkül)

Négy megfelelési szabály, két külön funkcióval, **szándékosan szétválasztva**:

- `unify(form, rules)` — **pooling**: a klasszikus alakot a koiné alakra hajtja, hogy a
  statisztika egy sorba gyűljön. Egyirányú (`ξυ`→`συ`), sosem visszafelé, és **idempotens**
  (a teszt állítja: `unify(unify(x)) == unify(x)`), különben a `work_freq` és a
  `variant_rates` más számot adna.
- `marked_rules(form, rules)` — **oldalfelismerés**: melyik szabály szerint visel a token
  MARKED (klasszikus/attikai) alakot. Ebből lesz a stílusmetrika.

| szabály | marked | kulcs-oldal | illesztés | metrika |
|---|---|---|---|---|
| `xyn`  | ξυ- | συ- | prefix | igen |
| `gign` | γιγν- | γιν- | substring | igen |
| `tt`   | -ττ- | -σσ- | substring | igen |
| `rr`   | ρσ- | ρρ- | lexémák | **nem** |

`applies_to` explicit if/elif (a korábbi olvashatatlan feltételes kifejezés helyett), plusz
stopliszták: `ξυλο/ξυλε/ξυλη/ξυλι/ξυρο/ξυρε/ξυρα/ξυνω` (ξύλον, ξυρόν nem ξύν!), `αττικ`
(Ἀττική nem Attic restoration a szövegben, hanem tulajdonnév), és `rr`-nél **csak kurált
lexémák** (`θαρσ/θαρρ`, `αρσην/αρρην`, `κορσ/κορρ`, `μυρσ/μυρρ`).

### 2. Három különböző irány — ez a lényeg

Éles mérés a produkciós úton (`applies_to`), ablak nélküli szövegen, elíziós töredékek és
**tulajdonnevek nélkül**. A = Thuküdidész `0003/001` (147 693 token), B = Prokopiosz
`4029/001` (222 699 token):

| szabály | A /1k | B /1k | A/B | irány |
|---|---|---|---|---|
| `xyn`  | 12.790 | 12.851 | 1.00 | **PARITY** |
| `gign` | 2.404 | 0.121 | 19.87 | **COLLAPSE** |
| `tt`   | 0.068 | 0.485 | 0.14 | **EXCESS** (B 7,1×) |
| `rr`   | 0.284 | 0.256 | 1.11 | parity (metrika ki) |

- `gign` az, amit a jelenlegi nézet hajt: Thuküdidész reduplikál, Prokopiosz elhagyta.
- `xyn` **paritás** — Prokopiosz **Thuküdidész saját rátáján** írja a ξυμμαχία-t, három
  tizedesre. Rendszerszintű imitáció, amire egy ritkaságszűrő **strukturálisan vak**, mert
  nincs ritka szó: a szavak gyakoriak, csak a HELYESÍRÁS választott.
- `tt` **fordítva fut**: a -ττ- a 2. századi attikista restauráció, nem thuküdidészi jegy.
  Egy ritkaságszűrő ezt *anti-archaizmusként* pontozza.

Ezért nem olvashatók a ráták ítéletként: hogy a paritás vagy a többlet az archaizáló választás,
az a **korszak normájának** ténye — harmadik, kortárs referencia-korpusz kell hozzá (2. pont).

### 3. Tulajdonnév-szűrő: teherviselő, nem kényelmi

`tt` nyersen 0.176/1.361 (`drop_proper=0`), szűrve 0.068/0.485 — a nyers ττ tokenek
62%-a (A) és 64%-a (B) tulajdonnév (`Ἀττική` 84 A-ban, `Οὐιττιγίς` = Witigis 116 B-ben).
Szűrés nélkül a szabály **prosopográfiát** mér, nem stílust; szűrve a többlet megmarad
(10 vs 108 tiszta token), tehát a jel valódi. Az `xyn`-nél a szűrő szinte semmit nem mozdít
(B 12.851 → 12.856).

### 4. `app/archaism_pure.py`: két riport

- `work_freq(..., variants=VARIANTS_DEFAULT)` — poolol `variants_unify`-val; visszaadja a
  `forms` szótárat is (`{kulcs: Counter[norm alak]}`), amiből a pooling kinyilatkoztatható.
- `variant_breakdown(key, fa, fb)` — a **két mű UNIÓJÁN** tesztel (`len(set(forms_a) | set(forms_b)) < 2`),
  nem művenként külön! A pool lényege, hogy a két mű **más** alakot választ: A ἧσσον-t ír és
  sosem ἥττων-t, B fordítva — művenkénti teszttel a legtisztább eset is „nem történt pooling"-ot
  jelentene. (Mérve: az a hiba mind a 300 sort elnémította.)
- `variant_report(...)` — **2/2. riport**, a stílusregiszter: `rate_a/rate_b` a marked alak
  ezrelékében, `ratio_ab`, `direction` (parity sáv 0.75–1.33 / collapse / excess /
  absent-in-B), a kiszűrt tulajdonnevek számával, a szabály `evidence`/`caveat` mezőjével.
- `variant_rates(...)` — csak a **marked** oldalt számolja (a marked oldal egzakt, a
  kulcs-oldal szennyezett).
- Minden lexikai sor megkapja a `variants` mezőt; a `contrast` params-ba bekerült a
  `variants` lista és a `variants_mismatch` zászló.

### 5. `app/server.py`

`/api/archaism/...` olvassa a `variants`-t (`variants_names`, ismeretlen név eldobva) és a
`mode`-ot (`lexical`|`style`, default lexical, lowercase-re normalizálva), és a `variant_report`
vagy a `report` függvényt hívja. Válasz: `mode`, `variants_available` (a `describe()`-ből),
`result`.

### 6. `app/static/app.js`

- `ARCH_VARIANTS = ["xyn","gign","tt","rr"]` (**`let`**, mert `_archReconcileRules` a motor
  tényleges szabálylistájához igazítja, `console.warn`-nal eltéréskor).
- `renderArchaism` új két-riportos bevezető; a lexikai küszöbök `<span class="arch-lex-only">`-ba
  kerültek, amit `_archSyncMode()` rejt el style módban. Új `.arch-variants` blokk
  szabályonkénti checkboxszal, tooltip a **motortól** (`_archVariantLabel`), nem ebből a fájlból.
  Az `#arch-mode` `change` eseménye `_archSyncMode`-ra kötve.
- `_styleHtml(d, opts)` — **új**: a regiszter-tábla (marked / kulcs-oldal / A és B ezrelék /
  A/B / irány **prózában** / token A-B), irány-badge, tulajdonnév-lábjegyzet, majd szabályonkénti
  jegyzet a motor `evidence`/`caveat` mezőjéből. `ARCH_DIRECTION` a négy irányt mondattá oldja
  (a `parity` és az `excess` külön szót kap, mert egyik a vak, másik a fordított eset).
- `_archHtml` — soronkénti `arch-vsplit` oszlop: egy poolozott sor megmondja, melyik alakokból
  áll a szám (`παραγιγνονται 6/0 · παραγινονται 0/1`). A count helyes, de aki konkordanciával
  veti össze, nem találná meg ennyi tokent a szó-oszlopban. A `marked` alak dőlt, a koiné halvány.

### 7. CSS

`styles.css`: `.arch-vsplit`, `.arch-variants`, `.arch-note`, `.arch-lex-only { display: contents }`
(így a `display:none` visszaváltás nem töri a kontroll-sor térközét), `.arch-where.arch-dir`.

### Módosult

ÚJ: `app/variants.py`. `app/archaism_pure.py`, `app/server.py`, `app/static/app.js`,
`app/static/styles.css`.

### Tesztelve

- ÚJ `test_variants.py`: **OK** — 60+ állítás: `names()` default/all/none/`-`/ismeretlen-eldobás;
  prefix/substring/stoplista viselkedés (`ξύλον`, `ξυρόν`, `Ἀττική` nem marked); `rr` lexémák;
  `unify` fixpont már-koiné alakokon és stoplistázott alakokon, **idempotencia** mind az öt
  reprezentatív alakra, `ξύμμαχοι → σύμμαχοι` (nincs kettős magánhangzó); `marked_rules`
  függetlenség (`προσγιγνόμενα` → gign); `describe()` kulcskészlet és részhalmaz;
  `BY_NAME`/`DEFAULT`/`METRIC_RULES` konzisztencia. Két kezdeti teszt-elvárás **az én hibám
  volt** (a `θαρρ-` a koiné oldal, nem a marked; az `unify` szabály-**neveket** vár, nem
  `Rule` objektumot) — a tesztet igazítottam, nem a modult.
- ÚJ `test_style_view.js`: **0 failure** — valódi végpont-válaszon: 4 sor + fej, nincs
  `undefined`/`NaN`, mind a négy irány **prózában** jelenik meg (ismeretlen irány a nyers
  tokenre esik vissza), a null arány em-dash nem `null`, üres szabálylista saját üzenetet kap,
  XSS: `<img>`/`<b>`/`<i>`/`<u>` escape-elve mind a táblában, mind a jegyzetekben,
  tulajdonnév-lábjegyzet csak nemnulla esetén, kiegyensúlyozott tagek.
- `test_arch_view.js`: **0 failure** — +4 állítás a poolozott sor kinyilatkoztatására
  (a split-div pontosan a poolozott sorokon jelenik meg).
- Regresszió: `test_arch.py`, `test_cluster.py`, `test_align.py`, `test_group.js`, `test_refs.js`
  0 failure · `validate_canon.py` 0 hiba / 0 figyelmeztetés · `check_no_restricted.py` OK ·
  `node --check app/static/app.js` OK.

Él-végpont mátrix: `mode=STYLE` (kis-nagybetű-érzéketlen) → `mode=style`; `variants=none` →
0 szabály; `variants=tt` → 1; `variants=xyn,nope` → 1 (ismeretlen eldobva); `mode=garbage` →
lexical fallback; `drop_proper=0` → a `tt` nyers rátái (0.176/1.361) jelennek meg;
nem létező mű → 404.

**TODO:**
- Az elágazás kész, de a **harmadik referencia-korpusz** (2. pont) nélkül a ráták még mindig
  nem ítéletek. A Tier-2 `cts.perseids.org` úton 350 `cts_confirmed` mű van a 2–7. századból
  (Sokrates, Sozomenos, Theodoretus HE, Euagriosz, Zószimosz, Agathiasz, Athanasziosz,
  Kürosz) — ez a kortárs koiné bázis, külső függőség nélkül.
- 1. pont (Morpheus `greek.ml` lemma-réteg) és 5. pont (KWIC kattintásra, párhuzamos
  locus-keresés a meglévő Flame motorral, 2-/3-gram frazeológia) hátravan; a sorrend
  szerint előbb az 5. (független rész), aztán az 1–2. (lemma + háromutas modell).

---

## Archaizmus #5. pont: KWIC, párhuzamos locus-keresés, 2-/3-gram frazeológia

Az utolsó „független rész". A kiindulás a felhasználó mondata: „`WHERE IN B: 8.2.10`
egymagában nem elég". Egy sor a riportban **állítás**, és az az állítás, aminek a
bizonyítéka egy kattintásra van, ellenőrizhető; amelyik külön oldalon van, nem lesz
ellenőrizve.

### 1. Új modul: `app/loci_pure.py` (stdlib-only)

Három, egymástól független funkció:

- **`kwic(sections, keys, ..., rule=None)`** — keyword-in-context. `keys` a poolozott
  kulcs: egy token akkor találat, ha a **saját poolozott** alakja a kulcs, tehát egy sor,
  aminek a száma `ξυμμαχία` + `συμμαχία` összege, **mindkettőt** mutatja — épp ezért
  pooloztuk. A `span` **szavakban** van, nem karakterekben (a karakterablak elvágja a
  görög szavakat, és két különböző hosszú locus összehasonlíthatatlan lesz).
  `per_key` korlátozza egy szó hozzájárulását, és a `truncated` jelzi, ha vágott —
  enélkül a olvasó megszámolná a locusokat, és azt hinné, a többi nincs meg.
  A találat `marked` mezője megmondja, melyik szabály szerint visel a token MARKED alakot.
- **`sentences(sections)`** — mondatbontás a kiadások írásjelein (`.;·!?`), cikkszám-címke
  megtartásával. A visszatérési érték tartalmazza a **hosszeloszlást** (`min/median/p90/max`):
  a hosszú, írásjel nélküli függőbeszéd 300 szavas „mondatokat" ad, és ezt tudni kell,
  mielőtt hasonlósági pontszámokat hasonlítunk össze.
- **`parallel_loci(sections_a, query_words, n, min_shared, max_words)`** — A mondatai
  TF-IDF koszinusszal rankelve, **a motor saját** `_idf`/`_tfidf`/`cosine` függvényeivel.
  Két őr tartja őszintén: `min_shared` (egy találatnak legalább ennyi közös 2-/3-gramot
  kell mutatnia — a rövid mondatok koszinuszát a funkciószavak dominálják, és a közös
  frazéma nélküli „párhuzam" hamis barát), és `max_words` (a túl hosszú, írásjel nélküli
  futamok csak azért pontoznának magasan, mert mindent tartalmaznak). Mindkettő **kizár**,
  nem lesúlyoz, és a kizártak száma (`n_dropped`, `n_skipped_long`) a válaszban van.
- **`ngram_table`** / **`ngram_contrast`** — 2-/3-gram frazeológia. A `ngram_table` soronként
  **két** alakot ad vissza: `gram` a nyomtatott (eredeti, ékezetes) ablak olvasáshoz, és
  `pooled` a poolozott ablak, amire a szám megy. Nem fölcserélhetők: A `ἡ ξυμμαχία`-ja és
  B `ἡ συμμαχία`-ja **ugyanaz a frazéma**, és ezt csak a poolozott alak mondja meg. Ezért
  az `ngram_contrast` a **poolozott** gramra indexel — a nyomtatottra indexelve pont azt
  a megfelelést jelentené hiányként B-ben, amit keresni jött.
  A `ngram_contrast` a **művek** szószámával oszt (`total_a`/`total_b` paraméter), nem a
  tábla saját összegével: egy `context` tábla minden gramot **minden** benne szereplő
  kulcs alatt megszámol, így a `total`-ja sorösszeg, nem tokenszám — azt nevezőnek adni
  csendes mértékegység-hiba lenne. A pontszám ugyanaz a Haldane–Anscombe korrigált
  log2 ráta-arány, mint a lexikai riportban, tehát a sorok összehasonlíthatók.

Amit **szándékosan nem** csinál: nincs stemming/lemmatizálás (az az 1. pont, Morpheus),
nincs írásjelnél mélyebb mondatbontás, és nincs fuzzy párhuzamkeresés (azt a
`flame_pure.compare_iter` már tudja; ez a szándékosan olcsó, magyarázható, egy-horgonyos
változat, amely a nyers bizonyítékát is kiadja).

### 2. Három új végpont (`app/server.py`)

`/api/loci/<a1>/<w1>/<a2>/<w2>?word=|rule=`, `/api/ngrams/...?word=&n=2|3`,
`/api/parallel/...?word=&label=&index=|q=`. Mindhárom `window=False`-szal tölti a szöveget,
mint az archaizmus-számlálás — a locusoknak és a gramoknak **ugyanabból** a tokenfolyamból
kell jönniük, amiből a sor számai, különben a bizonyíték nem tudja igazolni a számot,
amelyik mellé ki van írva.

A `word` a **megjelenített** szó (ékezetes alak a riportból); a poolozási kulcsot a
szerver származtatja, ugyanazzal a függvénnyel, amivel a szám készült. A kliens **soha**
nem poolol maga: a megfelelési szabályok második implementációja JavaScriptben egy
második hely lenne, ahol elromolhatnak.

**`rule=`** — a stílustábla sorai **nem szavak**. `ξυ` nem szó, és kulcsként keresve
`σύ`-t („te") találna és semmi mást; amiről a sor szól, az „minden ξυ-vel írt szó", amit
csak a szabály tud megválaszolni. Két látszólagos döntés, valójában nem az:
a szabályt a **nem-poolozott** normalizált alakon kell tesztelni (a poolozás megsemmisíti
a markot, amit keres — `ξυμμαχία` → `συμμαχια`, ami már nem kezdődik ξυ-vel), és a
szabály a `(rule,)` listán megy, **nem** a `variants`-on (különben egy szabály sora halott
lenne, mert az olvasó kipipálta a poolozását). A szabálynevet a szerver az **engine
regiszteréhez** validálja (`VARIANT_RULE_NAMES`), így a kitalált név 400 a valódi listával,
nem üres találat, ami „erre a szóra sosem használja"-nak látszik.

### 3. Front-end (`app/static/app.js`)

- A lexikai tábla szó-cellája és a stílustábla marked-cellája **kattintható**
  (`data-arch-word` / `data-arch-rule`), pontozott aláhúzás hoverre.
- `_evUrl` / `_evLoad` / `_evLociHtml` / `_evNgramsHtml` / `_evParallelHtml` — az
  evidence-panel renderelői. A KWIC két hasábban (A és B), a marked alak kiemelve
  (`<mark class="ev-marked">`, a szabály nevével tooltipben). A stílus-sor panelje
  `rule` módban **kimondja**, hogy nem szóról van szó, és **nem kínál** frazeológiát
  (az szóra kulcsolt; egy szabály alaktípus, nem szó, ami köré frazéma formálható) —
  és meg is mondja, miért.
- Minden B-találat mellett `‖ parallel` gomb → a B-ablak (±10 szó) ellen rankelt A-mondatok,
  a **közös 2-/3-gramok kiírva** a pontszám mellé. Ez a lényeg: egy közös szó nem bizonyít
  semmit, egy közös frazéma igen.
- `_wireEvidence(box)` — egyetlen delegált click-handler az egész találati dobozon,
  `box.dataset.evWired` őrrel. A panel minden betöltésnél teljesen cserélődik, így a
  csomópontra kötött listener újrakötést igényelne — és a hamarosan cserélendő csomópontra
  kötött listener pontosan így szerez magának kétszer tüzelő kattintásokat.

### 4. CSS

`.arch-evidence`, `.ev-head`, `.ev-cols`, `.ev-kwic`, `.ev-parallel`, `.ev-locus`,
`.ev-context`, `mark`, `.ev-mini`, `.ev-score`, `.ev-shared`, `.ev-note`, `.ev-actions`,
`.arch-table td[data-arch-word]`/`[data-arch-rule]` + hover, és 760px alatt egy hasáb.
A kiemelés `color-mix(in srgb, var(--accent) 22%, transparent)` — szín helyett halvány
háttér, hogy monokróm nyomtatásban is átjöjjön.

### Módosult

ÚJ: `app/loci_pure.py`. `app/server.py` (`_with_works`, `VARIANT_RULE_NAMES`, 3 route,
3 handler-ág, `rule` validálás), `app/static/app.js`, `app/static/styles.css`,
`.claudesignore` (3 új forrásfájl a térképen: `archaism_pure.py`, `variants.py`,
`loci_pure.py`).

### Tesztelve

- ÚJ `test_loci.py`: **OK** — 60+ állítás szintetikus szövegen: KWIC poolozás + poolozás
  kikapcsolva; `span` a szakasz-határon csonkol; `per_key` vág **és kinyilatkoztat**
  (`n_hits` a teljes számot adja); elíziós töredék nem találat, `drop_elided=False`
  visszahozza; `rule=` kulcs a szabályon, a nem-poolozott alakon, poolozástól függetlenül,
  és **`σύ`-t találna a kulcs-keresés** — a szabály-út léte nem elméleti; mondatbontás
  címkékkel és belső indexszel; cikkszámok nem lesznek bag-dimenziók; `parallel_loci`
  megtalálja az ikermondatot, a közös 2-/3-gram **poolozva** (`συμμαχοι εγινοντο` ←
  `ξύμμαχοι ἐγίγνοντο`); `max_words` kihagy **és számol**; `min_shared` kemény küszöb;
  üres query és csak-számjegy query nem ad mindent; `ngram_table` bins/pooled/display/
  contentful; egy ablak **két** kulccsal két sor; `ngram_contrast`: a poolozott gramok
  **összeérnek** (A ξυ- vs B συ-), egyenlő ráták → pontszám 0,0, Haldane az `B=0` esetre
  véges, `max_b`/`min_a` szűr, a nevező a mű szószáma.
  Négy kezdeti teszt-elvárás **az én hibám volt** (a fixture 9.9 szakasza is tartalmazta
  a szót; a `max_words` default 400, nem 20; a `γίγνεται` poolozva `γινεται`, nem
  `γινομαι`; a `n_skipped_long` a default cap alatt 0) — a tesztet igazítottam, nem a modult.
- ÚJ `test_ev_view.js`: **0 failure** — valódi végpont-válaszokon mindhárom panel: close
  gomb, két hasáb, occurrence-számok, truncation kinyilatkoztatva, `±span` kiírva, üres
  oldal saját üzenettel; n-gram tábla sor+fej, gram-méret váltó, `display` a nyomtatott
  alakot adja (a poolozott kulcs **nem** kerül a frazéma-oszlopba), a nevező kiírva
  (locale-tűrő minta: a Node itt NARROW NO-BREAK SPACE-t tesz a ezresek közé);
  parallel panel pontszámokkal, `shared:` bizonyítékkal, 3-gram megkülönböztetve, az
  over-long kihagyás csak nemnulla esetén; **rule-panel**: kimondja hogy szabály, kiírja
  a tokenszámot, nem kínál frazeológiát és megmondja miért, de parallel-t igen;
  XSS mind a négy mezőben; minden tag kiegyensúlyozott.
- ÚJ `test_ev_wire.js`: **0 failure** — a **delegált click-handler** valódi forrásból,
  minimál DOM-stubbal, **valódi fixture-ökkel** (a stub az URL alapján dönt, és az URL a
  teszt tárgya): pontosan egy listener, a második `_wireEvidence` nem köt újra; szó-cella
  → `/loci` a helyes mű-párra, URL-encodolva, a poolozás-választással; szabály-cella →
  `rule=` **névvel**, `word=` nélkül (hogy egy szabályt ne lehessen szónak nézni);
  parallel gomb → `label`/`index` helyesen vágva, a `word` a **nyitott panel** szava
  (a modul saját állapotából, nem keményített értékből); n-gram gomb → `n` a gombból,
  a küszöbök a panel inputjaiból; vissza-occ gomb; close nem indít kérést; ismeretlen
  target nem indít kérést; `null` event target nem dob; összehasonlítás előtt nincs kérés.
- Regresszió: `test_arch.py`, `test_variants.py`, `test_cluster.py`, `test_align.py`,
  `test_arch_view.js`, `test_style_view.js`, `test_group.js`, `test_refs.js` 0 failure ·
  `validate_canon.py` 0 hiba / 0 figyelmeztetés · `check_no_restricted.py` OK ·
  `node --check app/static/app.js` OK · `compare_stream` él-adaton 908 pár / 939 NDJSON
  sor `done`-ig (az engine érintetlen).

Él-végpont: a UI **által ténylegesen épített** 10 URL mind 200 — `loci` `variants=all|none|xyn,tt`,
`rule=xyn|gign` poolozással és anélkül, `ngrams` n=2 és n=3, `parallel` szabad `q=`-val és
`label`+`index`-szel. Hibaterek: `rule=bogus` → 400 + a valódi szabálylista; `word=...` →
400 („nincs betűje"); `word` nélkül `loci`/`ngrams` → 400; nem létező mű → 404;
`span=nan&limit=abc&per_key=undefined` → 200, minden default.

**A két legerősebb új bizonyíték**, amit ez a pont hozott felszínre:
- `rule=xyn` KWIC, **mindkét mű első sora**: Thuküdidész `1.1.1` → `ξυνέγραψε`;
  Prokopiosz `1.1.1` → `ξυνέγραψεν`. A paritás-eredmény (12.790 vs 12.851 /1k) itt
  token-szintű inkarnációt kap: a nyitóige írásmódja ugyanaz.
- `parallel` a `3.19.6` prokopioszi locusra: `1.77.3` — `…τὸν ἥσσω τῷ **κρατοῦντι** ὑποχωρεῖν`
  / `…τοῖς τὰ δίκαια προτεινομένοις … τῷ **κρατοῦντι**` (közös bigram), és `6.24.3`
  `ὁ δὲ πολὺς ὅμιλος καὶ **στρατιώτης**` / `καὶ **στρατιώτης** τῷ κρατοῦντι`.

**TODO:**
- A 4. és 5. pont kész; hátravan az **1. (Morpheus `greek.ml` lemma-réteg)** és a
  **2. (harmadik, kortárs referencia-korpusz)** — ezek a modell szintjén függenek össze,
  és a ráták ítéletté csak a 2. után válnak.
- A `_FUNCTION_WORDS` lista kézzel írt és görög funkciószavakra szűk; ha egy szöveg
  bag-dimenziói közt sok a jelöletlen funkciószó-gram, bővíteni kell — ez **megjelenítési**
  jelző, nem stoplista, semmit nem távolít el.
- `scripts/serve.py` (PID 549513) **régi kódon fut** — a felhasználónak újra kell indítania.

## 2026-09-21 — 1. pont: lemmatizálás és inflexiós aggregáció (`lemmas_pure.py`)

**Kérés (szó szerint):** „`ὁπλίτας`/`ὁπλῖται`/`ὁπλιτῶν` must collapse to one lemma `ὁπλίτης`,
with the inflectional breakdown expanding on click."

**A lemmaforrás döntése — és amit a döntés nem tudott teljesíteni.** A választott forrás a
Morpheus `greek.ml` lexikon volt. Ez **nem letölthető adatfájl**: a `greek.ml` a Morpheus
C-forrásából a `mks` eszközzel **lefordított** stemlib (bináris), a morfológiai tudás pedig
a `stemlib/` `.src` fájlokban C-nyelvű szintaxissal (unifikációs szabályok) áll — kiolvasása
vagy a Morpheus-C befordítása új bináris/külső függőséget jelentene, amit a projekt szabálya
(„igyekszünk mentesek lenni a kódban minden külső függőségtől") kizár. Ezért **nem** kötöttük
be, hanem a Megara-ben megismert, mérhető viselkedést képeztük le a repó saját eszközeivel:
deklarált toldalék-szabálytábla + **korpusz-resolver**. A Morpheus-tekintély így nem
hivatkozás, hanem a szabálytábla névadója és a pontosság-mérés kalibrálója.

**Architektúra (3 réteg, mind stdlib, 0 új függőség):**
1. **Zárt osztály + paradigma** — `_CLOSED` / `_PARADIGM`: memorizált olvasatok (névelő,
   kötőszó, névmás, prepozíció, δέ/τε/…). Ezek **kivétel nélkül nyernek** a szabály-olvasatok
   ellen, és soha nem korpusz-súly dönt róluk. `φ`-os, `ττ`-s alakok külön kulcson.
2. **Toldalék-szabálytábla** — `RULES` (`LemmaRule`: név, szófaj, végződés, lemma-sablonok,
   `stem_min`, `drop`, `stem_re`). A sablon többes száma **nem hezitálás, hanem deklaráció**:
   `-ου` valóban 2. decl. genitivus *és* 1. decl. masculinum genitivus. Az augment-leválasztás
   (`_AUGMENT_TENSES` + `ε`-kezdetű tő) adja `ἐποίησε` → `ποιεω` és `ἐλύθη` → `λυω` második
   olvasatát.
3. **Korpusz-resolver** — `LemmaIndex._pass1()` durva kezdet, majd `_settle(rounds=2)`
   **minden körben nulláról** újraszámolja a besorolást. Az `analyse(form)` a gyorsítótárazott
   `_keys`-ből ad `(candidates, chosen, ambiguous)` hármast.

**A központi hiba, amit a resolver javít (ez volt a blokkoló):** egy alak **nem szavazhat a
saját egyértelműsítéséről**. A `_key()` levonja az adott alak saját token- és forma-számát
minden olyan kandidátusból, amit az előző kör hozzá rendelt — önkitöltő visszacsatolás nélkül
a `θαλάσσης` (24 token) felfújta az első körben tippelt lemmát, és felülírta a korpusz
többi alakja által támogatott olvasatot. A tesztek ezt **invarianciaként** rögzítik: tízszeres
önfrekvencia nem változtathatja meg az alak lemmáját.

**A rangsorolás, mérve (nem érvelve) — `_key` tuple:**
`(-declension_family, -support, -match_length, -weight, -neuter, declaration_index)`

- **MATCH LENGTH** (`len(rule.ending)`) önmagában nem elég: `ἐγένετο` `-ο`-ra végződik
  (legitím neutrum nominativus) *és* `-ετο`-ra (imperf. medium). Rövid találatnál a főnév- és
  melléknévtábla **nyelte el** az igéket (`ἐγένετος`, `ἐποίησος`, `γενέσθη`, `κατέστος`).
- **SUPPORT** (hány **különböző** korpusz-alak választotta ezt a lemmát, `self.fcount`)
  **megelőzi a token-súlyt**: a `πολύς` 151 tokent hordoz mindössze 3 alakban, a `πόλις` 92-t
  9 alakban — súly szerint rendezve a `πόλεως` 47 thuküdidészi tokenben a `πολύς`-hoz került.
- **Sorrend-kísérlet, ami megbukott:** a hossz elé sorolása a `λόγος`-t `λοξ`-ra vitte a `-γος`
  tőhangzó-szabályon át (7 alaknyi bizonyíték elvesztése 3 betűért). A support-first
  **73,43% → 73,74% exact, 70,14% → 71,30% purity** (Thuküdidész, éles tokenek).
- **`declension_family` — ez teszi lehetővé a kért paradigmát.** Az `ὁπλίτας`, `ὁπλῖται`,
  `ὁπλίταις`, `ὁπλίτην` mind ambivalens a masculinum `-ης` és a femininum `-η` között; a
  femininum olvasatok **négyen vannak ketten ellen**, így a formaszám a rossz családot teszi
  elsőnek, és az `ὁπλίτας`/`ὁπλῖται`/`ὁπλιτῶν` **két kulcsra szakad** — pontosan az a hiba,
  amit ez a réteg javítani hivatott, pontosan a kérésben megnevezett paradigmán. Amit dönt:
  a kandidátus **saját paradigmája által megjósolt** esetalak jelenléte a korpuszban —
  masculinum: `stemου` genitivus (az `-ου` **soha** nem 1. decl. femininum genitivus);
  femininum: `lemma + ν` acc. singularis. Számozva (`2`/`1`), mert nem egyenlő erejűek: az
  `-ου` egyértelmű, a `θαλασσαν` csak annyit mond, hogy femininum — és számozni kell, mert
  `ὁπλίτης` alaknál **mindkettő** tüzel, és egyenlően rendezve a support visszaadja
  `ὁπλιτη`-nek. Mindkettő őrzött: (a) a vizsgált alak nem tanúskodhat saját magáról
  (`πολεμου` **az** a `stemου` string → `πολεμης` önigazoló; ez 25 tokenben pont ezt a hibát
  hozta létre), (b) `stemος` jelenléte kizárja a 2. decl.-t (`αλλου`/`πολεμου` a `αλλος`/
  `πολεμος` genitivusa, nem `-ης` headword).
- **NEUTER:** amelyik főnév töve `-α` pluralist mutat a korpuszban, az neutrum → `-ον` alakja
  **önmaga** alá kerül (`χωρίον`), nem `-ος` alá (`χώριος`); `λόγᾱ` nem alak, ezért
  `λόγον` → `λόγος`. Melléknevek kizárva (`νέον` = `νέος` masc acc.).
- **Elutasított kandidátusok, rögzítve** (hogy újra ne javasoljuk): nominativus-alak
  önlemmává emelése (73,73% vs 73,74%, és a `μέρη` neutr. pluralis önmaga alá kerül);
  `a_acc_sg_f`/`a_gen_pl` kiszélesítése masculinumra **a family-tag nélkül** (−0,37 pont);
  a family support **alá** sorolása (mérve 74,01%/71,58% — mégis rossz, mert nem javítja azt
  az esetet, amiért van: a kért paradigma két kulcsra szakad).
- **`_FORM_PREF = {"ων": "ος", "ω": "ος", "η": "η"}`** — kulcs **és** érték normalizált (a
  `_c()` normalizált lemmát tárol): `ων`: `ὅς` 82 vs `εἰμί` 13; `ω`: `ᾧ` 38 vs `ὦ` 14;
  `η`: `ἡ` 139 vs `ὁ` 101; kontraszt: `ην`-nél az `εἰμί` 131–43-ra vezet, ott nincs csere.

**Poolozás (`variants.unify`) LEGVÉGÜL történik:** `key_of(lemma) = unify(lemma)`. A
`θάλασσα`/`θάλαττα` a **saját írásmódján** lemmatizálódik — a ττ/σσ megfelelés az, amit a
stílusjelentés mér, és a `unify` eltünteti — és csak azután találkoznak egy kulcson. A
teszt ezt rögzíti: `θαλαττης` ≠ `θαλασσης` lemma, de `key_of` mindkettőre `θαλασσα`.

**Pontosság — `ACCURACY` a modulban, gold treebanken mérve** (Perseus AGDT v2.1,
CC BY-SA 3.0; Thuküdidész 1 + Polybius; fejlesztés idején, **nem** redistribuálva, futásidőben
**nem** olvasva; éles tokenek, az elíziós töredékek kihagyva):

| corpus | exact | within | ambiguous | unreduced | purity | noun | adj | verb | adv |
|---|---|---|---|---|---|---|---|---|---|
| Thuküdidész 1 | **74,40%** | 81,07% | 15,53% | 12,44% | **71,30%** | 86,0% | 71,8% | 50,7% | 88,8% |
| Polybius 1–2 | **74,18%** | 80,93% | 11,40% | 10,63% | **72,58%** | 86,6% | 72,2% | 56,2% | 87,1% |

Purity = a gold lemma tokenjei hány **különböző** aggregációs kulcsra esnek szét (a
konzisztensen rossz headword még egyben tartja a lexémát; két kulcs **kettészeli a rátát** —
ez az, amit javítani kellett). A maradék szakadás irregularis/suppletiv igetövek
(`γιγνομαι` → `γενω`/`γινω`/`εγενομενος`; 13–25 vödör), amit toldalék-szabállyal nem lehet
visszanyerni — ezért **kimondjuk** (szófaj szerinti purity), nem hajszoljuk tovább.
A legnagyobb megmaradó hibaosztály az ékezetek/légzések `normalize`-törlése
(`ἀλλά`/`ἄλλα`, `οἵ`/`οἱ`, `ὅ`/`ὁ`, `ἕν`/`ἐν`, `ὧν`/`ὤν`, `αὐτῶν`/`αὑτῶν`): **ambiguitásként
kimondva**, lexikon vagy tagger nélkül nem javítható.

**A UI-követelmény (kattintásra nyíló inflexiós bontás):** minden sor
`data-lemma-toggle` + a következő `<tr class="lemma-forms" hidden>`; a bontás alakonként
írja a megjelenített alakot, szófajt, `infl`-t, forrást (`closed`/`paradigm`/`rule`/
`unreduced`), a szabály nevét, `count_a`/`count_b`-t és a versengő olvasatokat. A fejléc
kiírja a **mért** pontosságot (exact/within/purity_noun/purity_verb) és a figyelmeztetést:
„egy sort jelöltként olvass, ne idézetként".

**Él-verifikáció:** `0003.001 → 4029.001`, `mode=lemma`: 43 739 alak → 20 513 lemma,
tömörítés **2,132**, 2,6 s; sorok lemma szerint összegezve, `n_forms_a`, ambiguitás-számmal.
Lemma-módú `loci` kiterjesztés a kulcs **összes** alakjára: `οπλιτη` 5 alak / 143+2 találat,
`θαλασσα` 3 alak / 166+96, `πολις` 2 alak / 337+352.

**Módosult:** `app/lemmas_pure.py` (ÚJ, ~1750 sor), `app/server.py` (`lemmas_pure` import,
`mode=lemma` ág, `min_a`/`min_b`/`max_b`/`min_score` **szándékosan nem** átadva — ez a
jelentés nem `contrast` pontszámmal rangsorol; `/api/loci` lemma-ág + `mode` a válaszban),
`app/static/app.js` (`_archMode`, `<option>`, `_archSyncMode`, `_evUrl` `mode`-merge,
`_lemmaHtml` renderer, `data-lemma-toggle` ág a delegált handlerben), `app/static/styles.css`
(`.lemma-forms` blokk), `.claudesignore` (1. szekció + mappa-fa: `lemmas_pure.py`,
`loci_pure.py`).

**Tesztelve:** ÚJ `test_lemmas.py` **31/31 OK** — kézzel épített korpuszokon (a resolver
**korpusz**-resolver, nem lexikon: 8 tokenen nincs mit számolnia, és a deklarációs sorrend
döntene — ezt a teszt fejében ki is mondjuk, és minden korpusz ismétli a paradigmát, ahogy a
próza teszi). Lefedi: a teljes `ὁπλίτης`-paradigma **egy** kulcson (16 token / 8 alak) és a
bontás összege = a sor száma; a 2. decl. ferde esetek nem szivárognak külön sorba;
ττ/σσ külön lemma, egy kulcs; a family-inferencia femininum-vezérlője (`τιμης`/`τιμην` →
`τιμη`, mert nincs `τιμου`); ön-felfújás invariancia; neutrum/masculinum; augment; a
`ACCURACY` valódi (nem placeholder) és `describe()` ugyanazt adja; a `lemma_key_lookup` és a
`key_forms` egyezik és a sor számához összegez; ismeretlen kulcs `found=False`.

Regresszió: `test_arch.py`, `test_cluster.py`, `test_loci.py`, `test_variants.py`,
`test_align.py` 0 failure · `test_arch_view.js`, `test_style_view.js`, `test_ev_view.js`,
`test_ev_wire.js` 0 failure · `node --check app/static/app.js` OK.

**TODO:**
- **2. pont** (harmadik, kortárs koiné referencia-korpusz) — a ráták ítéletté csak utána
  válnak; a First1KGreek-en át, új külső függőség nélkül.
- **3. pont** (allúzió-kereső vs. stílusregiszter-kereső szétválasztása) — nincs elkezdve.
- A headword **neve** a korpusztól függ: ha a nominativus és a `-ου` genitivus is hiányzik
  a szövegből, a kulcs a femininum-látszat (`οπλιτη`) lesz — az **aggregáció ilyenkor is
  egyben marad**, csak a kiírt headword nem az idézési alak. (Thuküdidész 1-ben pontosan ez
  a helyzet: 16 `ὁπλίτης`-token, csupa ferde eset.) A UI ezt jelzi a pontosság-figyelmeztetéssel.
- A resolver deklarációs sorrendre támaszkodása rövid paradigmáknál elkerülhetetlen
  (korpusz-bizonyíték híján); a teszt ezt nem is próbálja kikényszeríteni.
- `scripts/serve.py` (PID 549513) **régi kódon fut** — a felhasználónak újra kell indítania.
- **Nyitott, destruktív döntést igénylő ügy:** a nyilvános `kreeedit/KONI` repóban a HEAD
  követi a `.claude-isolated-config/`-ot (520 fájl, benne 4 `.key` és 17 session-átirat);
  a javítás `git filter-repo` + force-push, ezért **ehhez semmihez nem nyúltam**, és ebben
  a sessionben **semmit nem commitoltam**.

## 2026-09-21 — 2. pont: harmadik, kortárs koiné referencia-korpusz (`app/archaism_pure.py`)

A felhasználói kritika lényege: az eddigi felület „nem archaizmust mér, hanem témakülönbséget
és szókincskopást". Ez a pont azt a hiányzó **harmadik korpuszt** köti be, ami a két rátát
ítéletté teszi. Új archaizmus-definíció (számokkal alátámasztva, nem kijelentve):

    archaism = Gyakoriság_A magas  ∧  Gyakoriság_koiné ≈ 0  ∧  B TÖBBET használja, mint A

**Fájlok:** `app/archaism_pure.py` (új: `KOINE_REFERENCE`, `_classify`, `koine_contrast`,
`koine_report`, `MIN_AC`/`MIN_BC`/`MIN_REVIVAL`, `CLASS_ORDER`), `app/server.py`
(`mode=koine` + `ref=<aid>/<wid>`, `koine_reference` az envelope-ban), `app/static/app.js`
(`_koineHtml`, `ARCH_CLASSES`, `KOINE_DEFAULTS`, `_archReconcileReference`), `app/static/styles.css`,
`.claudesignore`, `log.md`.

**A referencia-korpusz:** Szókratész Szkholasztikusz, `Historia Ecclesiastica`
(`urn:cts:greekLit:tlg2057.tlg002`, 4–5. sz. AD, 104 575 token). First1KGreek/CTS úton
érkezik a **meglévő** `texts` úton — nulla új függőség, nulla canon-módosítás. Műfaj
szándékosan egyezik (történetírás), csak a regiszter tér el: pontosan az a zavaró tényező,
amiről a kritika szól.

**A mérés, ami a tervet eldöntötte** (A = Thuküdidész 1 = 147 693 token, B = Prokopios
de Bellis = 222 699, C = Szókratész = 104 575):

- A felhasználói kritérium **szó szerint** véve (A magas ∧ C ≈ 0 ∧ B > 0) **5485 szóból 1378-at
  ad (25%)** — `συμμαχοι`, `νηες`, `θερους`, `σικελια`: egyháztörténésznek nincs flottája,
  nincs Szicíliája. A `contrast` `B=1` artefaktja helyett tehát a C-abszencia ugyanaz a
  téma-zavar, csak átköltöztetve.
- A harmadik konjunkció (`score_ab ≤ -0.5`, azaz B **felülhasználja** a szót a saját
  mintaszerzőjéhez képest) **341-re (6–7%)** vágja: `σφισιν`, `σφισι`, `σφων`, `ταλλα`,
  `ηκιστα`, `ενθενδε`, `νω`, `ονπερ`, `ξυνηνεχθη`, `λαθρα`, `πανταπασιν`, `διαφεροντως` —
  ezek **grammatikai/megjelölt** elemek, nem topikális lexika.
- A besorolás mérve: `archaism` 339 · `classical` 1006 · `overused` 250 · `avoided` 1930 ·
  `shared` 1169 (min_a=3, drop_proper után, 4694 szó). **Az elkerülés (vocabulary attrition)
  a nagyobb hatás, mint az archaizálás** — a kritika saját állítása, most számmal.
- A régi jelentés top-200 sora **0 archaizmust** tartalmaz (148 topik-vezérelt, 52 `avoided`),
  és a `MAX_B=1` miatt szerkezetileg **nem is érheti el** a jelenséget: `σφισιν` (0.89→1.94/1k)
  és `καιπερ` (0.12→0.49) meg sem jelenhet ott. Ezért az új jelentés a `contrast`-tól
  **függetlenül** szkenneli a szókincset (csak `min_a` a belépő), és minden sor mindhárom
  nyers számot + mindhárom rátát kiírja.
- A legfelső valódi sor: `ἐς` (A 1804 / B 4245 / C 0) — az attikai/ion `ἐς` a koiné `εἰς`-szel
  szemben; `σφίσιν` (C=0) a koiné `αὐτοῖς`-szel szemben. A tükör-eset: `ἐκκλησία`
  (A 11 / B 1 / C 97) `avoided` — a szekuláris archaizáló kerüli az egyházi koiné szókincsét.
- **Ami statisztikailag nem dönthető el, kimondva:** a `καρχηδονα`, `στρατω`, `πολιορκιαν`,
  `ποταμος`, `πεδιω` sorok az `archaism` osztályban maradnak, mert Justinianus háborúi
  többet beszélnek ostromról, folyóról, síkságról, mint Thuküdidész 1. könyve. Ezért minden
  sor kap `marked_b` oszlopot (a `variants` által B saját tokenjeiben látott attikai
  írásmód-választás: `ξυν-`, `ττ`), ami megkülönbözteti a grammatikai revíziót a topiktól —
  ellenőrzésre, nem hitre.

**Tesztelve:** ÚJ `test_koine.py` **48/48 OK** — szintetikus háromkorpuszos számokon
(az osztályozó hat szám függvénye, a valós figurák rögzítése a korpuszt tesztelné, nem a
kódot), plusz a valós három művön a mérési állítások: a küszöb nélküli szabály túlenged
(`classical` 1006 > `archaism` 339), az `archaism` kisebbség (7.2%), `avoided` > `archaism`,
a top sor a `ἐς`, és a `marked_b` a B saját írásmódjából olvasódik. Regresszió: `test_arch`,
`test_variants`, `test_lemmas`, `test_loci`, `test_align`, `test_cluster` 0 failure ·
`node --check app/static/app.js` OK · élő HTTP-ellenőrzés: `mode=koine` 4694 szó, minden
UI-mező létezik (nincs `undefined`-drift), hibás `ref` → 400, olvashatatlan `ref` → 404.
(A teszt-harness — mint a korábbiak — a session munkakönyvtárában van, nem a repóban:
`.claude-isolated-config/jobs/88b99e67/tmp/test_koine.py`; `PYTHONPATH=.:scripts` kell hozzá.)

**TODO:**
- **3. pont** (allúzió-kereső vs. stílusregiszter-kereső szétválasztása) — nincs elkezdve;
  a mostani `archaism` osztály topik-maradványa (`καρχηδονα`, `ποταμος`) pont ennek a
  szétválasztásnak a legjobb teszt-esete.
- `scripts/serve.py` **nem fut** — a felhasználónak újra kell indítania (a teszt-szervert leállítottam).
- A `σφισιν`/`νω` típusú soroknál a lemma-szint (1. pont) még nincs összekötve ezzel a
  jelentéssel: a háromkorpuszos nézet surface formon számol, a lemma-aggregáció külön mód.
- **Nyitott, destruktív döntést igénylő ügy:** a nyilvános `kreeedit/KONI` repóban a HEAD
  követi a `.claude-isolated-config/`-ot (520 fájl, benne 4 `.key` és 17 session-átirat);
  **ebben a sessionben semmit nem commitoltam.**

---

## 2026-09-23 — Olvasófelület: LSJ szótár, jegyzetek, export

A kiindulás a felhasználó kérése: „…be kellene csatornázni egy görög szótárat is ami
segítheti az olvasást, megérts, a szövegeket exportálni lehessen, lehessen kijelöléseket
csinálni és exportálni, menteni az annotációkat, szóval az olvasófelületet egy kicsit
felhasználóbarátabbá tenni." Négy rész: (a) szótár, (b) szöveg-export, (c) kijelölés →
jegyzet → mentés/export, (d) általános olvasó-UX. Mind a négy kész; a (d) kimerül a
szótár-fiókban, a szerkesztő-sávban és a billentyű-parancsokban.

### 1. Béta-kód ↔ Unicode: mérés, nem találgatás (`app/betacode.py`)

A tábla (`c`=ξ, `x`=χ, `)`=pszilé, `(`=dasia) **mérésből** származik, nem feltevésből: a
döntő bizonyíték az LSJ saját szójegyzéke (a `lang="greek"` jelöléssel ellátott
`<orth>`/`<quote>` elemek szövege a helyes Unicode-alakkal együtt szerepel a glossban) —
pl. `a)ei/dw` glosszája „sing" → ἀείδω (pszilé), `a(li/skomai` „to be taken, conquered"
→ ἁλίσκομαι (dasia), `ce/nos` = ξένος, `xe/nos` sehol. A tábla minden sora
`describe()`-ben hordozza a rá vonatkozó bizonyítékot, és a `test_betacode.py` assertálja
őket — így egy későbbi „javítás" nem tudja csendben elrontani.

Két buktató, amit a kód név szerint kezel:
- **Kanoniális sorrend:** a `U+0390` (ΐ) dekompozíciója `<ι, 0308, 0301>` (diasziszisz
  előbb), az LSJ viszont `dai/+` alakot ír (akut előbb). Mindkét jel ccc=230, ezért az NFC
  soha nem cseréli fel őket → a `_compose` a jelöléseket `(combining(m), m != DIAERESIS)`
  szerint rendezi.
- **Nyelvvakság:** a béta-kód és az angol is ASCII, ezért a `decode` önmagában nem tudja
  szétválasztani őket — a döntést a **jelölés** (`lang="greek"`) hozza. A `decode_prose`
  ezért a `looks_greek(token)` (magánhangzó/ρ után közvetlenül jelölés) heurisztikát
  használja a kevert szövegű prózához; a docstring kimondja, hogy `st(h)`/`and/or` típusú
  bemeneten ez elvi korlát, nem hiba.

**Mérve:** a `PerseusDL/treebank_data` v2.1 arany 2543 lemmáján a round trip **2541/2543 =
99.92%** (a 2 hiba az arany-adat latin `v`-tippje, nem a kód); a round trip azonban
**csak a jelölés-csatolást** bizonyítja, a lehelet irányát nem — ezt a docstring ki is
mondja.

### 2. Szótár-építés (`scripts/fetch_lsj.sh`, `scripts/build_lexicon.py`)

- `fetch_lsj.sh`: újrakezdhető, **rögzített commit** (`56061ca1…`), `curl --retry 3`,
  skip-if-parses. 27 szelet, 271 MB.
- `build_lexicon.py` (~380 sor): `ET.iterparse` streamelve, minden elemet töröl — a 271 MB
  soha nem kerül memóriába, a teljes korpusz pedig nem kerül a kontextusba. Görög csak ott,
  ahol `lang="greek"` (`orth`/`quote`/`foreign`/`gen`/`etym`).
- **Kétszintű index:** `index` (címszavak, mérvadó) vs. `index_forms` (az LSJ által idézett
  ragozott alakok, csak találat hiányában) — ez azért teherviselő, mert a szinonima/idióma
  álnevek (pl. `ξενος` → ξένη) különben eltakarnák a valódi szócikket.
- **Etimológiai sense kihagyása** strukturális teszttel: az átírás az LSJ nyomtatott
  etimológiai bekezdését egy 1-es szintű sense-be csomagolja, amelynek `n`-je **ismétlődik**
  (`ἔχω`: `['A','A','B','C']`) → ha az első `n` megismétlődik, az a sense eldobandó. E
  nélkül az `ἔχω` glosszája szanszkrit és latin rokon szavakból állt.
- **Egy dokumentum-sorrendű menet** (`seen_gloss` a kiválasztott sense első `<tr>`-jéig):
  korábban az `ἄξιος` szócikk minden `<foreign>`-je forma lett, ezért a **`λόγου` az
  `ἄξιος`-hoz** oldódott („ἄξιος λόγου" idióma). Ugyanígy az `εὐπέμπελος` 5 szavas
  Aiszkhülosz-idézetéből az első token került be formaként (`ἔχουσι`) — a javítás: az
  **egy szavas** teszt a nyers szövegen fut, nem a `_clean_head` után.
- **Mérve:** 116 497 szócikk · 119 543 címszó-kulcs · 9 388 idézett forma · 27 szelet ·
  31 MB · építés ~10 s.

### 3. Keresés és végpontok (`app/lexicon.py`, `app/server.py`)

Lánc: normalizált alak → címszavak → idézett formák → `lemmas_pure.candidates` +
variáns-**poolozás** (`app.variants.unify`, pl. `ξυμμάχων` → `συμμαχος`) → lemma-szócikk.
A válasz `match` mezője (`head`/`form`/`lemma`) és az `analysis` tömb szándékosan
**különválasztja a szótár tényét a morfológiai olvasattól**: hogy egy alak nem címszó, az
információ, nem hibaüzenet. Új végpontok: `GET /api/lexicon?word=…[&a1=&w1=&a2=&w2=]`
(előfordulás-számmal, ha a mű meg van adva) és `GET /api/lexicon/info` (manifest +
attribúció). A modul lusta (`lookup.json` az első hívásra, 4-es LRU a szeletekre), futásidőben
**nem hálózik**.

### 4. Olvasófelület (`app/static/app.js`, `app/static/styles.css`)

- **Szótár-fiók** (jobb oldali, rögzített `#drawer`, két fül): szóra kattintva
  `caretRangeFromPoint` → görög szó (`\p{Script=Greek}\p{M}`) → `/api/lexicon`. Kiírja a
  címszót, a glosszát (vagy a `note`-ot), a címkéket, az idézett alakokat, a **más
  olvasatokat**, az előfordulásszámot („`<key>`-val egyező tokenek, ékezet nélkül"), a
  Perseus-linket és a CC BY-SA attribúciót. Széles képernyőn a fiók **helyet kér**
  (`body.drawer-open .reader-pane { padding-right }`), nem takarja a szöveget.
- **Kijelölés → jegyzet:** kijelölésekor úszó „✎ annotate" gomb → popover (jegyzet + tagek)
  → `localStorage["koni.annotations"]`, verziózott borítékban, munkánként szűrve. A
  **horgony a kijelölt szöveg, nem a karakter-offszet**: ha a kiadás változik, a kiemelés
  egyszerűen nem talál, a jegyzet viszont megmarad és exportálható.
- **Kiemelés:** a blokk szövegcsomópontjaiból összefűzött szövegen, **whitespace-re
  kollapszált** alakban keresünk, egy oda-vissza index-térképpel (a választás szövege és a
  DOM szövege máshogy egyezik meg a soremelésekről). A sor-számok (`lnum`) kimaradnak a
  kijelölésből és a keresésből is.
- **Jegyzet-fül:** listázás szakaszonként, ugorj a helyre, szerkesztés, törlés,
  **export JSON / Markdown**, **import JSON** (ütköző id újraosztva, nem felülírás).
- **Export:** „⤓ section" / „⤓ whole work" — fejléces plain text, a szakaszok a kiadás
  sorszámaival, a végén a jegyzetek függeléke. A fejléc **nem talál ki licencet** a
  szövegre: azt írja, hogy az app által szolgáltatott nyílt kiadás, és a Sources listára
  irányít; hiányzó kiadásnevet pedig kimond („as recorded by the app"), nem hagy üresen.
- **UX:** `[`/`]` szakasz-léptetés (beviteli mezőben nem lopja el), `Esc` zárás, a
  **szakasz a cím része** (`#/read/aid/wid/idx`), és a `route()` felismeri, ha már ezt a
  művet olvassuk — ilyenkor csak a szakaszt tölti, nem rendereli újra a nézetet.

### Módosult

`app/betacode.py`, `app/lexicon.py` (ÚJ), `app/server.py`, `app/static/app.js`,
`app/static/styles.css`, `data/lexicon/README.md` (ÚJ), `.gitignore`, `.claudesignore`;
ÚJ scriptek: `scripts/fetch_lsj.sh`, `scripts/build_lexicon.py`, `scripts/validate_lexicon.py`.
A `data/lexicon/out/` (31 MB) generált és git-ignorált; a README az egyetlen követett fájl
a `data/lexicon/` alatt.

### Tesztelve

- ÚJ `validate_lexicon.py`: **18/18 OK** — minden állítás azt a hibát nevezi meg, amit
  rögzít (`λόγου`/`ἄξιος`, `ἔχουσι`/`εὐπέμπελος`, `ξυμμάχων` poolozás, `ἔχω` etimológia,
  `ξαίνω` paradigma, attribúció, nincs kötőjel a címszavakban).
- ÚJ `test_reader.js`: **66 állítás OK** — a szótár-panel mondanivalója (a `head`/`form`/
  `lemma` három különböző mondat, a lemma-találat „nem szótári tény"-ként jelölve, alternatív
  olvasatok, hiányzó szótár → építési parancs, nulla előfordulás nem „találat", XSS-mindent
  escape-elve, nincs `undefined`/`NaN`), a **kollapsz-index-térkép** mint invariáns, az
  exportok (szakasz/mű/jegyzet JSON+MD, hibás szakasz `FAILED` jelöléssel a fájlban),
  az import (ütköző id, idézet nélküli eldobva, hibás fájl jelentve), a delegáció
  (melyik selector nyer, törlés-megerősítés, `#ann-file`), és a billentyűk. A szótár-végpont
  hiányát (régi szerver) külön ág kezeli: „restart it", nem „build the dictionary" — pont az
  a hiba, amibe a felhasználó most azonnal belefut.
- ÚJ `test_highlighter.js`: **36 állítás OK** — a kiemelés a szöveget *díszíti*, tehát az
  egyetlen rész, ami csendben **elronthatja** az olvasott szöveget. Mini-DOM (text node,
  elem, `Range.surroundContents` a spec szerinti darabolással) fölött a rögzített tulajdonság:
  a kiemelés után a szavak pontosan azok a szavak. Lefedi a whitespace-kollapszálást
  (a nyers szöveg, nem a kollapszált alak kerül kiemelésre), a sorszám (`lnum`) kizárását
  mind a kijelölésből, mind a keresésből, a **több csomóponton átnyúló** idézetet (per-node
  darabolás — itt dobna a `surroundContents`), az **átfedő** jegyzeteket, az újrafestést,
  és a blokk szélén/egészén lévő idézetet. Az én két elvárásom itt is hibás volt
  (a határon végződő idézet 2 csomópontot érint, nem 3-at; az átfedő jegyzet 3 span lesz,
  nem 2) — a tesztet igazítottam, a kódot nem.
- A harness **három valódi hibát** talált a saját kódomban: (1) a kollapszált szóköz a
  következő karakterre mutatott az index-térképben (egy karakterrel elcsúszó kiemelés);
  (2) a kiválasztott morfológiai olvasat nem írta ki a ragozási jegyet; (3) verssor utáni
  próza-blokk elvesztette az üres sorát a szöveg-exportban. Plusz egy szemle-hiba: a
  szótár-fül visszaváltáskor felülírta a megjelenített szócikket a súgóval.
- Regresszió: `test_arch`, `test_variants`, `test_lemmas`, `test_loci`, `test_align`,
  `test_cluster`, `test_koine`, `test_betacode` **0 failure** · `test_arch_view`,
  `test_group`, `test_refs`, `test_style_view`, `test_ev_view`, `test_ev_wire` 0 failure ·
  `validate_canon.py` 0 hiba / 0 figyelmeztetés · `node --check app/static/app.js` OK.
- Szemle (nem teszt): a `.drawer`-en `display: flex` felülírja a UA `[hidden]` szabályát,
  ezért `.drawer[hidden] { display: none }` kellett — enélkül a fiók **mindig** látszott
  volna. Ugyanez a csapda a `.ann-btn`/`.ann-pop` páron már eleve kezelve volt.
- Élő: `GET /api/lexicon?word=…` — `λόγου → λόγος`, `ξυμμάχων → σύμμᾱχος` (poolozva),
  `ἔχουσι → ἔχω` (lemma), `ξένος → ξένος` (címszó); `λόγου` **nem** `ἄξιος` többé.
  `0012/001` (Iliász) szakasz-végpont 611 `line` blokkot ad, `n` sztringként (az export
  `padStart`-tal igazítja).
- **Üzemeltetési csapda, amibe belefutottam:** a 8123-as teszt-szerver a **10:41-es
  újraépítés előtt** indult, és a memóriában tartott `lookup.json`-index miatt a **régi**
  adatot szolgálta (`λόγου → ἄξιος`, `ξυμμάχων` semmi). A `data/lexicon/out/` újraépítése
  **szerver-újraindítást igényel** — a szelet- és index-gyorsítótár processzen belüli.

**TODO:**
- **A felhasználó `scripts/serve.py`-át újra kell indítani** (PID 1318466): a futó példány
  a szótár-végpontok és az új olvasó-UI előtt indult. A teszt-szervert (8123) leállítottam,
  majd az új kóddal újraindítottam.
- Ismert korlátok, szándékosan kimondva: **blokkon átnyúló kijelölés** esetén a jegyzet
  elmentődik és listázódik, de a szövegben nem lesz kiemelve (a horgony egy blokkhoz
  kötött); a kiemelés idézet-egyezésen múlik, kiadásváltásnál eltűnik (a jegyzet marad);
  mobilon a fiók fedvény, nem oszlop; a szótár csak görög szóra nyílik.
- **Nyitott, destruktív döntést igénylő ügy (változatlan):** a nyilvános `kreeedit/KONI`
  repóban a HEAD követi a `.claude-isolated-config/`-ot (520 fájl, benne 4 `.key` és 17
  session-átirat); **ebben a sessionben semmit nem commitoltam.**
- Az archaizmus-kritika **3. pontja** (allúzió-kereső vs. stílusregiszter-kereső
  szétválasztása) továbbra sincs elkezdve.

## 2026-09-24 — Javítás: `POPOVER_HTML is not defined` az olvasóban

### Mit csináltam

- A `#/read/0004/001` útvonal `Error: POPOVER_HTML is not defined` hibát dobott: a
  `renderReader()` a `$view().innerHTML` sablonjában hivatkozott egy `POPOVER_HTML`
  konstansra, ami **soha nem létezett** a fájlban (`git log -S POPOVER_HTML` csak a
  használatot találja, definíciót egyik commitban sem).
- A jegyzet-popover már a bd0778d refaktor óta **futásidőben** épül fel a `_popover()`
  függvényben (`app/static/app.js:689`), ezért a statikus sablon-hivatkozás felesleges
  maradvány. A `DRAWER_HTML` ezzel szemben létezik (`:419`), az marad.
- Javítás: a `${meta.has_text ? POPOVER_HTML : ""}` sor törölve (`app/static/app.js:328-329`).
  Új konstans nem kellett — a popover a `_openPopover()` első hívásakor jön létre és
  a `document.body`-ra kerül, nem a nézet-sablonba.

### Módosult

`app/static/app.js` (1 sor törölve). log.md.

### Tesztelve

- `node --check app/static/app.js` → OK.
- Ellenőrizve, hogy nincs több azonos mintájú hivatkozás: `grep -o '\${[A-Z_][A-Z_0-9]*}'`
  nulla találat, minden `UPPER_CASE` konstans (`DRAWER_HTML`, `API`, `PAGE`, `ANNOT`, …)
  definiálva van a fájlban.
- Élő szerver **nem futott** (`curl http://127.0.0.1:8000/` → 000), ezért böngészős
  smoke-teszt nem történt — a hiba egy referencia-feloldási hiba volt, ami a nézet
  felépítése előtt dobott, így a törléssel megszűnik.

**TODO:**
- A `scripts/serve.py` szervert újra kell indítani, és a `#/read/0004/001` útvonalat
  böngészőben ellenőrizni (olvasó renderel, szótár-fül nyílik, jegyzet-popover megjelenik
  szövegkijelölésre).
- Változatlan nyitott ügy: a `.claude-isolated-config/` (520 fájl, benne 4 `.key`)
  követése a nyilvános repóban — destruktív döntést igényel.

# Claude Code Projekt Szabályzat

Üdvözöllek ebben a projektben! Te egy autonóm AI szoftvermérnök vagy. Ahhoz, hogy maximális hatékonysággal és minimális API-költséggel dolgozz, SZIGORÚAN be kell tartanod az alábbi szabályokat:

## 1. Indítás és Tájékozódás (Bootstrapping)
- Minden új session kezdetén az ELSŐ dolgod, hogy elolvasod a .claudesignore fájlt! 
- Ez a fájl nem csak a tiltásokat tartalmazza, hanem a kommentek között ez a hivatalos Repótérképünk. Ebből fogod megérteni a mappa-struktúrát, a fájlok darabszámát és funkcióját. Ne használj find parancsot a felfedezésre, amíg ezt nem olvastad el!

## 2. Költség- és Tokenvédelem (Vakság)
- A .claudesignore fájlban tiltott adatmappákat (pl. CSV-k, bináris adatok, parquet fájlok, nagy szövegkorpuszok) FIZIKAILAG tilos beolvasnod!
- Ha feltétlenül szükséged van egy tiltott fájl adatszerkezetére (schema), használd a terminált: `head -n 5 data/fajlneved.csv` paranccsal olvass be belőle 5 sort. Ezt az 5 sort használd a feldolgozó kód megírásához! SOHA ne olvasd be a teljes fájlt!

## 3. Rövidtávú Memória (log.md)
- A projektben folyamatosan vezetjük a log.md fájlt.
- Mielőtt egy meglévő funkcióhoz nyúlsz, olvasd el a log.md tartalmát, hogy tudd, hol hagytuk abba a munkát tegnap, és mik a jelenlegi ismert hibák.
- KÖTELEZŐ: Minden nagyobb logikai egység, refaktorálás vagy sikeres tesztelés után a legutolsó lépésed az legyen, hogy frissíted a log.md fájlt! Röviden, bullet-pointokban írd le: 
  - Mit csináltál?
  - Milyen fájlok módosultak?
  - Mi a következő javasolt lépés (TODO)?

# KONI gaps report — the open backlog

This report is generated from `data/canon.json` by `scripts/build_gaps_report.py`. It makes KONI's existing `cts_confirmed` / `proposed` signals explicit: each row below is a place where open metadata, an open text, or an authority link is still missing — i.e. a candidate for high-value open-data work by the community. The canon is the *publicly reconstructable* portion of the TLG canon, so this backlog is never *complete*; it is an open mirror of what is currently available.

## Summary

- Authors: **3274** — works: **8816**

- Works with an open text (`cts_confirmed=true`): 1622/8816 (18.4%)

- Works flagged `proposed` (no open text yet): 7194/8816 (81.6%)

- Authors matched to Wikidata: 1924/3274 (58.8%)

- Authors with a VIAF id: 0/3274 (0.0%)

- Authors with an era/floruit: 1153/3274 (35.2%)

- Authors with a Greek name form: 604/3274 (18.4%)

- Authors with works but no open text at all: 2181

- Authors attested in the canon with zero works: 750


## Author-level gaps

### No Wikidata match (1350)

These authors could not be reconciled to a Wikidata Q via the TLG-id (P3576) property. Adding the `P3576` statement on Wikidata, or supplying an alternative authority link, closes the gap.

- Arcesilai
- Pausaniae I Et Xerxis
- Pisistrati
- Phalaridis
- Thrasybuli
- Periplus Maris Erythraei
- Anonymi Grammatici
- Periplus Ponti Euxini
- Periplus Maris Magni
- Anonymi Geographiae Expositio Compendiaria
- Zenonis
- Archias
- Anonymi Epigrammatici
- Erycius Cyzicenus
- Gaetulicus
- Mantissa Proverbiorum
- Mace(donius)
- Anonymi Curetum Hymnus
- Anonymi Hymnus In Dactylos Idaeos
- Lyrica Adespota (CA)
- Elegiaca Adespota (CA)
- Elegiaca Adespota (IEG)
- Iambica Adespota (IEG)
- [Homerus]
- Nautarum Cantiunculae
- _…and 1325 more_


### No VIAF id (3274)

VIAF coverage currently relies on the Wikidata `P214` property, which is sparse for TLG authors. See `docs/` for the open-source back-fill investigation. Until then these authors carry no VIAF `skos:exactMatch`.

_Top 25 of 3274: Apollonius Rhodius, Theognis, Thucydides, Diogenes Laertius, Theocritus Bucol., Euripides, Plutarchus, Athenaeus, Sappho, Isocrates, Sophocles, Homerus, Hymni Homerici, Demosthenes, Herodianus, Herodotus, Isaeus, Philo Judaeus, Aristophanes, Hesiodus, Nicander, Oppianus, Oppianus, Aeschines, Andocides_


### No era / floruit (2121)

Best-effort era comes from Wikidata `P569/P570/P2348`. Authors without it have `era: null`.

- Diogenes Laertius
- Hymni Homerici
- Novum Testamentum
- Arcesilai
- Mithridatis
- Alexandri Magni
- Pausaniae I Et Xerxis
- Pisistrati
- Phalaridis
- Themistoclis
- Thrasybuli
- Pseudo-Lucianus
- Dionysius
- Periplus Maris Erythraei
- Anonymi Grammatici
- Periplus Ponti Euxini
- Zelotus
- Periplus Maris Magni
- Menippus
- Anonymi Geographiae Expositio Compendiaria
- Pseudo-Plutarchus
- Aceratus
- Adaeus
- Aemilianus Rhetor
- Agis
- _…and 2096 more_


### No Greek name form (2670)

Greek names come from the Wikidata Greek label / the TLG canon. Their absence is mostly a coverage limit, not a data error.

- Herodianus
- Oppianus
- Oppianus
- Antiphon
- Dinarchus
- Anacharsidis
- Arcesilai
- Mithridatis
- Calani
- Chionis
- Alexandri Magni
- Pausaniae I Et Xerxis
- Pisistrati
- Ptolemaei II Philadelphi Et Eleazari
- <Melissa>
- Phalaridis
- <Theano>
- Themistoclis
- Thrasybuli
- Galenus
- Aeneas
- Diodorus Siculus
- Pseudo-Lucianus
- Agatharchides
- Pseudo-Scymnus
- _…and 2645 more_


## Work-level gaps

### Works with no open text yet (`proposed`, 7194)

These works are attested in the TLG canon but have no openly-licensed text in the Perseus CTS catalogue. In `canon.jsonld` they are flagged `koni:proposed`, i.e. KONI *suggests* the CTS URN that does not yet resolve. Publishing an open TEI edition for any of these (and registering the CTS URN) closes the gap and is the highest-value contribution an independent researcher can make here.

- **Apollonius Rhodius** — *Fragmenta* — `urn:cts:greekLit:tlg0001.tlg002`
- **Apollonius Rhodius** — *Epigrammata* — `urn:cts:greekLit:tlg0001.tlg003`
- **Theognis** — *Elegiae* — `urn:cts:greekLit:tlg0002.tlg001`
- **Theognis** — *Epigrammata* — `urn:cts:greekLit:tlg0002.tlg004`
- **Thucydides** — *Epigramma* — `urn:cts:greekLit:tlg0003.tlg002`
- **Diogenes Laertius** — *Epigrammata* — `urn:cts:greekLit:tlg0004.tlg002`
- **Diogenes Laertius** — *Vitae philosophorum* — `urn:cts:greekLit:tlg0004.tlg003`
- **Theocritus Bucol.** — *Fragmentum* — `urn:cts:greekLit:tlg0005.tlg004`
- **Theocritus Bucol.** — *Epigrammata* — `urn:cts:greekLit:tlg0005.tlg005`
- **Euripides** — *Cretum (part of Fragmenta Papyracea)* — `urn:cts:greekLit:tlg0006.tlg021`
- **Euripides** — *Epinicium in Alcibiadem* — `urn:cts:greekLit:tlg0006.tlg022`
- **Euripides** — *Fragmenta Phaethontis* — `urn:cts:greekLit:tlg0006.tlg023`
- **Euripides** — *Fragmenta Alexandri* — `urn:cts:greekLit:tlg0006.tlg025`
- **Euripides** — *Hypsiples Fragmenta* — `urn:cts:greekLit:tlg0006.tlg026`
- **Euripides** — *Fragmenta Phrixei* — `urn:cts:greekLit:tlg0006.tlg027`
- **Euripides** — *Fragmenta fabulae incertae* — `urn:cts:greekLit:tlg0006.tlg028`
- **Euripides** — *Fragmenta Oenei* — `urn:cts:greekLit:tlg0006.tlg030`
- **Euripides** — *Epigrammata* — `urn:cts:greekLit:tlg0006.tlg031`
- **Euripides** — *Fragmenta* — `urn:cts:greekLit:tlg0006.tlg053`
- **Plutarchus** — *Aetia Romana et Graeca* — `urn:cts:greekLit:tlg0007.tlg084`
- **Plutarchus** — *De libidine et aegritudine* — `urn:cts:greekLit:tlg0007.tlg143`
- **Plutarchus** — *Parsne an facultas animi sit viva passiva* — `urn:cts:greekLit:tlg0007.tlg144`
- **Plutarchus** — *Fragmenta* — `urn:cts:greekLit:tlg0007.tlg145`
- **Sappho** — *Fragmenta* — `urn:cts:greekLit:tlg0009.tlg001`
- **Sappho** — *Epigrammata* — `urn:cts:greekLit:tlg0009.tlg002`
- _…and 7169 more_


### Authors with works but zero open texts (2181)

Every work by these authors is `proposed` — none has an open TEI text yet. These authors are the clearest targets for new open editions.

- Theognis
- Sappho
- Arcesilai
- Calani
- Alexandri Magni
- Amasis
- <Melissa>
- Menippus
- <Theano>
- Zelotus
- Xenocritus Rhodius
- Aceratus
- Adaeus
- Aemilianus Rhetor
- Aeschines
- Agis
- Alcaeus
- Alexander Magnes
- Alpheius Mytilenensis
- Ammianus
- Ammonides
- Andronicus
- Antiochus
- Antipater of Sidon
- Antipater of Thessalonica
- _…and 2156 more_


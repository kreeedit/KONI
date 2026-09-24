# data/lexicon — a reading-aid dictionary (LSJ)

The reader panel that answers "what does this word mean" reads from here.
Nothing in this directory is fetched at runtime and nothing here is required
for the rest of the app to work: if it is absent, the dictionary panel says so
and the reader still reads.

## What is here

| path | what | in git? |
|---|---|---|
| `raw/` | the 27 source slices, `grc.lsj.perseus-eng1..27.xml`, ~271 MB | no |
| `out/NN.json` | one built slice: entries + two lookup indexes | no |
| `out/lookup.json` | normalised form -> slice number, so a lookup opens one slice | no |
| `out/manifest.json` | counts, provenance, attribution, licence | no |

Only this README and the build scripts are in git. The corpora themselves are
too large for a repository and are regenerated instead.

## Build

```bash
scripts/fetch_lsj.sh          # resumable: a slice that parses is not refetched
python3 scripts/build_lexicon.py
python3 scripts/validate_lexicon.py --builder
```

`fetch_lsj.sh` pins the upstream commit, so a rebuild next year produces the
same index rather than following an upstream edit. `build_lexicon.py` is also
resumable (a slice whose output exists is skipped; `--force` rebuilds) and
takes about ten seconds for all 27 slices.

## Source, licence, attribution

**Liddell, H. G., Scott, R., Jones, H. S., & McKenzie, R. (1940). *A
Greek-English Lexicon*. Oxford: Clarendon Press.** Digitised by the Perseus
Digital Library (`PerseusDL/lexica`,
`CTS_XML_TEI/perseus/pdllex/grc/lsj/`), licensed **CC BY-SA 4.0**.

This build is a MODIFIED version, which the licence requires us to say:

* the text was transliterated from Perseus/TLG **Beta Code** to Unicode Greek
  (`app/betacode.py`);
* each entry was reduced to headword, gloss, grammatical labels, cited
  inflected forms and the Perseus entry id;
* the full entry text is not reproduced — the app links to Perseus for it.

The attribution is also carried in `out/manifest.json` and served to the UI by
`/api/lexicon/info`, so the panel can display it rather than relying on this
file being read.

## How a lookup works

`app/lexicon.py`. A form from a text is normalised (accents stripped, the same
`flame_pure.normalize` the rest of the app uses), then tried against headwords,
then against the inflected forms LSJ itself cites, and finally reduced by
`lemmas_pure` and looked up by lemma. The result always says which of the three
answered, because a dictionary fact and a morphological reading are not the
same kind of evidence.

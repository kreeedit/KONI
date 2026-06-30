#!/usr/bin/env python3
"""KONI — add a JSON-LD / Linked Open Data view of the canon.

Run from the PROJECT ROOT:

    python3 apply_jsonld_patch.py

Creates (additive — no existing file is modified):

  schema/context.jsonld    A publishable JSON-LD @context. Anchors the canon on
                           LAWD / SKOS / Dublin Core / PROV, with Wikidata (wd:)
                           and VIAF (viaf:) prefixes for cross-links.

  scripts/build_jsonld.py  Pure-stdlib converter. Reads data/canon.json, joins
                           Wikidata QIDs from the cached Wikidata intermediate,
                           and writes:
                             data/canon.jsonld   full JSON-LD (@context + @graph)
                             data/canon-links.nt the SAFE cross-reference subset
                                                 (with --links): N-Triples linking
                                                 koni:/Scaife URIs to public
                                                 Wikidata/VIAF URIs only — no TLG
                                                 bibliographic content.

After running, build the LOD view with:

    python3 scripts/build_jsonld.py            # -> data/canon.jsonld
    python3 scripts/build_jsonld.py --links    # also -> data/canon-links.nt

Safe to re-run (existing targets are backed up to *.bak.<ts> first).
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sys
import time

ROOT = pathlib.Path.cwd()
STAMP = time.strftime("%Y%m%d-%H%M%S")


def _need_root() -> None:
    if not (ROOT / "scripts" / "common.py").exists() or not (ROOT / "schema").exists():
        sys.exit("[ABORT] Futtasd a projekt gyökeréből (ahol a scripts/ és schema/ van).")


def _write(rel: str, text: str) -> None:
    fp = ROOT / rel
    fp.parent.mkdir(parents=True, exist_ok=True)
    if fp.exists():
        bak = fp.with_name(fp.name + f".bak.{STAMP}")
        shutil.copy2(fp, bak)
        print(f"    backup -> {bak.name}")
    fp.write_text(text, encoding="utf-8")
    print(f"  wrote {rel}")


# --------------------------------------------------------------------------
# The JSON-LD @context (single source of truth; build_jsonld.py embeds it).
# --------------------------------------------------------------------------
CONTEXT = {
    "@version": 1.1,
    "id": "@id",
    "type": "@type",

    "koni": "https://w3id.org/koni/tlg/",
    "lawd": "http://lawd.info/ontology/",
    "dcterms": "http://purl.org/dc/terms/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "schema": "https://schema.org/",
    "prov": "http://www.w3.org/ns/prov#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "wd": "http://www.wikidata.org/entity/",
    "viaf": "https://viaf.org/viaf/",

    "Author": "lawd:Author",
    "Work": "lawd:Work",

    "name_la":  {"@id": "skos:prefLabel", "@language": "la"},
    "name_grc": {"@id": "skos:altLabel",  "@language": "grc"},
    "name_en":  {"@id": "rdfs:label",     "@language": "en"},
    "title_la":  {"@id": "dcterms:title", "@language": "la"},
    "title_grc": {"@id": "dcterms:title", "@language": "grc"},
    "title_en":  {"@id": "dcterms:title", "@language": "en"},

    "epithet": "dcterms:subject",
    "floruit": "dcterms:temporal",
    "edition": "dcterms:bibliographicCitation",
    "tlg_id":  "dcterms:identifier",
    "cts_urn": "dcterms:identifier",

    "ctsConfirmed": {"@id": "koni:ctsConfirmed", "@type": "xsd:boolean"},
    "proposed":     {"@id": "koni:proposed",     "@type": "xsd:boolean"},

    "exactMatch":  {"@id": "skos:exactMatch",  "@type": "@id"},
    "closeMatch":  {"@id": "skos:closeMatch",  "@type": "@id"},
    "derivedFrom": {"@id": "prov:wasDerivedFrom", "@type": "@id"},
    "inScheme":    {"@id": "skos:inScheme", "@type": "@id"},
    "source":      {"@id": "dcterms:source", "@type": "@id"},
    "references":  {"@id": "dcterms:references", "@type": "@id"},
    "author":      {"@id": "dcterms:creator", "@type": "@id"},
    "works":       {"@id": "dcterms:hasPart", "@type": "@id"},
}


# --------------------------------------------------------------------------
# scripts/build_jsonld.py  (raw string: JS-style/Python escapes emitted verbatim)
# --------------------------------------------------------------------------
BUILD_JSONLD = r'''"""Emit a JSON-LD (Linked Open Data) view of the KONI canon.

Reads data/canon.json, joins Wikidata QIDs from the cached Wikidata
intermediate (data/intermediate/wikidata_era.json), and writes a JSON-LD graph.

  data/canon.jsonld    Full JSON-LD: self-contained @context (from
                       schema/context.jsonld) + an @graph of author nodes with
                       embedded work nodes. Language-tagged labels (la/grc/en),
                       skos:exactMatch -> Wikidata (wd:) and VIAF (viaf:),
                       prov:wasDerivedFrom -> source URIs, and a stable koni:
                       @id for every entity. Confirmed works link to a
                       dereferenceable Scaife URL via exactMatch; unconfirmed
                       works are flagged koni:proposed = true (a *suggested*
                       URI for a resource that has no authority record yet).

  data/canon-links.nt  (with --links) The SAFE cross-reference subset only:
                       N-Triples linking koni:/Scaife URIs to PUBLIC Wikidata /
                       VIAF URIs (plus identifiers and hasPart). It carries no
                       TLG names/epithets/editions, so it is the redistributable
                       Linked-Open-Data contribution. (canon.jsonld itself is
                       built from the TLG-derived canon and stays local.)

Pure standard library. Run after scripts/build_canon.py.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # so `import common` works
import common

SCAIFE = "https://scaife.perseus.org/library/{urn}/"

# The printed authority that defines the TLG author/work numbering scheme KONI
# reconstructs. Cited (not derived-from) at the ConceptScheme level. The @id is
# the stable WorldCat record; identifiers carry the ISBN/OCLC.
SOURCE_WORK = {
    "id": "koni:source/tlg-canon-1990",
    "type": "schema:Book",
    "dcterms:title": "Thesaurus Linguae Graecae: Canon of Greek Authors and Works",
    "schema:bookEdition": "3rd ed.",
    "dcterms:creator": ["Luci Berkowitz", "Karl A. Squitier", "William A. Johnson"],
    "dcterms:publisher": "Oxford University Press",
    "dcterms:date": "1990",
    "dcterms:extent": "lx, 471 p.",
    "dcterms:language": "en",
    "dcterms:bibliographicCitation":
        "Berkowitz, Luci, and Karl A. Squitier, with technical assistance from "
        "William A. Johnson. Thesaurus Linguae Graecae: Canon of Greek Authors "
        "and Works. 3rd ed. New York: Oxford University Press, 1990.",
    # Links to precise, resolvable bibliographic records (not retailer pages):
    "exactMatch": [
        "https://openlibrary.org/books/OL2220683M",
        "https://lccn.loc.gov/89049454",
        "https://www.worldcat.org/oclc/20828572",
    ],
    "dcterms:identifier": [
        "urn:isbn:9780195060379", "urn:isbn:0195060377",
        "urn:oclc:20828572", "urn:lccn:89049454",
    ],
    "rdfs:comment": "Printed authority defining the TLG author/work numbering "
                    "scheme reconstructed by KONI; cited as the source of the "
                    "identifier scheme, not as a data source.",
}

# Greek script ranges (incl. Greek Extended / polytonic).
_GREEK = "\u0370\u03FF\u1F00\u1FFF"


def _first_script(s):
    """Language of a title by its FIRST alphabetic character.

    Titles lead with their primary language, so this correctly keeps a
    Latin title that carries a Greek gloss in parentheses
    (e.g. 'De figuris (= Περὶ σχημάτων)') as Latin, while a Greek title
    mis-filed in the Latin column ('Περὶ Συντάξεως') is recognised as Greek.
    """
    for ch in s:
        o = ord(ch)
        if (0x0370 <= o <= 0x03FF) or (0x1F00 <= o <= 0x1FFF):
            return "grc"
        if ("A" <= ch <= "Z") or ("a" <= ch <= "z"):
            return "la"
    return None


SRC_URI = {
    common.SRC_TLG_CD:   "https://stephanus.tlg.uci.edu/",
    common.SRC_TLG_POST: "https://stephanus.tlg.uci.edu/",
    common.SRC_CTS:      "https://cts.perseids.org/",
    common.SRC_WIKIDATA: "https://www.wikidata.org/",
    common.SRC_BCD:      "https://github.com/bcdavasconcelos/Greek-Authors-and-Works-in-TLG",
}

# CURIE prefixes used in the N-Triples cross-reference graph.
PREFIX = {
    "koni": "https://w3id.org/koni/tlg/",
    "wd":   "http://www.wikidata.org/entity/",
    "viaf": "https://viaf.org/viaf/",
}
P_EXACT = "http://www.w3.org/2004/02/skos/core#exactMatch"
P_ID = "http://purl.org/dc/terms/identifier"
P_HASPART = "http://purl.org/dc/terms/hasPart"
P_BIBCITE = "http://purl.org/dc/terms/bibliographicCitation"

# A work's curated/overlay provenance tier (set in data/local/supplement.json).
# 'restricted:*' is firewalled out of every published artifact; these stay local.
PUBLISHABLE_WORK_TIERS = {"local:curated"}


def _work_publishable(w):
    src = w.get("source")
    if isinstance(src, str) and src.startswith("restricted:"):
        return False
    if w.get("cts_confirmed"):
        return True
    return src in PUBLISHABLE_WORK_TIERS


def _viaf_curie(v):
    s = str(v).strip().rstrip("/")
    num = s.rsplit("/", 1)[-1]
    return "viaf:" + num if num.isdigit() else None


def _dedupe(xs):
    seen = set()
    out = []
    for x in xs:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _one_or_list(xs):
    return xs[0] if len(xs) == 1 else xs


def _expand(curie):
    if curie.startswith("http"):
        return curie
    if ":" in curie:
        pfx, rest = curie.split(":", 1)
        if pfx in PREFIX:
            return PREFIX[pfx] + rest
    return curie


def work_node(aid, wid, w):
    urn = w.get("cts_urn") or f"urn:cts:greekLit:tlg{aid}.tlg{wid}"
    confirmed = bool(w.get("cts_confirmed"))
    n = {
        "id": f"koni:{aid}.{wid}",
        "type": "Work",
        "author": f"koni:{aid}",
        "cts_urn": urn,
        "ctsConfirmed": confirmed,
    }
    if confirmed:
        n["exactMatch"] = SCAIFE.format(urn=urn)   # dereferenceable text
    else:
        n["proposed"] = True                       # suggested URI, no open text yet
    # Language tags follow the title's actual script, not the column name:
    # ~525 works carry a Greek title mis-filed in the Latin column.
    buckets = {"la": [], "grc": [], "en": []}

    def _put(val, default):
        if not val:
            return
        sc = _first_script(val)
        lang = "grc" if sc == "grc" else ("en" if default == "en" else "la")
        if val not in buckets[lang]:
            buckets[lang].append(val)

    _put(w.get("title_latin"), "la")
    _put(w.get("title_greek"), "grc")
    _put(w.get("title_english"), "en")
    if buckets["la"]:
        n["title_la"] = buckets["la"][0] if len(buckets["la"]) == 1 else buckets["la"]
    if buckets["grc"]:
        n["title_grc"] = buckets["grc"][0] if len(buckets["grc"]) == 1 else buckets["grc"]
    if buckets["en"]:
        n["title_en"] = buckets["en"][0] if len(buckets["en"]) == 1 else buckets["en"]
    if w.get("edition"):
        n["edition"] = w["edition"]
    return n


def author_node(aid, a, wikidata):
    n = {
        "id": f"koni:{aid}",
        "type": "Author",
        "inScheme": "koni:canon",
        "tlg_id": f"tlg{aid}",
    }
    if a.get("author_name_latin"):
        n["name_la"] = a["author_name_latin"]
    if a.get("author_name_greek"):
        n["name_grc"] = a["author_name_greek"]
    if a.get("author_name_english"):
        n["name_en"] = a["author_name_english"]
    if a.get("epitheton"):
        n["epithet"] = a["epitheton"]
    if a.get("era"):
        n["floruit"] = a["era"]

    matches = []
    qid = (wikidata.get(aid) or {}).get("wikidata_qid")
    if qid:
        matches.append("wd:" + qid)
    if a.get("viaf_id"):
        vc = _viaf_curie(a["viaf_id"])
        if vc:
            matches.append(vc)
    if matches:
        n["exactMatch"] = _one_or_list(_dedupe(matches))

    derived = _dedupe([SRC_URI[s] for s in a.get("source", []) if s in SRC_URI])
    if derived:
        n["derivedFrom"] = _one_or_list(derived)

    works = [work_node(aid, wid, w)
             for wid, w in sorted((a.get("works") or {}).items())]
    if works:
        n["works"] = works
    return n


def build_graph(canon, wikidata):
    scheme = {
        "id": "koni:canon",
        "type": "skos:ConceptScheme",
        "rdfs:label": "KONI — open machine-readable reconstruction of the TLG "
                      "author/work canon",
        "source": SOURCE_WORK["id"],
    }
    nodes = [author_node(aid, a, wikidata) for aid, a in sorted(canon.items())]
    return [SOURCE_WORK, scheme] + nodes


def nt_lines(canon, wikidata):
    """Build the two publishable N-Triples graphs, with the restricted firewall.

    Returns (links, editions):
      links    - CC0 cross-reference subset: identifiers + skos:exactMatch to
                 Wikidata / VIAF / Scaife (public URIs only).
      editions - source-edition citations: open TEI editions (CC BY-SA) plus
                 your own local:curated entries. Kept in a separate file so the
                 two licences never mix.
    Works whose source tier is 'restricted:*' appear in NEITHER graph.
    """
    lit = lambda s: __import__("json").dumps(s, ensure_ascii=False)
    iri = lambda u: "<" + u + ">"
    links, editions = [], []
    for aid, a in sorted(canon.items()):
        au = PREFIX["koni"] + aid
        emitted_author = False
        matches = []
        qid = (wikidata.get(aid) or {}).get("wikidata_qid")
        if qid:
            matches.append("wd:" + qid)
        if a.get("viaf_id"):
            vc = _viaf_curie(a["viaf_id"])
            if vc:
                matches.append(vc)
        for m in _dedupe(matches):
            links.append(f"{iri(au)} {iri(P_EXACT)} {iri(_expand(m))} .")
            emitted_author = True
        if emitted_author:
            links.append(f"{iri(au)} {iri(P_ID)} {lit('tlg' + aid)} .")
        for wid, w in sorted((a.get("works") or {}).items()):
            if not _work_publishable(w):
                continue                       # firewall: restricted stays local
            urn = w.get("cts_urn") or f"urn:cts:greekLit:tlg{aid}.tlg{wid}"
            wu = PREFIX["koni"] + f"{aid}.{wid}"
            links.append(f"{iri(au)} {iri(P_HASPART)} {iri(wu)} .")
            links.append(f"{iri(wu)} {iri(P_ID)} {lit(urn)} .")
            if w.get("cts_confirmed"):
                links.append(f"{iri(wu)} {iri(P_EXACT)} {iri(SCAIFE.format(urn=urn))} .")
            if w.get("edition"):
                editions.append(f"{iri(wu)} {iri(P_BIBCITE)} {lit(w['edition'])} .")
    return links, editions


def main():
    ap = argparse.ArgumentParser(description="Build a JSON-LD / LOD view of the canon.")
    ap.add_argument("--out", default=str(common.DATA / "canon.jsonld"),
                    help="output JSON-LD path (default: data/canon.jsonld)")
    ap.add_argument("--links", nargs="?", const=str(common.DATA / "canon-links.nt"),
                    default=None,
                    help="also write the publishable graphs as N-Triples: the CC0 "
                         "cross-reference subset (default data/canon-links.nt) and, "
                         "alongside it, data/canon-editions.nt")
    args = ap.parse_args()

    if not common.CANON_JSON.exists():
        sys.exit(f"[ABORT] {common.CANON_JSON} not found — run build_canon.py first.")
    canon = common.read_json(common.CANON_JSON)

    wikidata = {}
    if common.INT_WIKIDATA.exists():
        wikidata = common.read_json(common.INT_WIKIDATA)
        common.log(f"Wikidata QIDs available for {len(wikidata)} authors (for skos:exactMatch).")
    else:
        common.log("No Wikidata intermediate found; emitting without wd: links.")

    ctx_path = common.SCHEMA / "context.jsonld"
    context = common.read_json(ctx_path)["@context"]

    graph = build_graph(canon, wikidata)
    doc = {"@context": context, "@graph": graph}
    common.write_json(Path(args.out), doc)

    n_authors = sum(1 for n in graph if n.get("type") == "Author")
    n_links = sum(1 for n in graph
                  if n.get("type") == "Author" and "exactMatch" in n)
    common.log(f"Wrote {args.out}: {n_authors} authors, {n_links} with a "
               f"Wikidata/VIAF exactMatch.")

    if args.links:
        links, editions = nt_lines(canon, wikidata)
        hdr_links = ("# KONI cross-reference graph (CC0): koni / Scaife <-> "
                     "Wikidata / VIAF identifiers only.\n")
        Path(args.links).write_text(hdr_links + "\n".join(links) + "\n", encoding="utf-8")
        common.log(f"Wrote {args.links}: {len(links)} triples (CC0 cross-reference subset).")

        ed_path = Path(args.links).with_name("canon-editions.nt")
        hdr_ed = ("# KONI edition citations: open TEI editions (CC BY-SA) + your "
                  "local:curated entries. Restricted-tier sources are excluded.\n")
        ed_path.write_text(hdr_ed + "\n".join(editions) + "\n", encoding="utf-8")
        common.log(f"Wrote {ed_path}: {len(editions)} edition citations (publishable).")


if __name__ == "__main__":
    main()
'''


def main() -> None:
    _need_root()
    print(f"KONI JSON-LD patch — projekt gyökér: {ROOT}\nidőbélyeg: {STAMP}\n")
    print("[1/2] schema/context.jsonld")
    _write("schema/context.jsonld",
           json.dumps({"@context": CONTEXT}, ensure_ascii=False, indent=2) + "\n")
    print("[2/2] scripts/build_jsonld.py")
    _write("scripts/build_jsonld.py", BUILD_JSONLD)
    print("\nKész. Építsd meg a LOD-nézetet:")
    print("  python3 scripts/build_jsonld.py            # -> data/canon.jsonld")
    print("  python3 scripts/build_jsonld.py --links    # + data/canon-links.nt")
    print("\nMegjegyzés: a data/canon.jsonld a TLG-eredetű kánonból épül -> a")
    print("data/ amúgy is .gitignore-olt, ne publikáld. A data/canon-links.nt a")
    print("biztonságos, publikus URI-k közti kereszthivatkozási gráf (CC0 Wikidata/VIAF).")


if __name__ == "__main__":
    main()

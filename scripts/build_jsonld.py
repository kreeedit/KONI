"""Emit a JSON-LD (Linked Open Data) view of the KONI canon.

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
    if w.get("title_latin"):
        n["title_la"] = w["title_latin"]
    if w.get("title_greek"):
        n["title_grc"] = w["title_greek"]
    if w.get("title_english"):
        n["title_en"] = w["title_english"]
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
    }
    nodes = [author_node(aid, a, wikidata) for aid, a in sorted(canon.items())]
    return [scheme] + nodes


def nt_lines(canon, wikidata):
    """Safe cross-reference subset as N-Triples (public URIs only)."""
    lit = lambda s: __import__("json").dumps(s, ensure_ascii=False)
    iri = lambda u: "<" + u + ">"
    out = []
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
            out.append(f"{iri(au)} {iri(P_EXACT)} {iri(_expand(m))} .")
            emitted_author = True
        if emitted_author:
            out.append(f"{iri(au)} {iri(P_ID)} {lit('tlg' + aid)} .")
        for wid, w in sorted((a.get("works") or {}).items()):
            if not w.get("cts_confirmed"):
                continue
            urn = w.get("cts_urn") or f"urn:cts:greekLit:tlg{aid}.tlg{wid}"
            wu = PREFIX["koni"] + f"{aid}.{wid}"
            su = SCAIFE.format(urn=urn)
            out.append(f"{iri(au)} {iri(P_HASPART)} {iri(wu)} .")
            out.append(f"{iri(wu)} {iri(P_EXACT)} {iri(su)} .")
            out.append(f"{iri(wu)} {iri(P_ID)} {lit(urn)} .")
    return out


def main():
    ap = argparse.ArgumentParser(description="Build a JSON-LD / LOD view of the canon.")
    ap.add_argument("--out", default=str(common.DATA / "canon.jsonld"),
                    help="output JSON-LD path (default: data/canon.jsonld)")
    ap.add_argument("--links", nargs="?", const=str(common.DATA / "canon-links.nt"),
                    default=None,
                    help="also write the safe cross-reference graph as N-Triples "
                         "(default path: data/canon-links.nt)")
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
        lines = nt_lines(canon, wikidata)
        Path(args.links).write_text("\n".join(lines) + "\n", encoding="utf-8")
        common.log(f"Wrote {args.links}: {len(lines)} triples (safe cross-reference subset).")


if __name__ == "__main__":
    main()

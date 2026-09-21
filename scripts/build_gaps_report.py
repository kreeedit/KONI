"""Build a "gaps" / open-backlog report from data/canon.json.

KONI's `proposed` / `cts_confirmed=false` data model already *signals* where the
open classical-philology infrastructure is incomplete. This script aggregates
those signals into a single human-readable `reports/gaps_report.md` so the
community — and independent researchers looking for high-value work — can see
*where* open metadata, open texts, or authority links are still missing.

Pure stdlib, like validate_canon.py / build_jsonld.py. No new data model.
"""
from __future__ import annotations

import sys
from collections import Counter

from common import CANON_JSON, REPORTS, log, read_json

GAPS_REPORT = REPORTS / "gaps_report.md"
TOP_N = 25  # how many example records to list per gap category


def _pct(n: int, total: int) -> str:
    return f"{(100.0 * n / total):.1f}%" if total else "n/a"


def main() -> int:
    canon = read_json(CANON_JSON)
    authors = list(canon.values())
    n_authors = len(authors)
    n_works = sum(len(a.get("works", {})) for a in authors)

    # --- per-author gap flags -------------------------------------------------
    no_wikidata = []   # authors not matched to a Wikidata Q (no "wikidata" source)
    no_viaf = []       # authors with no VIAF id
    no_era = []        # authors with no era/floruit
    no_greek = []      # authors with no Greek name form
    zero_confirmed = []  # authors with works but none confirmed (no open text at all)
    no_works = []      # authors attested in the canon with zero works

    # --- per-work gaps --------------------------------------------------------
    n_confirmed = 0
    n_proposed = 0
    proposed_examples = []  # (author_name, title, urn)

    for aid, a in canon.items():
        src = a.get("source") or []
        name = a.get("author_name_latin") or aid
        works = a.get("works") or {}
        confirmed_here = 0
        for w in works.values():
            if w.get("cts_confirmed"):
                n_confirmed += 1
                confirmed_here += 1
            else:
                n_proposed += 1
                if len(proposed_examples) < TOP_N and (w.get("title_latin")
                                                      or w.get("title_english")):
                    proposed_examples.append(
                        (name, w.get("title_latin") or w.get("title_english"),
                         w.get("cts_urn")))
        if "wikidata" not in src:
            no_wikidata.append(name)
        if not a.get("viaf_id"):
            no_viaf.append(name)
        if not a.get("era"):
            no_era.append(name)
        if not a.get("author_name_greek"):
            no_greek.append(name)
        if works and confirmed_here == 0:
            zero_confirmed.append(name)
        if not works:
            no_works.append(name)

    log(f"authors: {n_authors} | works: {n_works} | "
        f"confirmed: {n_confirmed} | proposed: {n_proposed}")

    lines: list[str] = []
    add = lines.append

    add("# KONI gaps report — the open backlog\n")
    add("This report is generated from `data/canon.json` by "
        "`scripts/build_gaps_report.py`. It makes KONI's existing "
        "`cts_confirmed` / `proposed` signals explicit: each row below is a "
        "place where open metadata, an open text, or an authority link is still "
        "missing — i.e. a candidate for high-value open-data work by the "
        "community. The canon is the *publicly reconstructable* portion of the "
        "TLG canon, so this backlog is never *complete*; it is an open mirror "
        "of what is currently available.\n")

    add("## Summary\n")
    add(f"- Authors: **{n_authors}** — works: **{n_works}**\n")
    add(f"- Works with an open text (`cts_confirmed=true`): "
        f"{n_confirmed}/{n_works} ({_pct(n_confirmed, n_works)})\n")
    add(f"- Works flagged `proposed` (no open text yet): "
        f"{n_proposed}/{n_works} ({_pct(n_proposed, n_works)})\n")
    add(f"- Authors matched to Wikidata: "
        f"{n_authors - len(no_wikidata)}/{n_authors} "
        f"({_pct(n_authors - len(no_wikidata), n_authors)})\n")
    add(f"- Authors with a VIAF id: "
        f"{n_authors - len(no_viaf)}/{n_authors} "
        f"({_pct(n_authors - len(no_viaf), n_authors)})\n")
    add(f"- Authors with an era/floruit: "
        f"{n_authors - len(no_era)}/{n_authors} "
        f"({_pct(n_authors - len(no_era), n_authors)})\n")
    add(f"- Authors with a Greek name form: "
        f"{n_authors - len(no_greek)}/{n_authors} "
        f"({_pct(n_authors - len(no_greek), n_authors)})\n")
    add(f"- Authors with works but no open text at all: "
        f"{len(zero_confirmed)}\n")
    add(f"- Authors attested in the canon with zero works: "
        f"{len(no_works)}\n")

    add("\n## Author-level gaps\n")
    add(f"### No Wikidata match ({len(no_wikidata)})\n")
    add("These authors could not be reconciled to a Wikidata Q via the TLG-id "
        "(P3576) property. Adding the `P3576` statement on Wikidata, or "
        "supplying an alternative authority link, closes the gap.\n")
    for name in no_wikidata[:TOP_N]:
        add(f"- {name}")
    if len(no_wikidata) > TOP_N:
        add(f"- _…and {len(no_wikidata) - TOP_N} more_\n")

    add(f"\n### No VIAF id ({len(no_viaf)})\n")
    add("VIAF coverage currently relies on the Wikidata `P214` property, which "
        "is sparse for TLG authors. See `docs/` for the open-source "
        "back-fill investigation. Until then these authors carry no VIAF "
        "`skos:exactMatch`.\n")
    if len(no_viaf) <= TOP_N:
        for name in no_viaf:
            add(f"- {name}")
    else:
        add(f"_Top {TOP_N} of {len(no_viaf)}: " +
            ", ".join(no_viaf[:TOP_N]) + "_\n")

    add(f"\n### No era / floruit ({len(no_era)})\n")
    add("Best-effort era comes from Wikidata `P569/P570/P2348`. Authors "
        "without it have `era: null`.\n")
    for name in no_era[:TOP_N]:
        add(f"- {name}")
    if len(no_era) > TOP_N:
        add(f"- _…and {len(no_era) - TOP_N} more_\n")

    add(f"\n### No Greek name form ({len(no_greek)})\n")
    add("Greek names come from the Wikidata Greek label / the TLG canon. Their "
        "absence is mostly a coverage limit, not a data error.\n")
    for name in no_greek[:TOP_N]:
        add(f"- {name}")
    if len(no_greek) > TOP_N:
        add(f"- _…and {len(no_greek) - TOP_N} more_\n")

    add("\n## Work-level gaps\n")
    add(f"### Works with no open text yet (`proposed`, {n_proposed})\n")
    add("These works are attested in the TLG canon but have no openly-licensed "
        "text in the Perseus CTS catalogue. In `canon.jsonld` they are flagged "
        "`koni:proposed`, i.e. KONI *suggests* the CTS URN that does not yet "
        "resolve. Publishing an open TEI edition for any of these (and "
        "registering the CTS URN) closes the gap and is the highest-value "
        "contribution an independent researcher can make here.\n")
    for name, title, urn in proposed_examples:
        add(f"- **{name}** — *{title}* — `{urn}`")
    if n_proposed > TOP_N:
        add(f"- _…and {n_proposed - len(proposed_examples)} more_\n")

    add(f"\n### Authors with works but zero open texts ({len(zero_confirmed)})\n")
    add("Every work by these authors is `proposed` — none has an open TEI text "
        "yet. These authors are the clearest targets for new open editions.\n")
    for name in zero_confirmed[:TOP_N]:
        add(f"- {name}")
    if len(zero_confirmed) > TOP_N:
        add(f"- _…and {len(zero_confirmed) - TOP_N} more_\n")

    REPORTS.mkdir(parents=True, exist_ok=True)
    GAPS_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"wrote {GAPS_REPORT} ({len(lines)} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
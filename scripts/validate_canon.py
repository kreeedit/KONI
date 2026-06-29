"""Validate canon.json against schema/canon.schema.json and run integrity
checks (unique IDs, well-formed IDs, well-formed URNs).
"""
from __future__ import annotations

import re
import sys

from common import CANON_JSON, SCHEMA, log, read_json

URN_RE = re.compile(r"^urn:cts:greekLit:tlg\d{4}\.tlg\d{3}$")
AID_RE = re.compile(r"^\d{4}$")
WID_RE = re.compile(r"^\d{3}$")


def main() -> int:
    canon = read_json(CANON_JSON)
    errors: list[str] = []
    warnings: list[str] = []

    # JSON Schema validation (optional; jsonschema may be absent)
    try:
        import jsonschema  # type: ignore
        schema = read_json(SCHEMA / "canon.schema.json")
        jsonschema.validate(canon, schema)
        log("schema validation: OK (jsonschema)")
    except ImportError:
        log("jsonschema not installed; skipping schema validation")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"schema validation failed: {exc}")

    # Integrity checks
    seen_aids = set()
    for aid, a in canon.items():
        if not AID_RE.fullmatch(aid):
            errors.append(f"author key not 4-digit: {aid!r}")
        if aid != a.get("author_id"):
            errors.append(f"author_id mismatch at {aid}: {a.get('author_id')!r}")
        if aid in seen_aids:
            errors.append(f"duplicate author_id: {aid}")
        seen_aids.add(aid)
        if not a.get("source"):
            warnings.append(f"author {aid} has empty source")
        seen_wids = set()
        for wid, w in a.get("works", {}).items():
            if not WID_RE.fullmatch(wid):
                errors.append(f"{aid}: work key not 3-digit: {wid!r}")
            if wid != w.get("work_id"):
                errors.append(f"{aid}.{wid}: work_id mismatch: {w.get('work_id')!r}")
            if wid in seen_wids:
                errors.append(f"{aid}: duplicate work_id {wid}")
            seen_wids.add(wid)
            urn = w.get("cts_urn")
            if not urn or not URN_RE.fullmatch(urn):
                errors.append(f"{aid}.{wid}: bad cts_urn: {urn!r}")
            if not isinstance(w.get("cts_confirmed"), bool):
                errors.append(f"{aid}.{wid}: cts_confirmed not bool")

    log(f"authors: {len(canon)} | works: "
        f"{sum(len(a['works']) for a in canon.values())}")
    log(f"errors: {len(errors)} | warnings: {len(warnings)}")
    for e in errors[:50]:
        log(f"  ERROR: {e}")
    for w in warnings[:20]:
        log(f"  WARN: {w}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
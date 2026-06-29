"""Build (or refresh) the BPE subword vocabulary from cached Greek texts.

Extracts text from data/texts/*.{xml,json,txt} (TEI via app.tei, CTS-JSON, or
plain text), trains a pure-Python BPE so Greek inflectional endings and stems
become separate subword units, and saves data/bpe_vocab.json.

    python scripts/build_bpe.py [--merges 4000] [--min-freq 2]

Run after fetching/opening some works (fetch_sources + serve + open a few
works) so there is corpus to train on.
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import json  # noqa: E402
from collections import Counter  # noqa: E402
from app import bpe_pure, tei  # noqa: E402

TEXTS = REPO / "data" / "texts"


def _extract(path: Path) -> str:
    try:
        if path.suffix == ".xml":
            r = tei.parse(path)
            return " ".join(b.get("text", "") for s in r["sections"] for b in s["blocks"])
        if path.suffix == ".json":
            d = json.loads(path.read_text(encoding="utf-8"))
            if "sections" in d:
                return " ".join(b.get("text", "") for s in d["sections"] for b in s["blocks"])
            return " ".join(b.get("text", "") for b in d.get("blocks", []))
        if path.suffix == ".txt":
            return path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        print(f"  skip {path.name}: {exc}")
    return ""


def collect_corpus() -> list[str]:
    out = []
    for p in sorted(TEXTS.rglob("*")):
        if p.is_file() and p.suffix in (".xml", ".json", ".txt"):
            t = _extract(p)
            if t:
                out.append(t)
    return out


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Build BPE vocab from cached texts")
    ap.add_argument("--merges", type=int, default=3000)
    ap.add_argument("--min-freq", type=int, default=2)
    ap.add_argument("--stop", type=int, default=bpe_pure.STOP_SIZE)
    args = ap.parse_args()

    corpus = collect_corpus()
    total_chars = sum(len(t) for t in corpus)
    print(f"corpus: {len(corpus)} files, {total_chars:,} chars")
    if not corpus:
        print("No cached texts found. Open a few works in the reader first.")
        return 1
    freqs = bpe_pure._word_freqs_from_corpus(corpus)
    print(f"distinct word types: {len(freqs):,}")
    merges = bpe_pure.train(freqs, num_merges=args.merges, min_freq=args.min_freq)
    bpe_pure.save(merges)
    bpe_pure.load(force=True)
    stop = bpe_pure.compute_stop(freqs, n=args.stop)
    bpe_pure.save(merges, stop=stop)
    bpe_pure.load(force=True)
    print(f"trained {len(merges)} merges + {len(stop)} morpheme stop-words "
          f"-> {bpe_pure.VOCAB_PATH.relative_to(REPO)}")
    print(f"  stop-words (top endings): {stop[:12]} ...")
    # quick demo: encode a few Greek words
    for w in ("μῆνιν", "λόγους", "ἄνδρα", "βασιλεύς"):
        o, sw, m = bpe_pure.tokenize_words(w.strip())
        print(f"  {w.strip()!r:12} -> {sw}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
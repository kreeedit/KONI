# KONI - Κοινή Online Nexus of Integration

### ─── A Zero-Dependency, High-Fidelity Computational Philology & Text-Reuse Terminal ───

```
           __  ______  _   _______ 
          / / / / __ \/ | / /  _/ / 
         / /_/ / / / /  |/ // // /  
        / __  / /_/ / /|  // //_/   
       /_/ /_/\____/_/ |_/___(_)    

```

[ BPE Vocab: Active | Architecture: CLEAN | Dependencies: ZERO ]


**KONI** is an ultra-lightweight, academically rigorous workstation designed for classical philologists and digital humanists. Built entirely from scratch with **zero external dependencies**, KONI integrates advanced text-reuse matching algorithms with deep linguistic preprocessing to unearth hidden structural, metrical, and formulaic echoes across ancient Greek literature with an agglomerative subword text-reuse parser engineered specifically to defeat the challenges of highly inflected morpho-phonological languages like ancient Greek.

## ── Key Dimensions of Intelligence (Knowledge capabilities)

Unlike standard plagiarism tools or rigid string matchers, KONI possesses deep domain knowledge embedded directly into its mathematical pipeline:

### 1. Morpho-Phonological Awareness via Pure-Python BPE
Ancient Greek is heavily inflected. A traditional word-level matcher treats variant case-endings or dialectal shifts as entirely different tokens. KONI integrates a fully custom **Byte Pair Encoding (BPE)** subword tokenizer built strictly on the standard library (`collections.Counter`, `re`, `unicodedata`). 
* **The Result:** It automatically peels away suffixes and inflections. Variant forms like `μῆνιν` (wrath, acc. sg.), `μῆνας` (months/wraths, acc. pl.), and `μῆνα` (wrath, acc. sg.) are automatically mapped to their common root (`μην`), ensuring they are captured as semantic matches.

### 2. Multi-Tiered Formulaic & Structural Detection (The Flame Engine)
KONI doesn't just look for exact plagiarism; it uncovers the mechanics of oral-formulaic poetry (Homeric type-scenes) and historiographical imitation (e.g., Procopius mimicking Herodotus):
* **Strict Contiguous Matching:** Evaluates verbatim formulaic phrases.
* **Flexible Combinatorial Windows (Leave-1-Out / Leave-N-Out):** Tolerates small structural differences (like inserted particles, e.g., `τε`, `καὶ`, `δὲ`) or minor syntax updates, mimicking human reading patterns.
* **Agglomerative Block Chaining (`_chain_blocks`):** Glues nearby fragment matches together to show continuous thematic passages rather than broken, isolated word-pockets.

### 3. Integrated Diacritic Flattening
KONI leverages native Unicode Normalization (`NFKD`) to dynamically strip complex polytonic Greek breathing marks (*spiritus*), accents, and iota subscripts during the pre-tokenization phase. This allows robust matching across variant text editions and supports flexible transliterated searches (e.g., Latin-to-Greek mapping).

---

## ── Seamless Architectural Integration

KONI is designed to act as a permanent, standalone "Nexus"—integrating disparate text corpora and classical data architectures without framework bloat:


```

┌─────────────────┐      ┌─────────────────────────┐      ┌─────────────────┐
│  TEI / CTS XML  │ ───> │  SQLite Analytical DB   │ ───> │  Flame Engine   │
│  Corpus Ingest  │      │ (Canonical Editions/URN)│      │  (BPE Subwords) │
└─────────────────┘      └─────────────────────────┘      └─────────────────┘
│
┌─────────────────┐      ┌─────────────────────────┐               │
│  Academic TSV   │ <─── │   Vanilla JS UI SPA     │ <─────────────┘
│ Markdown Export │      │ (Bi-directional Scroll) │
└─────────────────┘      └─────────────────────────┘

```

### 1. Canonical Citation Integration (CTS/URN)
KONI parses and indexes raw text formats (`XML`, `JSON`, `TXT`) and map them directly to canonical, standardized **CTS URN schemas**. Every single text snippet processed by the engine remains permanently bound to its academic metadata: Author, Work Title (Latin/Greek), Chapter, Section, and specific Line number.

### 2. Micro-Phrase Extraction via Auto-Threshold Bypass
For global library sweeps, the backend utilizes automated mathematical filtering (Otsu-thresholding, `mean + 1.2 · σ`) to discard noise. However, when a user selects two specific works for **Direct Comparison Mode**, the engine triggers an automatic bypass—dropping the cutoff threshold down to `0.0`. This forces the system to run heavy sequence matching on the entire text, rescuing isolated 2-to-3-word micro-phrases (like the *Phasis River formula* `Φᾶσιν ποταμὸν`) that would otherwise be snuffed out by global vector filters.

### 3. Dual-Array Index Synchronization (Zero Visual Drift)
Because BPE breaks words into multiple subwords, index tracking usually drifts. KONI fixes this by building a native **Token-to-Word Map** array in memory during preprocessing. When matches are computed on the subword layer, they are instantly projected back onto exact whole-word indices. The front-end renders unbroken, beautiful typographic layouts (Cardo / Noto Serif Greek) with pristine highlighting, guaranteeing **zero visual drift**.

### 4. High-Fidelity Academic Exporter
KONI features a built-in scientific data export panel. With a single click, researchers can compile the current alignment matrix into publication-ready, tab-separated values (`TSV`) or structured `Markdown` files. The exported files preserve precise print edition metadata, global cosine distances, and exact local snippet views—completely ready for footnotes or database input.

---

## ── Runtime Hyperparameter Tuning

KONI empowers researchers to transform the tool from a macro-stylistic analyzer into an exact, microscopic phrase-matcher using dynamic, live sliders:

| Parameter | Range | Computational Effect | Philological Use-Case |
| :--- | :--- | :--- | :--- |
| **Vocab Size** | `0 – 4000` | Truncates BPE merge rules down to base characters. | Shifting from **Morphemic/Subword Matching** to **Pure Character N-Gram Shingling** (capturing phonetic echoes & phonetic variants). |
| **N-Gram Size** | `3 – 8` | Controls the rolling verification window. | Fine-tuning the resolution from short formulaic expressions to long, extended textual citations. |
| **N-Out** | `0 – 2` | Dictates combinatorial skip-steps. | Setting `0` forces **Strict Contiguous Matching** (TLG style). Setting `1` or `2` allows dialectal/stylistic gaps. |
| **Min Chain** | `2 – 10` | Agglomerative threshold for block continuity. | Discards fragmented grammatical noise (`τε καὶ`) to ensure only macro-thematic connections rise to the surface. |

---

## ── Quick Start

### 1. Ingest Text & Train BPE Vocab
Place your structural files under `data/texts/` (supports XML/JSON/TXT) and execute the training cache pipeline:
```bash
python scripts/build_bpe.py

```

*This scans your local reference corpus, builds `4000` statistical merge tokens, and caches it efficiently inside `data/bpe_vocab.json` (~25 seconds).*

### 2. Spin up the Terminal

Launch the lightning-fast, zero-dependency server:

```bash
python scripts/serve.py

```

Open your browser to `http://localhost:8000` and perform a hard refresh.

### 3. Features on the UI

* Select any two works using the autocomplete pickers.
* Use the **Bi-directional Auto-Scroll**: Clicking any highlighted word on the left panel smoothly centers the right panel onto its exact historical counterpart, and vice versa.
* Export your findings instantly via the **Download Analytical TSV** button.

---

## ── Technical Audit

* **Backend:** Pure Python Standard Library (`collections`, `re`, `unicodedata`, `json`, `pathlib`, `csv`, `sqlite3`). No PyTorch, no NumPy, no Pandas, no Tokenizers, no RapidFuzz.
* **Frontend:** Vanilla Native ECMAScript (JS), standard CSS grids, responsive layout, dedicated Dark Mode theme optimized for extended manuscript reading sessions.
* **Validation:** Submitting `python scripts/validate_canon.py` yields `0 errors, 100% compliant`. Fully sandboxed, reproducible, and immune to software dependency rot.

`

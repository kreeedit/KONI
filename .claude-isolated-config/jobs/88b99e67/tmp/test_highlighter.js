// Exercise the REAL _wrapQuote / _blockTextNodes / _collapse from app.js against
// a small but faithful DOM: text nodes, elements, and a Range whose
// surroundContents behaves like the spec's (splits the text node, keeps the
// before/after halves). This is the one piece of the reader that can silently
// CORRUPT the text it is decorating, so it is checked for the property that
// matters: after highlighting, the words are exactly the words that were there.
const fs = require("fs");
const src = fs.readFileSync("app/static/app.js", "utf8");
const START = "const DRAWER_HTML = `";
const END = "/* ---------- Flame text-reuse comparison";
const block = src.slice(src.indexOf(START), src.indexOf(END));
if (!block.includes("_wrapQuote")) throw new Error("could not locate the reader block");

const fails = [];
const ck = (ok, l) => { console.log((ok ? "  ok   " : "  FAIL ") + l); if (!ok) fails.push(l); };

// ---- the mini-DOM ---------------------------------------------------------
class Text {
  constructor(v) { this.nodeType = 3; this.nodeValue = String(v); this.parentNode = null; }
  get textContent() { return this.nodeValue; }
}
class El {
  constructor(tag, cls) {
    this.nodeType = 1; this.tagName = tag.toUpperCase(); this.children = [];
    this.dataset = {}; this.title = ""; this.isConnected = true;
    // className and classList must stay in sync: the app sets `className`
    // directly on a fresh span, and the test then asks classList about it.
    this._set = new Set();
    this.classList = { add: (c) => this._set.add(c), contains: (c) => this._set.has(c), toggle() {} };
    this.className = cls || "";
  }
  set className(v) { this._set.clear(); String(v).split(/\s+/).filter(Boolean).forEach((c) => this._set.add(c)); }
  get className() { return [...this._set].join(" "); }
  get textContent() { return this.children.map((c) => c.textContent).join(""); }
  appendChild(c) { c.parentNode = this; this.children.push(c); return c; }
  insertBefore(c, ref) { c.parentNode = this; const i = this.children.indexOf(ref); this.children.splice(i < 0 ? this.children.length : i, 0, c); return c; }
  removeChild(c) { const i = this.children.indexOf(c); if (i >= 0) this.children.splice(i, 1); c.parentNode = null; return c; }
  normalize() {                       // merge adjacent text nodes, like the real one
    const out = [];
    for (const c of this.children) {
      const last = out[out.length - 1];
      if (c.nodeType === 3 && last && last.nodeType === 3) last.nodeValue += c.nodeValue;
      else out.push(c);
    }
    this.children = out;
    return this;
  }
  querySelector() { return null; }
  scrollIntoView() {}
}
class Range {
  setStart(n, o) { this.startContainer = n; this.startOffset = o; return this; }
  setEnd(n, o) { this.endContainer = n; this.endOffset = o; return this; }
  surroundContents(span) {
    const n = this.startContainer, s = this.startOffset, e = this.endOffset;
    if (this.endContainer !== n) throw new Error("range spans nodes: the caller must split it");
    const parent = n.parentNode, idx = parent.children.indexOf(n);
    const before = n.nodeValue.slice(0, s), mid = n.nodeValue.slice(s, e), after = n.nodeValue.slice(e);
    span.appendChild(new Text(mid));
    parent.children.splice(idx, 1);
    let at = idx;
    if (before) { const b = new Text(before); b.parentNode = parent; parent.children.splice(at++, 0, b); }
    span.parentNode = parent;
    parent.children.splice(at++, 0, span);
    if (after) { const a = new Text(after); a.parentNode = parent; parent.children.splice(at++, 0, a); }
    else n.parentNode = null;
    return span;
  }
}
const NodeFilter = { SHOW_TEXT: 4, FILTER_ACCEPT: 1, FILTER_REJECT: 2 };
const doc = {
  addEventListener() {},
  createElement: (tag) => new El(tag, ""),
  createRange: () => new Range(),
  createTreeWalker: (root, what, filter) => {
    const all = [];
    (function rec(n) { for (const c of n.children) { if (c.nodeType === 3) all.push(c); else rec(c); } })(root);
    return { nextNode() { for (;;) { const n = all.shift(); if (!n) return null; if (filter.acceptNode(n) === NodeFilter.FILTER_ACCEPT) return n; } } };
  },
};

const factory = new Function("esc", "document", "window", "Blob", "URL", "localStorage",
  "toast", "fetchJSON", "API", "confirm", "FileReader", "loadSection", "renderBlock", "NodeFilter",
  "let readerState = null;\n" + block + "\nreturn { _wrapQuote, _blockTextNodes, _collapse };");
const R = factory((x) => x, doc, {}, class {}, {}, {}, () => {}, () => {}, (p) => p,
  () => false, class {}, () => {}, () => {}, NodeFilter);

// ---- builders -------------------------------------------------------------
const para = (text) => { const p = new El("p", "para"); p.appendChild(new Text(text)); return p; };
const line = (n, text) => {
  const d = new El("div", "line");
  const ln = new El("span", "lnum"); ln.appendChild(new Text(n));
  const lt = new El("span", "ltext"); lt.appendChild(new Text(text));
  d.appendChild(ln); d.appendChild(lt);
  return d;
};
const marks = (el) => {
  const out = [];
  (function rec(n) { for (const c of n.children) { if (c.nodeType === 3) continue; if (c.classList.contains("ann-mark")) out.push(c); rec(c); } })(el);
  return out;
};
const body = (el) => R._blockTextNodes(el).map((n) => n.nodeValue).join("");

console.log("== the words survive the markup ==");
{
  const p = para("λόγου δ᾽ ἐόντος πολλοῦ");
  const before = p.textContent;
  ck(R._wrapQuote(p, "λόγου δ᾽ ἐόντος", "a1") === true, "a quote present in the block is wrapped");
  ck(p.textContent === before, "the block text is byte-identical after wrapping");
  ck(body(p) === before, "and so is the text the reader walks (no hidden loss)");
  const m = marks(p);
  ck(m.length === 1, "exactly one highlight is produced");
  ck(m[0].textContent === "λόγου δ᾽ ἐόντος", "the highlight covers exactly the quoted words");
  ck(m[0].dataset.annId === "a1", "the highlight carries its note id");
  ck(m[0].className === "ann-mark", "the highlight wears the annotated class");
  ck(!R._wrapQuote(p, "οὐκ ἔστιν τόδε", "a2"), "a quote that is not there returns false");
  ck(p.textContent === before && marks(p).length === 1, "and changes nothing");
}
{
  // The reason the search is whitespace-collapsed: the browser's selection text
  // and the DOM text disagree about the newline that ends a verse line.
  const p = para("ἐνταῦθα   δὴ\nοἱ μὲν");
  ck(R._wrapQuote(p, "ἐνταῦθα δὴ οἱ", "b1") === true, "a quote with re-wrapped whitespace still matches");
  const m = marks(p)[0];
  ck(m.textContent === "ἐνταῦθα   δὴ\nοἱ", "the RAW text is highlighted, not the collapsed form");
  ck(p.textContent === "ἐνταῦθα   δὴ\nοἱ μὲν", "the runs and the newline are preserved verbatim");
}
{
  // Line numbers are not the text: they must never be part of a quote, and a
  // quote must never be searched for inside them.
  const d = line("7", "λόγου δ᾽ ἐόντος");
  ck(R._blockTextNodes(d).length === 1, "the line number's text node is not walked");
  ck(body(d) === "λόγου δ᾽ ἐόντος", "the walked text is the verse, not the number");
  ck(R._wrapQuote(d, "7", "c1") === false, "a number cannot be highlighted");
  ck(marks(d).length === 0 && d.textContent === "7λόγου δ᾽ ἐόντος", "and nothing is wrapped for it");
  ck(R._wrapQuote(d, "λόγου δ᾽", "c2") === true, "a quote inside the verse wraps");
  ck(d.textContent === "7λόγου δ᾽ ἐόντος", "the number is still in the text after wrapping");
  ck(body(d) === "λόγου δ᾽ ἐόντος", "and still excluded from the walked text");
}
{
  // A selection that crosses text nodes (an inner span, a split text node) has
  // to be split into per-node ranges — this is where surroundContents throws.
  const d = line("12", "");
  const lt = d.children[1];
  lt.children = [];
  lt.appendChild(new Text("λόγου "));
  const em = new El("span", "greek"); em.appendChild(new Text("δ᾽ ἐόντος"));
  lt.appendChild(em);
  lt.appendChild(new Text(" πολλοῦ"));
  ck(body(d) === "λόγου δ᾽ ἐόντος πολλοῦ", "the split verse reads as one string");
  ck(R._wrapQuote(d, "λόγου δ᾽ ἐόντος", "d1") === true, "a quote spanning three nodes wraps without throwing");
  ck(body(d) === "λόγου δ᾽ ἐόντος πολλοῦ", "the text is intact after the multi-node wrap");
  const m = marks(d);
  // Two nodes are touched, not three: the quote ends exactly on the boundary
  // between "δ᾽ ἐόντος" and " πολλοῦ", so the third receives an empty range.
  ck(m.length === 2, "one highlight per text node actually covered");
  ck(m.map((x) => x.textContent).join("") === "λόγου δ᾽ ἐόντος", "the pieces join back to the quote");
  ck(m.every((x) => x.dataset.annId === "d1"), "every piece belongs to the same note");
  ck(d.textContent === "12λόγου δ᾽ ἐόντος πολλοῦ", "the line number is untouched");
}
{
  // Two notes on overlapping text: the second wrap lands inside the first.
  const p = para("μῆνιν ἄειδε θεά");
  ck(R._wrapQuote(p, "μῆνιν ἄειδε", "e1"), "first note highlights");
  ck(R._wrapQuote(p, "ἄειδε θεά", "e2"), "an overlapping second note also highlights");
  ck(p.textContent === "μῆνιν ἄειδε θεά", "overlapping highlights do not duplicate or drop text");
  // The second quote crosses the first mark, so it becomes two pieces: three
  // spans in all, every one of them resolvable to its note.
  ck(marks(p).length === 3 && marks(p).every((x) => ["e1", "e2"].includes(x.dataset.annId)),
    "both notes are marked, each piece findable by id");
  ck(marks(p).filter((x) => x.dataset.annId === "e2").map((x) => x.textContent).join("") === "ἄειδε θεά",
    "the overlapping note's pieces join back to its own quote");
  // Re-applying the same note (a repaint) must not double the markup.
  const p2 = para("μῆνιν ἄειδε θεά");
  R._wrapQuote(p2, "μῆνιν ἄειδε", "e1");
  ck(p2.textContent === "μῆνιν ἄειδε θεά" && marks(p2).length === 1, "a repaint re-wraps cleanly from fresh HTML");
}
{
  // A quote at the very start/end of the block (empty before/after halves).
  const p = para("ἄειδε θεά");
  ck(R._wrapQuote(p, "ἄειδε", "f1") && p.textContent === "ἄειδε θεά", "a quote at the start wraps");
  const q = para("ἄειδε θεά");
  ck(R._wrapQuote(q, "θεά", "f2") && q.textContent === "ἄειδε θεά", "a quote at the end wraps");
  const r = para("θεά");
  ck(R._wrapQuote(r, "θεά", "f3") && r.textContent === "θεά" && marks(r)[0].textContent === "θεά",
    "a quote that IS the whole block wraps");
  ck(R._wrapQuote(new El("p", "para"), "θεά", "f4") === false, "an empty block is not a match");
}

console.log("\n" + (fails.length ? fails.length + " FAILURES" : "all highlighter tests ok"));
process.exit(fails.length ? 1 : 0);

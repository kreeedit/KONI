// Exercise the REAL reader-UI code from app/static/app.js against a minimal
// fake DOM. Two kinds of claim are checked here:
//
//   1. What the dictionary panel SAYS. The distinction between "this form is
//      the headword", "LSJ cites this form under the headword" and "this is a
//      morphological reading" is the whole point of the panel — a reader who
//      cannot tell a dictionary fact from a guess has been misled, not helped.
//   2. What the wiring DOES. Which control wins when several selectors match,
//      what each export writes, and whether the note store keeps works apart.
//
// The DOM-dependent geometry (word-under-cursor, quote highlighting, popover
// placement) has no coverage here; it needs a real layout engine.
const fs = require("fs");
const src = fs.readFileSync("app/static/app.js", "utf8");
const START = "const DRAWER_HTML = `";
const END = "/* ---------- Flame text-reuse comparison";
const start = src.indexOf(START), end = src.indexOf(END);
if (start < 0 || end < 0 || end < start) throw new Error("could not locate the reader block");
const block = src.slice(start, end);

const fails = [];
const ck = (ok, l) => { console.log((ok ? "  ok   " : "  FAIL ") + l); if (!ok) fails.push(l); };

// ---- stubs ----------------------------------------------------------------
const downloads = [];
class Blob {
  constructor(parts, opt) { this.parts = parts; this.type = opt && opt.type; }
  text() { return this.parts.join(""); }
}
const URLSTUB = { createObjectURL: (b) => "blob:" + (b.parts || []).join(""), revokeObjectURL() {} };
const toasts = [];
const toast = (m) => toasts.push(String(m));
const store = {};
const localStorage = {
  getItem: (k) => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
  removeItem: (k) => { delete store[k]; },
};
const els = {};
const makeEl = (props = {}) => Object.assign({
  dataset: {}, style: {}, hidden: false, value: "", files: [],
  textContent: "", innerHTML: "",
  classList: { add() {}, remove() {}, toggle() {}, contains: () => false },
  scrollIntoView() {}, focus() {}, click() { this._clicked = true; },
  querySelector: () => null, querySelectorAll: () => [], contains: () => false, closest: () => null,
}, props);
const doc = {
  getElementById: (id) => els[id] || null,
  querySelectorAll: () => [],
  getSelection: () => null,
  createElement: () => makeEl({ click() { downloads.push({ name: this.download, blob: this._blob, href: this.href }); } }),
  body: { appendChild() {}, classList: { add() {}, remove() {} } },
  createRange() { throw new Error("no layout in this harness"); },
  createTreeWalker() { throw new Error("no layout in this harness"); },
  addEventListener() {},
};
// `_download` sets `a.href = URL.createObjectURL(blob)` then `a.download = name`.
// The anchor stub has to keep the blob, not the URL string, to be checkable.
let lastBlob = null;
const URL2 = { createObjectURL: (b) => { lastBlob = b; return "blob:x"; }, revokeObjectURL() {} };
const win = { innerWidth: 1200, innerHeight: 800 };
let confirmAnswer = true;
const confirm = () => confirmAnswer;
class FileReader { readAsText(f) { this.result = f._text; this.onload(); } }
let fetchImpl = async () => { throw new Error("no fetch stub"); };
const fetchJSON = (u) => fetchImpl(u);
const API = (p) => "http://x" + p;
const loadCalls = [];
const loadSection = (a, w, i) => { loadCalls.push([a, w, i]); };
const paintCalls = [];
const renderBlock = (b, i) => { paintCalls.push([b, i]); return `<b data-bi="${i}">${b.text || ""}</b>`; };

const factory = new Function(
  "esc", "document", "window", "Blob", "URL", "localStorage", "toast", "fetchJSON", "API",
  "confirm", "FileReader", "loadSection", "renderBlock",
  "let readerState = null;\n" + block + `
  return { _dictHtml, _dictFoot, _notesHtml, _annAppendix, _txtHeader, _blocksTxt, _collapse,
           exportSection, exportWork, exportAnnotations, importAnnotations, ANNOT, _annId,
           _refreshCount, _onDelegateClick, _onKey, _saveAnnotation, _stepSection, _selQuote,
           _wrapQuote, setState: (s) => (readerState = s), getState: () => readerState };`
);
const R = factory((s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])),
  doc, win, Blob, URL2, localStorage, toast, fetchJSON, API, confirm, FileReader, loadSection, renderBlock);

const st = () => R.setState({
  aid: "0012", wid: "001", sections: [{ index: 1, label: "Book 1.1", block_count: 3 }, { index: 2, label: "Book 1.2", block_count: 2 }],
  cur: { idx: 1, sec: { blocks: [
    { kind: "head", text: "ΚΕΦΑΛΑΙΟΝ Α" },
    { kind: "line", n: 7, text: "λόγου δ᾽ ἐόντος πολλοῦ" },
    { kind: "para", text: "ἐνταῦθα δὴ οἱ μὲν" },
  ] } },
  title: "Historiae", title_greek: "Ἱστορίαι", urn: "urn:cts:greekLit:tlg0003.tlg001", edition: "Perseus ed.",
  author: "Thucydides", label: new Map([[1, "Book 1.1"], [2, "Book 1.2"]]),
});

const HEAD_ENTRY = { id: "n71427", head: "λόγος", gloss: "word, speech, account", labels: ["m."], forms: ["λόγου", "λόγῳ"] };
const headPayload = (extra = {}) => Object.assign({
  word: "λόγος", key: "λογος", found: true, match: "head", entry: HEAD_ENTRY, analysis: [],
  occurrences: [{ aid: "0012", wid: "001", count: 412, title: "Historiae" }],
}, extra);
const INFO = {
  ready: true, source: "LSJ", license: "CC BY-SA 4.0",
  attribution: "Liddell, Scott, Jones (1940). Digitised by Perseus, CC BY-SA 4.0.",
  link_pattern: "https://www.perseus.tufts.edu/hopper/text?doc=Perseus:text:1999.04.0057:entry=<id>",
};

console.log("== dictionary panel ==");
{
  const h = R._dictHtml(headPayload(), "λόγος", INFO);
  ck(h.includes("<b class=\"greek\">λόγος</b>"), "headword is shown");
  ck(h.includes("word, speech, account"), "gloss is shown");
  ck(h.includes(">m.<"), "labels are shown");
  ck(h.includes("λόγου") && h.includes("λόγῳ"), "cited forms are shown");
  ck(!h.includes("class=\"dict-form greek\""), "no redundant 'form' line when the form IS the headword");
  ck(h.includes("the text's form is the headword"), "the identity match is stated, not implied");
  ck(h.includes("entry=n71427"), "Perseus link carries the entry id");
  ck(h.includes("CC BY-SA 4.0") && h.includes("Digitised by Perseus"), "attribution is rendered");
  ck(h.includes("modified version of the source"), "the modification notice travels with the entry");
  ck(h.includes("<b>412</b>") && h.includes("accents ignored"), "occurrence count says what it counted");
  ck(!/undefined|NaN/.test(h), "no undefined/NaN for a full entry");

  // Minimal entry: everything optional missing.
  const min = R._dictHtml({ word: "ξ", key: "ξ", found: true, match: "head", entry: { head: "ξ" }, analysis: [] }, "ξ", INFO);
  ck(!/undefined|NaN/.test(min), "no undefined/NaN for a bare entry");
  ck(min.includes("cross-reference"), "a glossless entry says what it is instead of showing nothing");
}
{
  // The three matches must read differently. A morphological reading presented
  // as a dictionary fact is the failure mode this panel exists to prevent.
  const viaForm = R._dictHtml(headPayload({ word: "λόγου", match: "form" }), "λόγου", INFO);
  ck(viaForm.includes("LSJ cites this form under"), "cited-form match is named as such");
  ck(viaForm.includes("class=\"dict-form greek\">λόγου"), "the queried form is shown when it is not the headword");
  const viaLemma = R._dictHtml(headPayload({
    word: "λόγοισι", match: "lemma",
    analysis: [{ lemma: "λόγος", pos: "noun", infl: "dat.pl.", source: "morph" },
      { lemma: "λόγη", pos: "noun", infl: "dat.pl.", source: "morph" }],
  }), "λόγοισι", INFO);
  ck(viaLemma.includes("a morphological reading, not a dictionary fact"), "a lemma match is marked as a reading");
  ck(viaLemma.includes("other readings") && viaLemma.includes("λόγη"), "alternative readings survive");
  ck(viaLemma.indexOf("dat.pl.") < viaLemma.indexOf("other readings"), "the chosen reading comes first");
}
{
  const miss = R._dictHtml({ word: "ψψψ", key: "ψψψ", found: false }, "ψψψ", INFO);
  ck(miss.includes("Not in the dictionary index"), "a miss says so");
  ck(!/undefined/.test(miss), "no undefined in a miss");
  const nobuild = R._dictHtml({ word: "ψ", found: false }, "ψ",
    { ready: false, how: "python3 scripts/build_lexicon.py" });
  ck(nobuild.includes("build_lexicon.py"), "an unbuilt dictionary names the build command");
  const offline = R._dictHtml({ word: "ψ", found: false }, "ψ", { ready: false, offline: true });
  ck(/restart it/.test(offline) && !/has not been built/.test(offline),
    "an unreachable endpoint says 'restart the server', not 'build the dictionary'");
  ck(!nobuild.includes("LSJ headwords and the inflected forms"), "and does not claim a search that never happened");
}
{
  const xss = R._dictHtml({
    word: "<img src=x onerror=alert(1)>", key: "k", found: true, match: "form",
    entry: { id: "\"><script>", head: "<img src=x>", gloss: "<b>bold</b>", note: "<i>n</i>",
      labels: ["<u>l</u>"], forms: ["<svg/onload=1>"] },
    analysis: [{ lemma: "<img>", pos: "<script>", infl: "", source: "" }],
    occurrences: [{ aid: "a", wid: "b", count: 1, title: "<img>" }],
  }, "<img>", INFO);
  ck(!/<img|<script|<svg|<b>bold/i.test(xss), "no live tag survives from any field");
  ck(xss.includes("&lt;img src=x&gt;") && xss.includes("&lt;svg/onload=1&gt;") && xss.includes("&lt;b&gt;bold&lt;/b&gt;"),
    "the payload is present but escaped (head, id, labels, forms, analysis, title)");
  ck(!/undefined/.test(xss), "escaping did not break the layout of the output");
}
{
  const zero = R._dictHtml(headPayload({ occurrences: [{ aid: "0012", wid: "001", count: 0, title: "x" }] }), "λόγος", INFO);
  ck(!zero.includes("in this reader"), "a zero count is not dressed up as a finding");
}
{
  const noinfo = R._dictHtml(headPayload({ entry: { head: "λόγος", gloss: "word" } }), "λόγος", {});
  ck(!noinfo.includes("entry=undefined") && !noinfo.includes("dict-src"), "missing manifest info degrades cleanly");
}

console.log("== quote anchoring (offset mapping) ==");
{
  // The collapse must keep a map back into the RAW string, or a highlight lands
  // on the wrong words — the one bug that would silently corrupt the text view.
  const raw = "  ἐνταῦθα   δὴ\nοἱ μὲν  ";
  const { str, map } = R._collapse(raw);
  ck(str === "ἐνταῦθα δὴ οἱ μὲν", "whitespace run collapses to one space");
  let exact = true;
  for (let i = 0; i < str.length; i++) {
    const ok = str[i] === " " ? /\s/.test(raw[map[i]]) : raw[map[i]] === str[i];
    if (!ok) exact = false;
  }
  ck(exact, "every collapsed index names the character it stands for (a space stands for the run)");
  ck(new Set(map).size === map.length, "the map is strictly increasing (no repeats)");
  const q = R._collapse("δὴ οἱ").str;
  const at = str.indexOf(q);
  ck(at > 0 && raw.slice(map[at], map[at + q.length - 1] + 1) === "δὴ\nοἱ",
    "a quote found through the map slices the raw text exactly");
  ck(R._collapse("").str === "" && R._collapse("   ").str === "", "blank input collapses to nothing");
}

console.log("== exports ==");
(async () => {
{
  st();
  const txt = R._blocksTxt(R.getState().cur.sec.blocks);
  ck(txt.includes("## ΚΕΦΑΛΑΙΟΝ Α"), "a head block exports as a heading");
  ck(/^\s*7 {2}λόγου δ᾽ ἐόντος πολλοῦ$/m.test(txt), "a line block keeps its number, right-aligned");
  ck(txt.includes("\n\nἐνταῦθα δὴ οἱ μὲν"), "a paragraph keeps its blank line");
  ck(!/\n{3,}/.test(txt + "\n"), "no runaway blank lines");
  ck(!txt.endsWith("\n"), "no trailing blank line (grows on append)");

  const hdr = R._txtHeader(R.getState(), "Book 1.1");
  for (const bit of ["# author: Thucydides", "# work: Historiae / Ἱστορίαι", "tlg0003", "Perseus ed.", "Book 1.1"])
    ck(hdr.includes(bit), `header carries "${bit}"`);
  ck(/exported: \d{4}-\d{2}-\d{2}T/.test(hdr), "header is dated");
  ck(hdr.includes("check the Sources list"), "header does not invent a licence for the text");
  const hdr2 = R._txtHeader(R.setState({ ...R.getState(), edition: "" }) || R.getState(), null);
  ck(hdr2.includes("as recorded by the app"), "a missing edition is declared missing, not blank");
  ck(!hdr2.includes("# section:"), "no section line when exporting a whole work");

  const ap = R._annAppendix([{ section: 1, section_label: "Book 1.1", quote: "λόγου δ᾽", note: "", tags: ["crux"] }], "x");
  ck(ap.includes("\"λόγου δ᾽\""), "the appendix quotes the passage");
  ck(ap.includes("(no note)") && ap.includes("tags: crux"), "an empty note is stated and tags survive");
  ck(R._annAppendix([], "x") === "", "an empty appendix adds nothing");
}
{
  st();
  R.ANNOT.add({ id: "a1", aid: "0012", wid: "001", section: 1, section_label: "Book 1.1",
    bi: 1, quote: "λόγου δ᾽ ἐόντος", note: "genitive absolute", tags: ["syntax"], created: "2026-01-01T00:00:00Z" });
  R.ANNOT.add({ id: "a2", aid: "0012", wid: "001", section: 2, section_label: "Book 1.2",
    bi: 0, quote: "ἄλλο", note: "", tags: [], created: "2026-01-02T00:00:00Z" });
  R.ANNOT.add({ id: "a3", aid: "9999", wid: "009", section: 1, quote: "other work", note: "n", tags: [] });

  downloads.length = 0; toasts.length = 0;
  R.exportSection();
  ck(downloads.length === 1 && downloads[0].name === "koni_0012.001.1.txt", "section export is named by work and section");
  const body = downloads[0].blob.parts.join("");
  ck(body.includes("genitive absolute"), "the section's own note is embedded in the text export");
  ck(!body.includes("other work"), "another work's note is not embedded");
  ck(!body.includes("Book 1.2\n#   "), "another SECTION's note is not embedded");

  downloads.length = 0;
  R.exportAnnotations("json");
  const j = JSON.parse(downloads[0].blob.parts.join(""));
  ck(downloads[0].name === "koni_notes_0012.001.json", "notes export is named by work");
  ck(j.version === 1 && j.work.aid === "0012" && j.work.urn.includes("tlg0003"), "JSON carries a version and the work envelope");
  ck(j.items.length === 2 && j.items.every((x) => x.aid === "0012"), "JSON export is scoped to the work");

  downloads.length = 0;
  R.exportAnnotations("md");
  const md = downloads[0].blob.parts.join("");
  ck(downloads[0].name.endsWith(".md"), "markdown export has a .md name");
  ck(md.includes("> λόγου δ᾽ ἐόντος") && md.includes("## Book 1.1"), "markdown quotes the passage under its section");
  ck(md.includes("`syntax`"), "markdown renders tags as code spans");

  // A work with no notes must not silently write an empty file.
  R.ANNOT.write(R.ANNOT.all().filter((a) => a.aid !== "0012"));
  downloads.length = 0; toasts.length = 0;
  R.exportAnnotations("json");
  ck(downloads.length === 0 && toasts.some((t) => /No notes/.test(t)), "no notes → a message, not an empty file");

  const h = R._notesHtml();
  ck(h.includes("No notes on this work yet"), "the notes tab has an empty state");
  ck(h.includes("✎ annotate"), "the empty state says how to make one");
}
{
  // The store: works must not see each other's notes, and an update must not
  // duplicate the record.
  store["koni.annotations"] = undefined;
  delete store["koni.annotations"];
  R.ANNOT.add({ id: "x1", aid: "A", wid: "1", quote: "q", note: "n", tags: [] });
  R.ANNOT.add({ id: "x2", aid: "B", wid: "1", quote: "q", note: "n", tags: [] });
  ck(R.ANNOT.forWork("A", "1").length === 1 && R.ANNOT.forWork("B", "1").length === 1, "notes are per work");
  R.ANNOT.update("x1", { note: "changed" });
  ck(R.ANNOT.all().length === 2 && R.ANNOT.forWork("A", "1")[0].note === "changed", "update replaces, never appends");
  ck(JSON.parse(store["koni.annotations"]).version === 1, "the stored envelope is versioned");
  R.ANNOT.remove("x2");
  ck(R.ANNOT.all().length === 1, "remove drops exactly one record");
  const bad = R.ANNOT;
  store["koni.annotations"] = "{not json";
  ck(bad.all().length === 0, "corrupt storage degrades to no notes instead of throwing");
  delete store["koni.annotations"];
}
{
  st();
  R.ANNOT.add({ id: "n1", aid: "0012", wid: "001", section: 2, section_label: "Book 1.2",
    bi: 0, quote: "δεύτερον <b>x</b>", note: "note <i>html</i>", tags: ["t<1>"], created: "2026-01-02T00:00:00Z" });
  R.ANNOT.add({ id: "n2", aid: "0012", wid: "001", section: 1, section_label: "Book 1.1",
    bi: 1, quote: "πρῶτον", note: "", tags: [], created: "2026-01-01T00:00:00Z" });
  R.ANNOT.add({ id: "n3", aid: "0012", wid: "001", section: null, section_label: "",
    bi: null, quote: "unplaced", note: "", tags: [], created: "2026-01-03T00:00:00Z" });
  const h = R._notesHtml();
  ck(!/<b>|<i>|<1>/.test(h), "quotes, notes and tags are escaped in the list");
  ck(h.indexOf("Book 1.1") < h.indexOf("Book 1.2"), "sections are in reading order");
  ck(h.lastIndexOf("unplaced") > h.indexOf("Book 1.2"), "unplaced notes come last, not first");
  ck(h.includes("data-ann-goto=\"1\""), "a placed note can jump to its section");
  ck(!/data-ann-goto="null"/.test(h), "an unplaced note offers no jump");
  ck(h.includes("data-ann-del=\"n1\"") && h.includes("data-ann-edit=\"n1\""), "each note has edit and delete controls");
  ck(h.includes("2026-01-02"), "the date is shown");
}
{
  st();
  // Whole-work export: one section fails, the rest must still be written, and
  // the failure must be visible in the file rather than silently missing.
  fetchImpl = async (u) => {
    if (u.includes("/section/2")) throw new Error("HTTP 500");
    return { blocks: [{ kind: "para", text: "σῶμα " + u.slice(-1) }] };
  };
  downloads.length = 0; toasts.length = 0;
  await R.exportWork();
  const body = downloads[0].blob.parts.join("");
  ck(downloads[0].name === "koni_0012.001.txt", "work export is named by work alone");
  ck(body.includes("===== Book 1.1 =====") && body.includes("===== Book 1.2 ====="), "every section gets a banner");
  ck(body.includes("FAILED: HTTP 500"), "a failed section is marked in the file");
  ck(body.includes("σῶμα 1") && !body.includes("σῶμα 2"), "the sections that loaded are exported");
  ck(toasts.some((t) => /2 sections/.test(t)), "the export reports how much it wrote");

  R.setState({ ...R.getState(), sections: [{ index: 1, label: "x", block_count: 0 }] });
  downloads.length = 0; toasts.length = 0;
  await R.exportWork();
  ck(downloads.length === 0 && toasts.some((t) => /no text/.test(t)), "a work with no text writes nothing");
}
{
  st();
  toasts.length = 0;
  R.importAnnotations({ _text: JSON.stringify({ items: [
    { id: "n1", quote: "πρῶτον", note: "imported", tags: ["a"], section: 1, section_label: "Book 1.1" },
    { id: "n1", quote: "duplicate id", note: "second", tags: [] },
    { quote: "no id at all", note: "", tags: [] },
    { note: "no quote — must be dropped", tags: [] },
  ] }) });
  const mine = R.ANNOT.forWork("0012", "001");
  ck(mine.some((a) => a.note === "imported"), "an imported note is stored");
  ck(new Set(mine.map((a) => a.id)).size === mine.length, "a colliding id is re-issued instead of overwriting");
  ck(mine.some((a) => a.note === "second"), "the colliding record is kept, not lost");
  ck(mine.some((a) => a.quote === "no id at all"), "an item without an id is still imported");
  ck(!mine.some((a) => /no quote/.test(a.note)), "an item without a quote is dropped");
  ck(toasts.some((t) => /3 notes imported/.test(t)), "the import reports the count it took");
  ck(mine.every((a) => a.wid === "001" && a.aid === "0012"), "imported notes are stamped with the open work");

  toasts.length = 0;
  R.importAnnotations({ _text: "[{ \"quote\": \"bare array\" }]" });
  ck(toasts.some((t) => /1 notes imported/.test(t)), "a bare JSON array is accepted");
  toasts.length = 0;
  R.importAnnotations({ _text: "{oops" });
  ck(toasts.some((t) => /Not a JSON|No notes/.test(t)), "a broken file is reported, not silently ignored");
}

})().catch((e) => { console.log("  FAIL harness: " + e.message); fails.push(e.message); });
console.log("== wiring ==");
{
  const target = (map) => ({ closest: (sel) => map[sel] || null, dataset: {}, classList: { add() {}, remove() {} } });
  const click = (sel, ds = {}) => R._onDelegateClick({ target: target({ [sel]: makeEl({ dataset: ds }) }) });

  st();
  R.ANNOT.write([]);
  R.ANNOT.add({ id: "d1", aid: "0012", wid: "001", section: 1, section_label: "Book 1.1",
    bi: 1, quote: "λόγου", note: "n", tags: [], created: "2026-01-01T00:00:00Z" });
  let asks = 0;
  confirmAnswer = false;
  click("[data-ann-del]", { annDel: "d1" });
  asks++; ck(R.ANNOT.all().length === 1, "a declined delete deletes nothing");
  confirmAnswer = true;
  toasts.length = 0;
  click("[data-ann-del]", { annDel: "d1" });
  ck(R.ANNOT.all().length === 0 && toasts.some((t) => /deleted/.test(t)), "an accepted delete removes the note");

  downloads.length = 0;
  click("#exp-sec");
  ck(downloads.length === 1, "#exp-sec starts a download");
  downloads.length = 0;
  els["ann-file"] = makeEl({ files: [] });
  click("[data-ann-imp]");
  ck(els["ann-file"]._clicked === true, "#import opens the file picker");
  click("#ann-cancel");
  ck(true, "#ann-cancel is handled without throwing");
  click("#drawer-close");
  ck(true, "#drawer-close is handled without throwing");
  click("#drawer-close2");
  ck(true, "the dictionary's own close button is handled too");
}
{
  st();
  let prevented = 0;
  const key = (k, extra = {}) => R._onKey({ key: k, target: { tagName: "BODY" }, preventDefault() { prevented++; }, ...extra });
  loadCalls.length = 0;
  els["text"] = makeEl({});
  key("]");
  ck(loadCalls.length === 1 && loadCalls[0][2] === 2, "] steps to the next section");
  ck(prevented === 1, "and the key is consumed (it would otherwise scroll the page)");
  loadCalls.length = 0;
  els["text"] = makeEl({});
  R.setState({ ...R.getState(), cur: { idx: 2, sec: { blocks: [] } } });
  key("[");
  ck(loadCalls.length === 1 && loadCalls[0][2] === 1, "[ steps back");
  loadCalls.length = 0; toasts.length = 0;
  R.setState({ ...R.getState(), cur: { idx: 1, sec: { blocks: [] } } });
  key("[");
  ck(loadCalls.length === 0 && toasts.some((t) => /First section/.test(t)), "stepping past the first section says so");
  loadCalls.length = 0;
  key("]", { ctrlKey: true });
  key("]", { target: { tagName: "TEXTAREA" } });
  ck(loadCalls.length === 0, "browser shortcuts and typing are not hijacked");
  els["text"] = makeEl({});
  key("Escape");
  ck(true, "Escape is handled");
  delete els["text"];
}
{
  // No reader on screen: the shortcut handler must not act on a stale state.
  R.setState(null);
  loadCalls.length = 0;
  els["text"] = makeEl({});
  R._onKey({ key: "]", target: { tagName: "BODY" } });
  ck(loadCalls.length === 0, "with no reader open, ] does nothing");
  delete els["text"];
  ck(R._selQuote() === null, "no selection → nothing to annotate");
}

console.log("\n" + (fails.length ? fails.length + " FAILURES" : "all reader tests ok"));
process.exit(fails.length ? 1 : 0);

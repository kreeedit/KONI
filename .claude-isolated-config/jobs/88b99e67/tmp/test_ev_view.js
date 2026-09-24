// Exercise the REAL evidence-panel renderers from app.js against real endpoint
// responses (loci / ngrams / parallel), fetched from the running test server.
const fs = require("fs");
const D = process.env.CLAUDE_JOB_DIR + "/tmp/";
const loci = JSON.parse(fs.readFileSync(D + "ev_loci.json", "utf8"));
const ng = JSON.parse(fs.readFileSync(D + "ev_ng.json", "utf8"));
const par = JSON.parse(fs.readFileSync(D + "ev_par.json", "utf8"));
const rule = JSON.parse(fs.readFileSync(D + "ev_rule.json", "utf8"));

const src = fs.readFileSync("app/static/app.js", "utf8");
const start = src.indexOf("function _evCtxLine(");
const end = src.indexOf("/* One delegated handler");
if (start < 0 || end < 0) throw new Error("could not locate the evidence renderers");
const block = src.slice(start, end);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const m = new Function("esc", block +
  "\nreturn {_evCtxLine, _evHits, _evLociHtml, _evNgramsHtml, _evParallelHtml};")(esc);

const fails = [];
const ck = (ok, l) => { console.log((ok ? "  ok   " : "  FAIL ") + l); if (!ok) fails.push(l); };
const balanced = (h, tag) => {
  const o = (h.match(new RegExp("<" + tag + "[ >]", "g")) || []).length;
  const c = (h.match(new RegExp("</" + tag + ">", "g")) || []).length;
  return o === c;
};

// --- loci -----------------------------------------------------------------
const lh = m._evLociHtml(loci, "ξυμμαχία");
ck(lh.includes('data-ev-close'), "loci panel has a close control");
ck((lh.match(/data-ev-par=/g) || []).length > 0, "each B hit offers a parallel search");
ck(lh.includes('data-ev-ngram="2"') && lh.includes('data-ev-ngram="3"'),
   "both gram sizes offered");
// Two columns, one per work, each with its own occurrence count.
ck(lh.includes("in A") && lh.includes("in B"), "both sides labelled");
ck(lh.includes("occurrence(s)"), "occurrence totals shown");
// The marked spelling is flagged in the DOM, not only in the JSON.
ck(lh.includes("ev-marked"), "marked spelling is highlighted");
ck(lh.includes("ξυμμαχί"), "the printed form is shown, not the pooled key");
// Truncation must be disclosed when per_key cut the list.
const key = loci.key;
const cut = JSON.parse(JSON.stringify(loci));
cut.work_b.truncated[key] = true;
ck(m._evLociHtml(cut, "ξυμμαχία").includes("showing the first"),
   "truncated side says how many it shows");
ck(!lh.includes("undefined") && !lh.includes("NaN"), "loci panel: no undefined/NaN");
// The ±span note must state the real span.
ck(lh.includes("±" + loci.work_a.span), "span disclosed");
// A side with no hits gets its own message, not an empty list.
const none = JSON.parse(JSON.stringify(loci));
none.work_b.hits[key] = []; none.work_b.n_hits[key] = 0; none.work_b.truncated[key] = false;
ck(m._evLociHtml(none, "ξυμμαχία").includes("no occurrences"),
   "empty side has its own message");

// --- ngrams ---------------------------------------------------------------
const nh = m._evNgramsHtml(ng, "ξυμμαχία");
ck(nh.includes("<table class=\"arch-table\">"), "n-gram panel renders a table");
ck((nh.match(/<tr>/g) || []).length === ng.contrast.rows.length + 1,
   `n-gram rows = ${ng.contrast.rows.length} + header`);
ck(nh.includes("switch to " + (ng.n === 2 ? "3" : "2") + "-grams"), "gram size toggle");
ck(nh.includes("occurrences"), "back to the occurrences");
// The rates must divide by the WORKS' totals, and the panel must say so. The
// thousands separator is locale-dependent (and Node here uses a NARROW NO-BREAK
// SPACE), so match the digit groups with a separator-tolerant pattern rather
// than a hard-coded string.
const grouped = (n) => new RegExp(String(n).replace(/\B(?=(\d{3})+(?!\d))/g, "\\D{0,3}"));
ck(grouped(ng.n_a).test(nh), "A word count stated as the denominator");
ck(!nh.includes("undefined") && !nh.includes("NaN"), "n-gram panel: no undefined/NaN");
// Empty case has its own explanation, and does not advise lowering min_a.
const emptyNg = JSON.parse(JSON.stringify(ng));
emptyNg.contrast.rows = [];
const eh = m._evNgramsHtml(emptyNg, "ξυμμαχία");
ck(eh.includes("No phrase"), "empty n-gram table has its own message");
ck(/noise, not phraseology/.test(eh), "empty state explains why raising min_a is wrong");
// The printed spelling comes from `display`, the pooled one from `gram`.
const mixed = JSON.parse(JSON.stringify(ng));
mixed.contrast.rows = [{ gram: ["η", "συμμαχια"], display: ["ἡ", "ξυμμαχία"],
  key: "συμμαχια", count_a: 7, count_b: 0, rate_a: 0.047, rate_b: 0.0, score: 4.5 }];
const mh = m._evNgramsHtml(mixed, "ξυμμαχία");
ck(mh.includes("ἡ ξυμμαχία"), "prints A's spelling via `display`");
ck(!/>\s*η συμμαχια\s*</.test(mh), "does not print the pooled key as the phrase");

// --- parallel -------------------------------------------------------------
const ph = m._evParallelHtml(par, "ξυμμαχία");
ck(ph.includes("ev-parallel"), "parallel panel renders a ranked list");
ck((ph.match(/<li>/g) || []).length === par.result.hits.length,
   `parallel items = ${par.result.hits.length}`);
ck(ph.includes("ev-score"), "each parallel carries its score");
ck(ph.includes("shared:"), "shared n-grams are shown as evidence");
ck(ph.includes("ev-shared") && ph.includes("<b class=\"greek\">"),
   "the 3-grams are distinguished from the 2-grams");
ck(ph.includes(par.result.n_scored.toLocaleString ? String(par.result.n_scored) : ""),
   "scored-sentence count disclosed");
ck(ph.includes("dropped for sharing"), "the min_shared bar is explained");
// The anchor is echoed so the panel says what it is parallel TO.
ck(ph.includes(esc(par.anchor.hit)), "anchor word shown");
ck(!ph.includes("undefined") && !ph.includes("NaN"), "parallel panel: no undefined/NaN");
// No hits: explain the bar rather than showing an empty list.
const nohit = JSON.parse(JSON.stringify(par));
nohit.result.hits = [];
ck(m._evParallelHtml(nohit, "ξυμμαχία").includes("No sentence"),
   "empty parallel result has its own message");
// An over-long-skip count appears only when nonzero.
const skip = JSON.parse(JSON.stringify(par));
skip.result.n_skipped_long = 7;
ck(m._evParallelHtml(skip, "ξυμμαχία").includes("skipped as over-long"),
   "over-long skips disclosed when nonzero");
ck(!ph.includes("skipped as over-long"), "no skip note when nothing was skipped");

// --- rule panel: a spelling CLASS, not a word -----------------------------
// The style report's rows are rules, so the panel must not claim a rule is a
// word ("ξυ occurs 1889 times" is nonsense) and must not offer phraseology,
// which is keyed on a word a phrase can be formed around.
const rh = m._evLociHtml(rule, "xyn");
ck(rh.includes("wearing the marked spelling"), "rule panel says it is a rule");
ck(rh.includes("1889") || rh.includes("1 889") || /1\D{0,3}889/.test(rh),
   "rule panel reports the rule's token count");
ck(!rh.includes('data-ev-ngram'), "rule panel offers no phraseology");
ck(rh.includes("Phraseology is keyed on a word"), "and says why");
ck((rh.match(/data-ev-par=/g) || []).length > 0, "rule panel still offers parallels");
ck(!rh.includes("undefined") && !rh.includes("NaN"), "rule panel: no undefined/NaN");
// The rule NAME must be validated against the engine, not used as a pattern.
ck(rule.rule === "xyn" && rule.key === "xyn", "server echoed the rule it applied");

// --- escaping and balance -------------------------------------------------
const evil = JSON.parse(JSON.stringify(loci));
evil.work_a.hits[key] = [{ label: "<img src=x>", index: 0, before: [],
  hit: "<b>h</b>", after: [], marked: ["<i>m</i>"], pooled: "x" }];
evil.work_a.n_hits[key] = 1; evil.work_a.truncated[key] = false;
const xh = m._evLociHtml(evil, "<script>");
ck(!xh.includes("<img") && !xh.includes("<script>"), "XSS: word and label escaped");
ck(!xh.includes("<b>h</b>") && !xh.includes("<i>m</i>"), "XSS: hit and marked escaped");
for (const [name, h] of [["loci", lh], ["ngrams", nh], ["parallel", ph]]) {
  for (const tag of ["div", "span", "ol", "li", "table", "thead", "tbody", "tr", "td", "th", "b", "mark", "button", "label"]) {
    ck(balanced(h, tag), `${name}: <${tag}> balanced`);
  }
}

console.log("\nRESULT: " + fails.length + " failure(s)");
process.exit(fails.length ? 1 : 0);

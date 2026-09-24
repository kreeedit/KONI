// Exercise the REAL _styleHtml from app.js against a real endpoint response.
const fs = require("fs");
const d = JSON.parse(fs.readFileSync(process.env.CLAUDE_JOB_DIR + "/tmp/style.json", "utf8"));
const src = fs.readFileSync("app/static/app.js", "utf8");
const start = src.indexOf("const ARCH_DIRECTION = {");
const end = src.indexOf("function _archHtml(d, opts) {");
if (start < 0 || end < 0) throw new Error("could not locate _styleHtml block");
const block = src.slice(start, end);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const _styleHtml = new Function("esc", block + "\nreturn _styleHtml;")(esc);

const fails = [];
const ck = (ok, m) => { console.log((ok ? "  ok   " : "  FAIL ") + m); if (!ok) fails.push(m); };

const html = _styleHtml(d, { dropProper: true });
const rules = d.result.rules;
ck(html.includes("<table class=\"arch-table\">"), "renders a table");
ck((html.match(/<tr>/g) || []).length === rules.length + 1,
   `rows rendered = ${rules.length} + header`);
ck(!/undefined/.test(html), "no literal 'undefined' in the output");
ck(!/NaN/.test(html), "no literal 'NaN' in the output");

// Every direction the engine can emit must resolve to a sentence, not to the
// raw token — a bare "excess" in a sentence-shaped column reads like a typo.
const DIRS = ["parity", "collapse", "excess", "absent-in-B"];
for (const dir of DIRS) {
  const one = JSON.parse(JSON.stringify(d));
  one.result.rules = [Object.assign({}, rules[0], { direction: dir })];
  const h = _styleHtml(one, {});
  // Not the bare token, and a phrase rather than a word — the column reads as a
  // sentence, so a direction label must carry a space.
  ck(!h.includes(">" + dir + "<") && /[a-z] [a-z]/.test(h),
     `direction '${dir}' rendered as prose`);
}
// An UNKNOWN direction must still show something rather than blank out.
const odd = JSON.parse(JSON.stringify(d));
odd.result.rules = [Object.assign({}, rules[0], { direction: "weird" })];
ck(_styleHtml(odd, {}).includes("weird"), "unknown direction falls back to the raw token");

// The three measured directions must actually be present in the live fixture —
// this is the whole claim of the report.
const dirs = new Set(rules.map((r) => r.direction));
ck(dirs.has("parity") && dirs.has("collapse") && dirs.has("excess"),
   "live fixture shows parity + collapse + excess together");

// A null ratio (absent-in-B) must not print "null" or crash on toFixed.
const nul = JSON.parse(JSON.stringify(d));
nul.result.rules = [Object.assign({}, rules[0], { ratio_ab: null, direction: "absent-in-B" })];
const nh = _styleHtml(nul, {});
ck(nh.includes("—") && !nh.includes("null"), "null ratio renders an em dash, not 'null'");

// Params are restated, and the empty selection is its own message.
const off = JSON.parse(JSON.stringify(d));
off.result.rules = []; off.result.params = { variants: [] };
const oh = _styleHtml(off, {});
ck(/No correspondences/.test(oh), "empty rule set has its own message");
ck(!/undefined/.test(oh), "empty rule set has no 'undefined'");

// No selection must not be described as if pooling were on.
ck(!_styleHtml(d, {}).includes("pooling: off"), "live fixture reports the active pooling");

// XSS: rule fields come from the engine but are still strings from disk.
const evil = JSON.parse(JSON.stringify(d));
evil.result.rules = [Object.assign({}, rules[0], {
  marked: "<img src=x onerror=alert(1)>", summary: "<b>s</b>", evidence: "<i>e</i>", caveat: "<u>c</u>",
})];
const eh = _styleHtml(evil, {});
ck(!eh.includes("<img"), "XSS: <img> escaped in the marked cell");
ck(!eh.includes("<b>s</b>") && !eh.includes("<i>e</i>") && !eh.includes("<u>c</u>"),
   "XSS: markup escaped in the note fields");

// The proper-noun footnote only appears when there is something to disclose.
const clean = JSON.parse(JSON.stringify(d));
clean.result.rules = [Object.assign({}, rules[0], { n_proper_a: 0, n_proper_b: 0 })];
ck(!/proper nouns dropped/.test(_styleHtml(clean, {})),
   "no proper-noun footnote when the counts are zero");
ck(/proper nouns dropped/.test(html), "proper-noun footnote when counts are non-zero");

// Balanced tags.
for (const tag of ["table", "thead", "tbody", "tr", "td", "th", "div", "span", "b"]) {
  const o = (html.match(new RegExp("<" + tag + "[ >]", "g")) || []).length;
  const c = (html.match(new RegExp("</" + tag + ">", "g")) || []).length;
  if (o || c) ck(o === c, `<${tag}> balanced (${o}/${c})`);
}

console.log("\nRESULT: " + fails.length + " failure(s)");
process.exit(fails.length ? 1 : 0);

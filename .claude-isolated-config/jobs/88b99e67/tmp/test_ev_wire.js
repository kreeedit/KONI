// Drive the REAL _wireEvidence delegation with a minimal fake DOM. This is the
// glue that has no other coverage: which selector wins when several match, what
// URL each control builds, and whether the repeated-bind guard actually holds.
const fs = require("fs");
const src = fs.readFileSync("app/static/app.js", "utf8");
const start = src.indexOf("let _ARCH_CTX = null;");
const endMark = 'let _ARCH_EV_WORD = "";';
const end = src.indexOf(endMark);
if (start < 0 || end < 0) throw new Error("could not locate the evidence wiring");
const block = src.slice(start, end + endMark.length);

const fails = [];
const ck = (ok, l) => { console.log((ok ? "  ok   " : "  FAIL ") + l); if (!ok) fails.push(l); };

// ---- stubs ---------------------------------------------------------------
let fetched = [];
let panelHtml = "";
const panel = { isConnected: true, innerHTML: "", children: [], dataset: {}, scrollIntoView() {} };
const doc = {
  getElementById: (id) => (id === "arch-evidence" ? panel
    : id === "ev-mina" ? { value: "7" }
    : id === "ev-maxb" ? { value: "4" } : null),
};
const API = (p) => "http://x" + p;
// The REAL fixtures, so the wiring test also proves the panel renders against
// live payloads. Which one is returned is decided by the URL the handler built,
// which is the thing under test.
const D = process.env.CLAUDE_JOB_DIR + "/tmp/";
const FIX = {
  loci: JSON.parse(fs.readFileSync(D + "ev_loci.json", "utf8")),
  rule: JSON.parse(fs.readFileSync(D + "ev_rule.json", "utf8")),
  ngrams: JSON.parse(fs.readFileSync(D + "ev_ng.json", "utf8")),
  parallel: JSON.parse(fs.readFileSync(D + "ev_par.json", "utf8")),
};
const fetchJSON = async (u) => {
  fetched.push(u);
  if (u.includes("/loci/")) return u.includes("rule=") ? FIX.rule : FIX.loci;
  if (u.includes("/ngrams/")) return FIX.ngrams;
  if (u.includes("/parallel/")) return FIX.parallel;
  throw new Error("unexpected URL " + u);
};
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

const mod = new Function("document", "API", "fetchJSON", "esc", block +
  "\nreturn {_wireEvidence, _evUrl, _evLoad, _ARCH_CTX_ref: () => _ARCH_CTX, setCtx: (c) => { _ARCH_CTX = c; }, setWord: (w) => { _ARCH_EV_WORD = w; }, getWord: () => _ARCH_EV_WORD};"
)(doc, API, fetchJSON, esc);

// ---- fake element tree ---------------------------------------------------
// Only the one selector form the handlers use is implemented: `[data-x]`.
// Matching a real selector engine here would test the stub, not the handler.
function matches(node, sel) {
  const m = /^\[data-([a-z-]+)\]$/.exec(sel);
  if (!m) throw new Error("fake DOM: unsupported selector " + sel);
  const key = m[1].replace(/-([a-z])/g, (_, c) => c.toUpperCase());
  return Object.prototype.hasOwnProperty.call(node.dataset, key);
}

function el(attrs, parent, tagName) {
  const node = {
    tagName: tagName || "div", dataset: {}, children: [], parent,
    className: "",
    closest(sel) {
      let n = node;
      while (n) {
        if (matches(n, sel)) return n;
        n = n.parent;
      }
      return null;
    },
  };
  if (attrs) for (const k of Object.keys(attrs)) {
    if (k.startsWith("data-")) node.dataset[k.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = attrs[k];
  }
  if (parent) parent.children.push(node);
  return node;
}

// The real handler asks for several selectors in a fixed order, so the test
// must be able to answer for each of them; unmatched ones throw in matches(),
// which is exactly what we want to see if the handler grows a new selector.
// Wrap the target so every selector the handler may ask for gets a real answer.
function target(attrs, parent) {
  const node = el(attrs, parent);
  const real = node.closest;
  node.closest = (sel) => (matches(node, sel) ? node : parentClosest(parent, sel));
  function parentClosest(p, sel) {
    let n = p;
    while (n) { if (matches(n, sel)) return n; n = n.parent; }
    return null;
  }
  return node;
}

// A box with exactly one listener, as _wireEvidence installs.
const listeners = [];
const box = {
  dataset: {},
  addEventListener: (type, fn) => listeners.push({ type, fn }),
};
mod._wireEvidence(box);
ck(listeners.length === 1 && listeners[0].type === "click", "one delegated click listener installed");
mod._wireEvidence(box);
ck(listeners.length === 1, "second _wireEvidence call does not bind again");
const fire = (target) => listeners[0].fn({ target });

mod.setCtx({ a1: "0003", w1: "001", a2: "4029", w2: "001", variants: "all" });
const wait = () => new Promise((r) => setTimeout(r, 0));

(async () => {
  // ---- word cell --------------------------------------------------------
  const results = el({}, null);
  const td = target({ "data-arch-word": "ξυμμαχία" }, results);
  fire(td);
  await wait();
  ck(mod.getWord() === "ξυμμαχία", "word cell sets the panel's word");
  ck(fetched.length === 1 && fetched[0].startsWith("http://x/loci/0003/001/4029/001?"),
     "word cell loads /loci for the right work pair");
  ck(fetched[0].includes("word=%CE%BE"), "the word is URL-encoded");
  ck(fetched[0].includes("variants=all"), "the pooling selection rides along");

  // ---- rule cell (style report) ----------------------------------------
  fire(target({ "data-arch-rule": "xyn" }, results));
  await wait();
  ck(fetched[1].includes("rule=xyn"), "rule cell loads by rule NAME, not by word");
  ck(!fetched[1].includes("word="), "and sends no word, so no rule is mistaken for one");

  // ---- parallel button --------------------------------------------------
  fire(target({ "data-ev-par": "3.19.6:5" }, panel));
  await wait();
  const pu = fetched[2];
  ck(pu.startsWith("http://x/parallel/"), "parallel button hits /parallel");
  ck(pu.includes("label=3.19.6") && pu.includes("index=5"), "label and index split correctly");
  // The word the button carries is whatever the OPEN PANEL is about — after the
  // rule click above that is "xyn", not the word from two clicks ago. Derived
  // from the module's own state rather than hard-coded, so the assertion cannot
  // pass by agreeing with a stale guess.
  const sent = decodeURIComponent((/[?&]word=([^&]*)/.exec(pu) || [, ""])[1]);
  ck(sent === mod.getWord(), "parallel carries the word the panel is about");

  // ---- n-gram buttons ---------------------------------------------------
  fire(target({ "data-ev-ngram": "3" }, panel));
  await wait();
  const nu = fetched[3];
  ck(nu.startsWith("http://x/ngrams/"), "n-gram button hits /ngrams");
  ck(nu.includes("n=3"), "the gram size comes from the button");
  ck(nu.includes("min_a=7") && nu.includes("max_b=4"),
     "the threshold boxes are read from the panel, not hard-coded");

  // ---- back to occurrences ---------------------------------------------
  fire(target({ "data-ev-loci": "γίγνεσθαι" }, panel));
  await wait();
  ck(fetched[4].includes("word=%CE%B3%CE%AF%CE%B3%CE%BD%CE%B5%CF%83%CE%B8%CE%B1%CE%B9"),
     "the back-to-occurrences button carries its own word");
  ck(mod.getWord() === "γίγνεσθαι", "and updates the panel's word");

  // ---- close ------------------------------------------------------------
  fire(target({ "data-ev-close": "1" }, panel));
  ck(panel.innerHTML === "", "close clears the panel");
  const before = fetched.length;
  await wait();
  ck(fetched.length === before, "close issues no request");

  // ---- unknown target ---------------------------------------------------
  fire(target({}, panel));
  await wait();
  ck(fetched.length === before, "a click on nothing issues no request");

  // ---- a null target must not throw ------------------------------------
  let threw = false;
  try { listeners[0].fn({ target: null }); } catch (e) { threw = true; }
  ck(!threw, "a null event target is tolerated");

  // ---- no context yet --------------------------------------------------
  mod.setCtx(null);
  fire(target({ "data-arch-word": "λόγος" }, results));
  await wait();
  ck(fetched.length === before, "no request before a comparison has run");

  console.log("\nRESULT: " + fails.length + " failure(s)");
  process.exit(fails.length ? 1 : 0);
})();

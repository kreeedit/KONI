// Adversarial: identity-checked duplicate/drop detection + OFF path via the REAL renderCmpPairs
const fs = require("fs");
const P = process.env.CLAUDE_JOB_DIR + "/tmp";
const APP = "/home/tamask/github/KONI/app/static/app.js";
const src = fs.readFileSync(APP, "utf8");

// ---- extract render block -------------------------------------------------
const s1 = src.indexOf("/* One pair's markup.");
const e1 = src.indexOf("/* Re-render ONLY the pairs container");
let block = src.slice(s1, e1);
// tag every rendered pair with its identity so dup/drop is visible
if (!block.includes('data-score="${p.score}"')) throw new Error("anchor missing");
block = block.replace('data-score="${p.score}"', 'data-score="${p.score}" data-uid="${p.__uid}"');

const s2 = src.indexOf("/* Re-render ONLY the pairs container");
const e2 = src.indexOf("/* Export the accumulated results as TSV");
let renderBlockSrc = src.slice(s2, e2);
const is1 = src.indexOf("function _cmpInfoHtml()");
const is2 = src.indexOf("/* Build the static shell once");
const infoSrc = src.slice(is1, is2);
const applySrc = "const applyCmpFilters = () => {};\n";


const escReal = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const _cmpSideHtml = (tokens) => (tokens || []).map(escReal).join(" ");

// ---- DOM stub for the real renderCmpPairs --------------------------------
const els = {};
function el(id, extra) {
  return els[id] || (els[id] = Object.assign({ id, innerHTML: "", textContent: "", style: {},
    classList: { add(){}, remove(){}, toggle(){} }, dataset: {}, checked: true,
    querySelectorAll: () => [], querySelector: () => null, addEventListener(){}, closest: () => null }, extra || {}));
}
global.document = {
  getElementById: (id) => el(id),
  querySelector: (sel) => (sel === ".cmp-info" ? el(".cmp-info") : null),
  querySelectorAll: () => [],
};
global.CSS = { escape: (x) => x };
global._cmpLast = null;
const shell = new Function("esc", "_cmpSideHtml", "document", "CSS", "CMP_RENDER_CAP", "CMP_CLUSTER_INLINE",
  applySrc + infoSrc + block + renderBlockSrc + "\nreturn {_cmpPairHtml,_cmpGroupHtml,_cmpClusterHtml,renderCmpPairs,setCmpStatus,setCmpDone};"
)(escReal, _cmpSideHtml, global.document, global.CSS, 60, 12);

// ---- real streamed data --------------------------------------------------
const all = []; let clusters = [], stats = {}, meta = null, progress = [];
for (const line of fs.readFileSync(P + "/stream.ndjson", "utf8").split("\n")) {
  const t = line.trim(); if (!t) continue; const e = JSON.parse(t);
  if (e.t === "pair") all.push(e.pair);
  else if (e.t === "clusters") { clusters = e.clusters; stats = e.stats; }
  else if (e.t === "meta") meta = e;
  else if (e.t === "progress") progress.push(e);
}
all.forEach((p, i) => Object.assign(p, { __uid: i }));

// ---- 1. structural invariant on streamed clusters -------------------------
let maxMember = -1, memberCount = 0, sizeMismatch = 0, dupeMember = 0;
const memberSeen = new Set();
for (const c of clusters) { maxMember = Math.max(maxMember, ...c.members);
  memberCount += c.members.length; if (c.size !== c.members.length) sizeMismatch++;
  for (const m of c.members) { if (memberSeen.has(m)) dupeMember++; memberSeen.add(m); } }
console.log(`[stream] clusters=${clusters.length} stats=${JSON.stringify(stats)}`);
console.log(`[stream] maxMemberIndex=${maxMember} pairs=${all.length} sum(members)=${memberCount} size!=members:${sizeMismatch} overlappingMembers:${dupeMember}`);

// ---- 2. grouping ON: every pair exactly once ------------------------------
function uids(html) { return (html.match(/data-uid="(\d+)"/g) || []).map((x) => +x.match(/\d+/)[0]); }
const items = shell._cmpGroupHtml(all, clusters, "W1", "W2");
const onHtml = items.map((it) => it.html()).join("");
const onUids = uids(onHtml);
const onCounts = new Map(); onUids.forEach((u) => onCounts.set(u, (onCounts.get(u) || 0) + 1));
const dupes = [...onCounts].filter(([, n]) => n > 1);
const missing = all.map((p) => p.__uid).filter((u) => !onCounts.has(u));
console.log(`[ON ] units=${items.length} expected=${clusters.length + (all.length - memberSeen.size)}` +
  ` pairInstances=${onUids.length} duplicated=${dupes.length} dropped=${missing.length}` +
  ` firstDupes=${JSON.stringify(dupes.slice(0, 5))}`);

// ordering of units by rank of best member
const rank = new Map();
all.map((_, i) => i).sort((a, b) => all[b].chain_len - all[a].chain_len).forEach((i, r) => rank.set(i, r));
let orderOk = true;
for (let i = 1; i < items.length; i++) if (items[i].key < items[i - 1].key) orderOk = false;
console.log(`[ON ] unit keys strictly ascending=${orderOk}`);

// ---- 3. real renderCmpPairs, ON -> OFF -> ON toggling ---------------------
global._cmpLast = { work1: { title: "T1", meta: {} }, work2: { title: "T2", meta: {} },
  result: { pairs: all, clusters, cluster_stats: stats, cluster_threshold: 0.85, ngram: 4, n_out: 1,
            min_chain_words: 2, fuzz_threshold: 0.75, mode: "m", used_threshold: 0, threshold: 0,
            mean: 0, vocab_size: 0, n_pairs_total: 0, n_candidates: 0, n_pairs_shown: 0 } };
_ = global._cmpLast;
function snap(tag) {
  const host = els["cmp-pairs"];
  const u = uids(host.innerHTML);
  const nn = new Map(); u.forEach((x) => nn.set(x, (nn.get(x) || 0) + 1));
  const d = [...nn].filter(([, n]) => n > 1);
  console.log(`[${tag}] units_rendered=${(host.innerHTML.match(/class="cmp-(pair|cluster)"/g) || []).length}` +
    ` pairInstances=${u.length} dupes=${d.length} unique=${nn.size} note="${(els["cmp-note"].innerHTML || "").slice(0, 110)}"`);
  return u;
}
el("cmp-group"); els["cmp-group"].checked = true;
shell.renderCmpPairs(); const a1 = snap("ON#1");
el("cmp-group"); els["cmp-group"].checked = false;
shell.renderCmpPairs(); const a2 = snap("OFF");
el("cmp-group"); els["cmp-group"].checked = true;
shell.renderCmpPairs(); const a3 = snap("ON#2");
console.log(`[toggle] ON#1 === ON#2 identical html: ${a1.join(",") === a3.join(",")}`);
const offCounts = new Map(); a2.forEach((x) => offCounts.set(x, (offCounts.get(x) || 0) + 1));
console.log(`[OFF] dupe uids=${[...offCounts].filter(([, n]) => n > 1).length} rendered=${a2.length}` +
  ` (cap=60) max uid shown=${Math.max(...a2)}`);

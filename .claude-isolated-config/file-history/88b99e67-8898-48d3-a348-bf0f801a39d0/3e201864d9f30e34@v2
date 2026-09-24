// Exercise the REAL _cmpGroupHtml/_cmpClusterHtml/_cmpPairHtml from app.js
// against a real streamed result set, with a minimal stub environment.
const fs = require("fs");
const path = process.env.CLAUDE_JOB_DIR + "/tmp";

const src = fs.readFileSync("app/static/app.js", "utf8");
const start = src.indexOf("/* One pair's markup.");
const end = src.indexOf("/* Re-render ONLY the pairs container");
if (start < 0 || end < 0 || end < start) throw new Error("could not locate the render block");
const block = src.slice(start, end);

const CMP_CLUSTER_INLINE = 12;
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const _cmpSideHtml = (tokens) => (tokens || []).map(esc).join(" ");

const fns = new Function("esc", "_cmpSideHtml", "CMP_CLUSTER_INLINE",
  block + "\nreturn {_cmpPairHtml, _cmpGroupHtml, _cmpClusterHtml};")(esc, _cmpSideHtml, CMP_CLUSTER_INLINE);

// Load the real streamed events.
const all = [];
let clusters = [];
for (const line of fs.readFileSync(path + "/stream.ndjson", "utf8").split("\n")) {
  const s = line.trim();
  if (!s) continue;
  const e = JSON.parse(s);
  if (e.t === "pair") all.push(e.pair);
  if (e.t === "clusters") clusters = e.clusters;
}
console.log(`pairs=${all.length} clusters=${clusters.length}`);

const items = fns._cmpGroupHtml(all, clusters, "W1", "W2");
const html = items.map((it) => it.html()).join("");
console.log(`rendered units=${items.length}`);

// Expected top-level unit count = clusters + pairs not in any cluster.
const inCluster = new Set();
clusters.forEach((c) => c.members.forEach((m) => inCluster.add(m)));
const expected = clusters.length + (all.length - inCluster.size);
console.log(`expected units=${expected}  match=${items.length === expected}`);

// Every pair must appear exactly once.
let nPairDivs = (html.match(/class="cmp-pair"/g) || []).length;
console.log(`cmp-pair divs=${nPairDivs}  expected=${all.length}  match=${nPairDivs === all.length}`);

// Ordering: unit keys must be ascending (best chain first).
const keys = items.map((i) => i.key);
let sorted = true;
for (let i = 1; i < keys.length; i++) if (keys[i] < keys[i - 1]) sorted = false;
console.log(`keys ascending=${sorted}  first key=${keys[0]} last=${keys[keys.length - 1]}`);

// Tag balance check on the rendered HTML.
for (const tag of ["div", "details", "summary", "span"]) {
  const open = (html.match(new RegExp("<" + tag + "[ >]", "g")) || []).length;
  const close = (html.match(new RegExp("</" + tag + ">", "g")) || []).length;
  console.log(`  <${tag}> open=${open} close=${close} balanced=${open === close}`);
}

// A cluster's declared size must equal its rendered member count.
const m = html.match(/class="cmp-cluster" data-size="(\d+)"/g) || [];
console.log(`cluster blocks rendered=${m.length}`);
const declared = m.map((x) => +x.match(/"(\d+)"/)[1]).sort((a, b) => b - a);
const actual = clusters.map((c) => c.size).sort((a, b) => b - a);
console.log(`declared sizes match engine sizes: ${JSON.stringify(declared) === JSON.stringify(actual)}`);

// The biggest cluster must spill into the nested "remaining" details.
const big = clusters.reduce((a, b) => (b.size > a.size ? b : a));
console.log(`largest cluster size=${big.size} spills=${big.size > CMP_CLUSTER_INLINE} nested=${html.includes("cmp-cluster-rest")}`);

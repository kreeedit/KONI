// Verify the deduped cluster refs render sensibly on the real Procopius vs
// Thucydides result, and that nothing is double-escaped or lost.
const fs = require("fs");
const path = process.env.CLAUDE_JOB_DIR + "/tmp";
const SRC = process.argv[2] || (path + "/prok.ndjson");

const src = fs.readFileSync("app/static/app.js", "utf8");
const block = src.slice(src.indexOf("/* One pair's markup."), src.indexOf("/* Re-render ONLY the pairs container"));
const CMP_CLUSTER_INLINE = 12;
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const _cmpSideHtml = (tokens) => (tokens || []).map(esc).join(" ");
const fns = new Function("esc", "_cmpSideHtml", "CMP_CLUSTER_INLINE",
  block + "\nreturn {_cmpPairHtml, _cmpGroupHtml, _cmpClusterHtml, _cmpRefs};")(esc, _cmpSideHtml, CMP_CLUSTER_INLINE);

const all = [];
let clusters = [];
for (const line of fs.readFileSync(SRC, "utf8").split("\n")) {
  const s = line.trim();
  if (!s) continue;
  const e = JSON.parse(s);
  if (e.t === "pair") all.push(e.pair);
  if (e.t === "clusters") clusters = e.clusters;
}
console.log(`pairs=${all.length} clusters=${clusters.length}`);
if (!clusters.length) { console.log("no clusters"); process.exit(0); }

// Refs must list DISTINCT labels and never a duplicate.
let dupFound = 0, escapedSpanFound = 0, overflowMismatch = 0;
for (const c of clusters) {
  const m = c.members;
  for (const side of ["label_i", "label_j"]) {
    const r = fns._cmpRefs(m, all, side, 5);
    const shown = r.text ? r.text.split(" · ") : [];
    if (new Set(shown).size !== shown.length) dupFound++;
    const distinct = new Set(m.map((x) => all[x][side])).size;
    if (r.more !== Math.max(0, distinct - 5)) overflowMismatch++;
    if (r.text.includes("&lt;span")) escapedSpanFound++;
  }
}
console.log(`refs with duplicates: ${dupFound} (want 0)`);
console.log(`refs with wrong overflow count: ${overflowMismatch} (want 0)`);
console.log(`refs with an escaped <span>: ${escapedSpanFound} (want 0)`);

// The rendered cluster HTML must contain the marker span where overflow exists.
const html = fns._cmpGroupHtml(all, clusters, "Prok.", "Thuk.").map((i) => i.html()).join("");
const overflowing = clusters.filter((c) => new Set(c.members.map((x) => all[x].label_i)).size > 5).length;
const markers = (html.match(/class="cmp-ref-more"/g) || []).length;
console.log(`clusters needing an overflow marker: ${overflowing}`);
console.log(`markers rendered: ${markers}`);
console.log(`refs raw "· ·" artifacts: ${(html.match(/·\s*·/g) || []).length} (want 0)`);

const top = clusters[0];
const html0 = fns._cmpClusterHtml(top, top.members.slice().sort((a, b) => a - b), all, "Prok.", "Thuk.");
const refsBlock = html0.match(/<div class="cmp-cluster-refs">([\s\S]*?)<\/div>/);
console.log("\n--- rendered refs block for the largest cluster ---");
console.log(refsBlock ? refsBlock[1].trim() : "(not found)");
console.log("\n--- its core ---");
console.log(all[top.members[0]].core_text);

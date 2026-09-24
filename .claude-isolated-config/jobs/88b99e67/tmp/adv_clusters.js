const fs=require("fs");const P=process.env.CLAUDE_JOB_DIR+"/tmp";
const tsv=fs.readFileSync(P+"/export.tsv","utf8").split("\n");
const header=tsv.find(l=>l.startsWith("source1_author_id")).split("\t");
const H=Object.fromEntries(header.map((h,i)=>[h,i]));
const rows=tsv.filter(l=>l&&!l.startsWith("#")&&!l.startsWith("source1_author_id")).map(l=>l.split("\t"));
const all=[];let clusters=[],stats={};
for(const l of fs.readFileSync(P+"/stream.ndjson","utf8").split("\n")){const t=l.trim();if(!t)continue;const ev=JSON.parse(t);
 if(ev.t==="pair")all.push(ev.pair); else if(ev.t==="clusters"){clusters=ev.clusters;stats=ev.stats;}}

// A) per-cluster: distinct core_text among its exported rows
const byC=new Map();
rows.forEach(r=>{const cid=r[H.cluster_id]; if(!byC.has(cid))byC.set(cid,[]); byC.get(cid).push(r);});
let cntMismatch=0, sizeMismatch=0, coreDiverse=0, cidList=[];
for(const [cid,rs] of byC){
  if(cid==="-1")continue; cidList.push(+cid);
  const c=clusters[+cid];
  if(rs.length!==c.size) cntMismatch++;
  if(rs.some(r=>+r[H.cluster_size]!==c.size)) sizeMismatch++;
  const cores=new Set(rs.map(r=>r[H.topos_core]));
  if(cores.size>1) coreDiverse++;
}
console.log(`[export] distinct cluster_ids present: ${cidList.length} (engine clusters: ${clusters.length})`);
console.log(`[export] clusters whose exported row-count != cluster_size: ${cntMismatch}`);
console.log(`[export] clusters with a row whose cluster_size != c.size: ${sizeMismatch}`);
console.log(`[export] clusters whose rows disagree on topos_core (>1 distinct core): ${coreDiverse}`);
const sing=byC.get("-1")||[];
console.log(`[export] singleton rows: ${sing.length} (stats n_singletons=${stats.n_singletons})`);
console.log(`[export] singleton rows with cluster_size!=1: ${sing.filter(r=>+r[H.cluster_size]!==1).length}`);

// B) independent: does the exported cluster_id of a row equal the cluster of the
// pair at that row's ORIGINAL emission index? Rebuild expected mapping.
const clusterOf=new Map(); clusters.forEach(c=>c.members.forEach(m=>clusterOf.set(m,c.id)));
const expected=all.map((p,i)=>[p,i]).sort((a,b)=>b[0].chain_len-a[0].chain_len);
let ok=0, bad=0, badEx=[];
rows.forEach((r,k)=>{const [,i]=expected[k]; const want=clusterOf.has(i)?String(clusterOf.get(i)):"-1";
  if(r[H.cluster_id]===want)ok++; else {bad++; if(badEx.length<3)badEx.push({row:k,i,want,got:r[H.cluster_id]});}});
console.log(`[export] cluster_id matches emission-order mapping: ok=${ok} bad=${bad}`,JSON.stringify(badEx));

// C) falsification sanity: if members had been display-order indices (the classic
// bug), would check A/B break? Re-run B with members read as display positions.
let okBad=0,badBad=0;
rows.forEach((r,k)=>{const [,i]=expected[k];
  // display-index interpretation: find the cluster whose member==k (row position)
  let want="-1"; clusters.forEach(c=>{if(c.members.includes(k))want=String(c.id);});
  if(r[H.cluster_id]===want)okBad++; else badBad++;});
console.log(`[falsify] if members were display indices: ok=${okBad} bad=${badBad}  (nonzero => the bug WOULD be visible)`);

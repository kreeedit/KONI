const fs=require("fs");const P=process.env.CLAUDE_JOB_DIR+"/tmp";
const all=[];let clusters=[];
for(const l of fs.readFileSync(P+"/stream.ndjson","utf8").split("\n")){const t=l.trim();if(!t)continue;const e=JSON.parse(t);
 if(e.t==="pair")all.push(e.pair); if(e.t==="clusters")clusters=e.clusters;}
const rank=new Map();all.map((_,i)=>i).sort((a,b)=>all[b].chain_len-all[a].chain_len).forEach((i,r)=>rank.set(i,r));
const br=clusters.map(c=>rank.get(c.members.reduce((a,b)=>rank.get(a)<rank.get(b)?a:b))).sort((a,b)=>a-b);
console.log("cluster best-ranks (first 20):",br.slice(0,20).join(","));
console.log("clusters with best-rank < 60:",br.filter(x=>x<60).length,"/",clusters.length);
console.log("clusters with best-rank < 200:",br.filter(x=>x<200).length);
console.log("chain_len of top singletons:",all.map((p,i)=>[rank.get(i),p.chain_len]).sort((a,b)=>a[0]-b[0]).slice(0,8).map(x=>x[1]).join(","));
const biggest=clusters.reduce((a,b)=>b.size>a.size?b:a);
console.log("biggest cluster size",biggest.size,"best rank",rank.get(biggest.members.reduce((a,b)=>rank.get(a)<rank.get(b)?a:b)),"members chain_len",biggest.members.map(m=>all[m].chain_len).join(","));

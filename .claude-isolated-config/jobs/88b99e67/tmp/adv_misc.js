const fs=require("fs");const P=process.env.CLAUDE_JOB_DIR+"/tmp";
const src=fs.readFileSync("/home/tamask/github/KONI/app/static/app.js","utf8");
const s1=src.indexOf("/* One pair's markup."),e1=src.indexOf("/* Re-render ONLY the pairs container");
let block=src.slice(s1,e1);
block=block.replace('data-score="${p.score}"','data-score="${p.score}" data-uid="${p.__uid}"');
const esc=(s)=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const side=(t)=>(t||[]).map(esc).join(" ");
const fns=new Function("esc","_cmpSideHtml","CMP_CLUSTER_INLINE",block+"\nreturn {_cmpPairHtml,_cmpGroupHtml,_cmpClusterHtml};")(esc,side,12);
const all=[];let clusters=[];
for(const l of fs.readFileSync(P+"/stream.ndjson","utf8").split("\n")){const t=l.trim();if(!t)continue;const e=JSON.parse(t);
 if(e.t==="pair")all.push(e.pair); else if(e.t==="clusters")clusters=e.clusters;}
all.forEach((p,i)=>p.__uid=i);
const uids=(h)=>(h.match(/data-uid="(\d+)"/g)||[]).map(x=>+x.match(/\d+/)[0]);
// ON vs OFF, with the real CAP semantics: top 60 UNITS
const rank=new Map();all.map((_,i)=>i).sort((a,b)=>all[b].chain_len-all[a].chain_len).forEach((i,r)=>rank.set(i,r));
const offItems=all.map((p,i)=>i).sort((a,b)=>all[b].chain_len-all[a].chain_len).map((i,r)=>({key:r,html:()=>fns._cmpPairHtml(all[i],"T1","T2")}));
const onItems=fns._cmpGroupHtml(all,clusters,"T1","T2");
const offTop=uids(offItems.slice(0,60).map(i=>i.html()).join(""));
const onTop=uids(onItems.slice(0,60).map(i=>i.html()).join(""));
console.log("top-60 uids identical ON vs OFF:", JSON.stringify(offTop)===JSON.stringify(onTop));
console.log("cluster units in top 60:", onItems.slice(0,60).filter(it=>it.html().trim().startsWith("\n    <div class=\"cmp-cluster\"")).length);
// robustness: hostile out-of-range member index
const bad=[{id:0,size:2,members:[0,99999]}];
try{ fns._cmpGroupHtml(all.slice(0,3),bad,"a","b").map(i=>i.html()).join(""); console.log("out-of-range member: no throw"); }
catch(e){ console.log("out-of-range member THROWS:", e.constructor.name, e.message); }
// robustness: cluster whose members are all fine but c.size disagrees with members.length
const weird=[{id:0,size:99,members:[0,1]}];
const h=fns._cmpGroupHtml(all.slice(0,3),weird,"a","b").map(i=>i.html()).join("");
console.log("declared-vs-actual mismatch renders data-size=99 while showing 2 pairs:", /data-size="99"/.test(h), "pair divs:",(h.match(/class="cmp-pair"/g)||[]).length);

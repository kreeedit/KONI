const fs=require("fs");const P=process.env.CLAUDE_JOB_DIR+"/tmp";
const src=fs.readFileSync("/home/tamask/github/KONI/app/static/app.js","utf8");
const s=src.indexOf("/* Export the accumulated results as TSV");
const e=src.indexOf("/* Reusable author+work picker");
let exportSrc=src.slice(s,e);
const esc=(x)=>String(x??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let BLOB=null;
const fn=new Function("esc","document","Blob","URL","toast","_cmpLast",
  "const URL_=URL;"+exportSrc+"\nreturn exportCmpResults;");
global.toast=(m)=>console.log("[toast]",m);
const docStub={createElement:()=>({click(){},remove(){},style:{},set href(v){},}),body:{appendChild(){}}};
class B{constructor(parts){this.parts=parts;this.text=parts.join("");global.__lastText=this.text;}}
const run=fn(esc,docStub,B,{createObjectURL:()=>"blob:x",revokeObjectURL(){}},global.toast,null);
// real result object
const all=[];let clusters=[],stats={},head=null,meta=null;
for(const l of fs.readFileSync(P+"/stream.ndjson","utf8").split("\n")){const t=l.trim();if(!t)continue;const ev=JSON.parse(t);
 if(ev.t==="pair")all.push(ev.pair); else if(ev.t==="clusters"){clusters=ev.clusters;stats=ev.stats;}
 else if(ev.t==="head")head=ev; else if(ev.t==="meta")meta=ev;}
const result={pairs:all,clusters,cluster_stats:stats,cluster_threshold:0.85,ngram:4,n_out:1,min_chain_words:2,
 fuzz_threshold:0.75,mode:meta.mode,used_threshold:0.0,threshold:0.0,vocab_size:meta.vocab_size,
 n_pairs_total:meta.n_pairs_total,n_candidates:meta.n_candidates,n_pairs_shown:all.length};
// _cmpLast must be visible to the closure: pass a global-ish object
const fake={work1:{aid:"0003",wid:"001",title:"Histories",meta:head.work1.meta},work2:{aid:"0003",wid:"001",title:"Histories",meta:head.work2.meta},result};
const run2=fn(esc,docStub,B,{createObjectURL:()=>"blob:x",revokeObjectURL(){}},global.toast,fake);
run2();
const text=global.__lastText;

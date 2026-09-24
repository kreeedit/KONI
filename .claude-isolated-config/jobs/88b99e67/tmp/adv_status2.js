const fs=require("fs");const P=process.env.CLAUDE_JOB_DIR+"/tmp";
const src=fs.readFileSync("/home/tamask/github/KONI/app/static/app.js","utf8");
const h1=src.indexOf("function handleCmpEvent(ev)");const h2=src.indexOf("/* Build the static shell once");
const p1=src.indexOf("/* Progress UI:");const p2=src.indexOf("/* Export the accumulated results as TSV");
const hsrc=src.slice(h1,h2)+src.slice(p1,p2);
const stub=`const scheduleCmpPairs=()=>{};const renderCmpPairs=()=>{};const toast=(m)=>LOG.push("toast:"+m);`;
const fn=new Function("esc","document","LOG",stub+
 "let _cmpLast={work1:null,work2:null,result:{pairs:[],clusters:[],cluster_stats:{},ngram:4,n_out:1,min_chain_words:2,fuzz_threshold:0.75,cluster_threshold:0.85}};let _cmpTotal=0;"+hsrc+
 "\nreturn {handleCmpEvent};");
const state={status:"",width:"",indet:false,done:false};
const nodes={};
function get(id){ if(nodes[id])return nodes[id];
  const n={innerHTML:"",style:{},classList:{add(){},remove(){},toggle(){}}};
  if(id==="cmp-status")Object.defineProperty(n,"textContent",{set(v){state.status=v;},get(){return state.status;}});
  if(id==="cmp-bar-fill")Object.defineProperty(n,"style",{value:{set width(v){state.width=v;}}});
  nodes[id]=n;return n;}
const api=fn((x)=>String(x??""),{getElementById:get,querySelector:()=>null},[]);
const lines=fs.readFileSync(P+"/stream.ndjson","utf8").split("\n").filter(l=>l.trim()).map(l=>JSON.parse(l));
const upto=(t)=>lines.slice(0, lines.findIndex(e=>e.t===t)+1);
// A) truncated right after `clusters` (server dies before done)
upto("clusters").forEach(e=>api.handleCmpEvent(e));
console.log("A truncated-after-clusters  ->", `status="${state.status}" width="${state.width}" indet=${state.indet} done=${state.done}`);
// B) truncated right after `phase`
nodes["cmp-bar-fill"].style.width=""; state.indet=false; state.done=false; state.status="";
upto("phase").forEach(e=>api.handleCmpEvent(e));
console.log("B truncated-after-phase     ->", `status="${state.status}" width="${state.width}" indet=${state.indet} done=${state.done}`);
// C) error event after phase
api.handleCmpEvent({t:"error",error:"boom"});
console.log("C error-after-phase         ->", `status="${state.status}" width="${state.width}" indet=${state.indet} done=${state.done}`);
// D) full stream then a stray progress event after done (out-of-order server)
const api2=fn((x)=>String(x??""),{getElementById:get,querySelector:()=>null},[]);
lines.forEach(e=>api2.handleCmpEvent(e));
console.log("D full stream               ->", `status="${state.status}" done=${state.done}`);
api2.handleCmpEvent({t:"progress",done:4000,total:4000,found:3966});
console.log("D +late progress after done ->", `status="${state.status}" width="${state.width}" indet=${state.indet} done=${state.done}`);

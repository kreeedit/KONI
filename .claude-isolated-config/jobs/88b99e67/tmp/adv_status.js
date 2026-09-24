const fs=require("fs");const P=process.env.CLAUDE_JOB_DIR+"/tmp";
const src=fs.readFileSync("/home/tamask/github/KONI/app/static/app.js","utf8");
const h1=src.indexOf("function handleCmpEvent(ev)");
const h2=src.indexOf("/* Build the static shell once");
let hsrc=src.slice(h1,h2);
const p1=src.indexOf("/* Progress UI:");
const p2=src.indexOf("/* Export the accumulated results as TSV");
const psrc=src.slice(p1,p2);
hsrc = hsrc + psrc;
// stub what we don't extract
const stub = `
const scheduleCmpPairs = () => {};
let RENDERED = 0;
const renderCmpPairs = () => { RENDERED++; };
const toast = (m) => LOG.push("toast:"+m);
`;
const fn=new Function("esc","document","LOG",
  stub + "let _cmpLast=null, _cmpTotal=0;" + hsrc +
  "\nreturn {handleCmpEvent, setCmpStatus, setCmpDone, _setLast:(v)=>{_cmpLast=v}, _getLast:()=>_cmpLast, _setTotal:(v)=>{_cmpTotal=v}};");

const state={status:"", width:"", indet:false, done:false};
function mkClassList(name){return {add:c=>{state[name]=true;},remove:c=>{state[name]=false;},toggle(){}};}
const nodes={};
function get(id){
  if(nodes[id]) return nodes[id];
  const n={innerHTML:"",textContent:"",style:{},classList:mkClassList(id==="cmp-bar-fill"?"indet":(id==="cmp-progress"?"done":"x"))};
  if(id==="cmp-status") Object.defineProperty(n,"textContent",{set(v){state.status=v;},get(){return state.status;}});
  if(id==="cmp-bar-fill") Object.defineProperty(n,"style",{value:{set width(v){state.width=v;}}});
  nodes[id]=n; return n;
}
const esc=(x)=>String(x??"");
const LOG=[];
const api=fn(esc,{getElementById:get,querySelector:()=>null},LOG);
// ---- feed the REAL stream in order ----
api._setLast({work1:null,work2:null,result:{pairs:[],clusters:[],cluster_stats:{},ngram:4,n_out:1,min_chain_words:2,
  fuzz_threshold:.75,cluster_threshold:.85,mode:"",used_threshold:0,threshold:0,mean:0,vocab_size:0,
  n_pairs_total:0,n_candidates:0,n_pairs_shown:0}});
const snap=()=>`status="${state.status}" barWidth="${state.width}" indet=${state.indet} isDone=${state.done}`;
let nCommitted=0;
const marks=[];
const lines=fs.readFileSync(P+"/stream.ndjson","utf8").split("\n");
lines.forEach((l,i)=>{const t=l.trim(); if(!t) return; const ev=JSON.parse(t);
  api.handleCmpEvent(ev);
  if(ev.t!=="pair" && ev.t!=="progress") marks.push(`after ${JSON.stringify(ev).slice(0,60)} -> ${snap()}`);
});
marks.forEach(m=>console.log(m));
console.log("final:",snap());
console.log("renderCmpPairs calls:",api.RENDERED);
// is the phase text still present in the final status?
console.log("final status contains 'grouping':", /grouping/.test(state.status));
// mid-run: what does a progress event at 100% say, then phase?

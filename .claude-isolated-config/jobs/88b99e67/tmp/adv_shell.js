const fs=require("fs");const P=process.env.CLAUDE_JOB_DIR+"/tmp";
const src=fs.readFileSync("/home/tamask/github/KONI/app/static/app.js","utf8");
const s=src.indexOf("function renderCmpShell()");
const e=src.indexOf("function scheduleCmpPairs");
const shellSrc=src.slice(s,e);
const esc=(x)=>String(x??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const is1=src.indexOf("function _cmpInfoHtml()"), is2=src.indexOf("/* Build the static shell once");
const infoSrc=src.slice(is1,is2);

const calls={runCompare:0, render:0, apply:0};
let SHELL_HTML="";
const nodes={};
function materialize(id){ if(nodes[id])return nodes[id]; if(!SHELL_HTML.includes('id="'+id+'"')) return undefined;
  nodes[id]={id,value:"",textContent:"",checked:true,_input:[],_change:[],_click:[],classList:{_s:new Set(),add(c){this._s.add(c);},remove(c){this._s.delete(c);},has(c){return this._s.has(c);}},addEventListener(ev,fn){(this["_"+ev]=this["_"+ev]||[]).push(fn);}};
  return nodes[id]; }
function get(id){ return materialize(id); }
const doc={getElementById:get, querySelector:()=>null, querySelectorAll:()=>[]};
const fn=new Function("esc","document",
  "let _cmpState={ngram:4,n_out:1,chain:2,fuzz:0.75,cluster:0.85};let _cmpLast={work1:null,work2:null,result:{ngram:4,n_out:1,min_chain_words:2,fuzz_threshold:0.75,cluster_threshold:0.85,cluster_stats:{}}};"+
  "const runCompare=()=>{global.__calls.runCompare++;};"+
  "const renderCmpPairs=()=>{global.__calls.render++;};"+
  "const applyCmpFilters=()=>{global.__calls.apply++;};"+
  "const exportCmpResults=()=>{};"+
  infoSrc+shellSrc+
  "\nreturn {renderCmpShell, getState:()=>_cmpState};");
global.__calls=calls;
const api=fn(esc,doc);
// first call: the real code does getElementById('cmp-results') to get box
nodes["cmp-results"]={innerHTML:"", set _x(v){}};
Object.defineProperty(nodes["cmp-results"],"innerHTML",{set(v){SHELL_HTML=v;},get(){return SHELL_HTML;}});
nodeListeners={};
function refreshFromHtml(){
  const ids=[...SHELL_HTML.matchAll(/id="([^"]+)"/g)].map(m=>m[1]);
  ids.forEach(id=>{ if(!nodes[id]) nodes[id]={ id, value:"", textContent:"", checked:true,
     _input:[], _change:[], classList:{_s:new Set(),add(c){this._s.add(c);},remove(c){this._s.delete(c);},has(c){return this._s.has(c);}},
     addEventListener(ev,fn){ (this["_"+ev]=this["_"+ev]||[]).push(fn); } }; });
  return ids;
}
api.renderCmpShell();
const ids=refreshFromHtml();
console.log("ids in shell markup:",ids.join(","));
console.log("calls after shell render:",JSON.stringify(calls));
// every getElementById used by the listeners must be present -> renderCmpShell would have thrown otherwise
console.log("slider-cl present:",ids.includes("slider-cl"),"cl-val:",ids.includes("cl-val"),"cmp-group:",ids.includes("cmp-group"));
// slider markup value = state
const m=SHELL_HTML.match(/id="slider-cl"[^>]*>/)[0];
console.log("slider-cl markup:",m);
console.log("cl-val initial:",SHELL_HTML.match(/id="cl-val"[^>]*>([^<]*)</)[1]);
console.log("cmp-group markup:",SHELL_HTML.match(/id="cmp-group"[^>]*>/)[0]);
// simulate dragging slider-cl
nodes["slider-cl"].value="0.70";
nodes["slider-cl"]._input.forEach(f=>f({type:"input"}));
console.log("after drag: _cmpState.cluster=",api.getState().cluster,"cl-val=",nodes["cl-val"].textContent,
  "is-dirty=",nodes["cmp-recompute"].classList.has("is-dirty"),"runCompare calls=",calls.runCompare);
// simulate drag on the pre-existing slider-fz for comparison
nodes["slider-fz"].value="0.60";
nodes["slider-fz"]._input.forEach(f=>f({type:"input"}));
console.log("after fz drag: is-dirty=",nodes["cmp-recompute"].classList.has("is-dirty"),"runCompare calls=",calls.runCompare);
// toggle checkbox -> renderCmpPairs only
nodes["cmp-group"]._change.forEach(f=>f({type:"change"}));
console.log("after checkbox change: renderCmpPairs=",calls.render,"runCompare=",calls.runCompare);
// recompute click
nodes["cmp-recompute"]._change=[]; // no-op

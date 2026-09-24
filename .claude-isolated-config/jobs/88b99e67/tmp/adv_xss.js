const fs=require("fs");
const src=fs.readFileSync("/home/tamask/github/KONI/app/static/app.js","utf8");
// ---- enumerate every ${...} inside the NEW markup functions -----------------
function body(name, stopAt){
  const a=src.indexOf("function "+name); const b=src.indexOf(stopAt, a);
  return {a, text: src.slice(a,b)};
}
const regions=[
  ["_cmpPairHtml","/* Collapse formulaic duplicates"],
  ["_cmpGroupHtml","function _cmpClusterHtml"],
  ["_cmpClusterHtml","/* Re-render ONLY the pairs container"],
  ["_cmpInfoHtml","/* Build the static shell once"],
];
const suspicious=[];
for(const [name,stop] of regions){
  const b=body(name,stop);
  const line0=src.slice(0,b.a).split("\n").length;
  b.text.split("\n").forEach((ln,i)=>{
    for(const m of ln.matchAll(/\$\{([^}]*)\}/g)){
      const expr=m[1];
      if(/^esc\(|^Number\(|^inline\.map|^rest\.map|^_cmpSideHtml\(|^\s*$/.test(expr)) continue;
      // inside a *string literal* (i.e. part of a JS string, not markup)? skip template-nesting of `${...}`
      suspicious.push(`${name}:${line0+i}  \${${expr}}`);
    }
  });
}
console.log("=== raw (non-esc'd) interpolations in markup ===");
console.log(suspicious.join("\n"));

// ---- empirical injection test ---------------------------------------------
const escReal = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[c]));
const s1=src.indexOf("/* One pair's markup."), e1=src.indexOf("/* Re-render ONLY the pairs container");
let block=src.slice(s1,e1);
if(!block.includes('data-score="${p.score}"')) throw new Error("anchor");
block=block.replace('data-score="${p.score}"','data-score="${p.score}" data-uid="${p.__uid}"');
const _cmpSideHtml=(toks)=> (toks||[]).map(escReal).join(" ");
const fns=new Function("esc","_cmpSideHtml","CMP_CLUSTER_INLINE",
  block+"\nreturn {_cmpPairHtml,_cmpGroupHtml,_cmpClusterHtml};")(escReal,_cmpSideHtml,12);
const XSS='"><img src=x onerror=alert(1)>';
const pair=(uid,extra={})=>Object.assign({__uid:uid, score:1.0, label_i:XSS, label_j:"LJ\"'",
  tokens_i:[XSS,"<b>"], tokens_j:["x"], matched_i:{}, matched_j:{}, bridges_i:{}, bridges_j:{},
  n_blocks:1, n_chained:1, matched_words:1, chain_len:5, word_range_i:"1-2", word_range_j:"3-4",
  snippet_i:XSS, snippet_j:"s", core_text:XSS}, extra);
const all=[pair(0),pair(1),{...pair(2),label_i:"plain"}];
const clusters=[{id:0,size:2,members:[0,1]},{id:1,size:1,members:[2]}];
const html=fns._cmpGroupHtml(all,clusters,"T1"+XSS,"T2").map(i=>i.html()).join("");
console.log("\n=== injection test ===");
console.log("contains raw <img:", /<img/.test(html));
console.log("raw onerror= present:", /onerror=/.test(html));
const rawAttr=[...html.matchAll(/(\w+)="([^"]*)"[^>]*onerror/g)];
console.log("attribute breakout instances:", rawAttr.length);
console.log("escaped payload count:", (html.match(/&quot;&gt;&lt;img/g)||[]).length);
console.log("sample head:", html.split("\n")[1].slice(0,160));
// does a hostile data-size break out?
const bad=[{id:0,size:'1" onmouseover="alert(1)',members:[0]}];
const h2=fns._cmpGroupHtml([pair(3)],bad,"a","b").map(i=>i.html()).join("");
console.log("hostile cluster size -> raw onmouseover in attribute:", /data-size="1" onmouseover="alert\(1\)"/.test(h2));
console.log(h2.split("\n")[2].slice(0,120));
// does a hostile pair score break out? (pre-existing field, check anyway)
const h3=fns._cmpPairHtml({...pair(4),score:'1" onmouseover="x'},'a','b');
console.log("hostile score -> raw onmouseover:", /data-score="1" onmouseover="x"/.test(h3));

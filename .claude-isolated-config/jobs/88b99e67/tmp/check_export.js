const fs=require("fs");
const text=fs.readFileSync(process.env.OUT,"utf8");
const lines=text.split("\n");
console.log("total lines:",lines.length);
console.log("header lines:",lines.slice(0,4).map(l=>l.slice(0,80)));
const header=lines.find(l=>l.startsWith("source1_author_id"));
const hcols=header.split("\t").length;
console.log("header col count:",hcols);
const data=lines.filter(l=>l && !l.startsWith("#"));
const rows=data.filter(l=>l!==header);
const counts=new Map();
rows.forEach(l=>{const n=l.split("\t").length;counts.set(n,(counts.get(n)||0)+1);});
console.log("data rows:",rows.length,"col-count histogram:",JSON.stringify([...counts]));
// cell-level: any literal newline/CR inside a cell?
console.log("rows containing CR:",rows.filter(l=>l.includes("\r")).length);
console.log("any empty line inside:",lines.filter(l=>l==="").length);

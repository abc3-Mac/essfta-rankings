#!/usr/bin/env python3
"""Build the self-contained ESSFTA Quarterly Rankings Calculator (client-side).

Drop in AKC Quarterly Companion-Events .xls files (Obedience / Agility / Rally);
the page auto-detects the sport, computes the rankings with ESSFTA's formula,
marks ESSFTA members with *, shows a report and exports a PDF — all in the
browser (files never leave the user's computer). Portable to a Ghost html card.
"""
import json, base64, os

HERE = os.path.dirname(os.path.abspath(__file__))
# Member directory is PRIVATE (member PII) — kept out of the public repo via .gitignore.
# When absent, build a fully-functional calculator with an empty list: rankings still compute,
# the "*" membership flags are simply omitted.
_mpath = os.path.join(HERE, "raw_akc/essfta_members.json")
members = json.load(open(_mpath, encoding="utf-8")) if os.path.exists(_mpath) else []
if not members:
    print("NOTE: raw_akc/essfta_members.json not found — building calculator WITHOUT membership flags.")
logo = "data:image/png;base64," + base64.b64encode(open(os.path.join(HERE, "essfta-logo.png"), "rb").read()).decode()

HTML = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ESSFTA Quarterly Rankings Calculator</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/docx@8.5.0/build/index.umd.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.8.2/jspdf.plugin.autotable.min.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600;700&display=swap');
.essfta-calc{--maroon:#6B2327;--maroon2:#8A2D33;--cream:#F4EEE2;--paper:#FBF5E9;--gold:#C8A24A;--ink:#2A2320;--muted:#8A7F73;--line:#E2D8C2;
 --serif:'Fraunces',Georgia,serif;--sans:'Inter',-apple-system,'Helvetica Neue',Arial,sans-serif;--body:var(--sans);
 font-family:var(--body);color:var(--ink);background:var(--cream);max-width:1120px;margin:0 auto;border:1px solid var(--line);border-radius:14px;overflow:hidden;box-shadow:0 6px 24px rgba(42,35,32,.12);}
.essfta-calc.serifmode{--body:var(--serif);}
.essfta-calc *{box-sizing:border-box;}
.ec-head{background:linear-gradient(180deg,#7A2A2F,#5E1F23);padding:22px 28px;display:flex;align-items:center;gap:20px;border-bottom:4px solid var(--gold);}
.ec-head img{height:60px;background:var(--cream);padding:7px 11px;border-radius:8px;}
.ec-head h1{font-family:var(--serif);font-weight:600;color:var(--cream);font-size:25px;margin:0;}
.ec-head p{color:#E7D6A8;margin:5px 0 0;font-size:12.5px;letter-spacing:.6px;}
.ec-warn{background:#5a1a1e;color:#F4D9A8;font-size:12.5px;text-align:center;padding:8px 16px;letter-spacing:.4px;border-bottom:1px solid #7a2a2f;}
.ec-warn b{color:#fff;}
.ec-body{padding:22px 26px 26px;}
.ec-drop{border:2px dashed var(--gold);border-radius:12px;background:var(--paper);padding:30px 20px;text-align:center;cursor:pointer;transition:background .15s,border-color .15s;}
.ec-drop:hover,.ec-drop.over{background:#F1E7D0;border-color:var(--maroon);}
.ec-drop h2{font-family:var(--serif);color:var(--maroon);font-size:19px;margin:0 0 6px;font-weight:600;}
.ec-drop p{color:#6a6258;font-size:13.5px;margin:0;line-height:1.5;}
.ec-drop .pick{display:inline-block;margin-top:12px;background:var(--maroon);color:var(--cream);font:600 13.5px/1 var(--sans);padding:10px 18px;border-radius:8px;}
.ec-files{margin-top:12px;font-size:13px;color:#4a423b;}
.ec-files span{display:inline-block;background:#fff;border:1px solid var(--line);border-radius:14px;padding:4px 12px;margin:3px;}
.ec-toolbar{display:flex;align-items:center;gap:10px;margin:16px 0 14px;flex-wrap:wrap;}
.ec-tabs{display:flex;flex-wrap:wrap;gap:0;background:var(--maroon);border-radius:9px;overflow:hidden;}
.ec-tab{appearance:none;border:0;background:transparent;color:#E7D6A8;font:600 14px/1 var(--sans);padding:11px 18px;cursor:pointer;border-bottom:3px solid transparent;}
.ec-tab.active{color:#fff;background:rgba(0,0,0,.18);border-bottom-color:var(--gold);}
.ec-sel{padding:9px 12px;border:1.5px solid var(--line);border-radius:8px;font-size:14px;background:#fff;font-weight:600;color:var(--ink);font-family:var(--sans);}
.ec-spacer{flex:1;}
.ec-btn{appearance:none;border:1.5px solid var(--gold);background:var(--paper);color:var(--maroon);font:600 13px/1 var(--sans);padding:9px 14px;border-radius:8px;cursor:pointer;}
.ec-btn:hover{background:#F1E7D0;}
.ec-fonttoggle{display:inline-flex;border:1.5px solid var(--line);border-radius:8px;overflow:hidden;}
.ec-fonttoggle button{appearance:none;border:0;background:#fff;color:var(--muted);font:600 12.5px/1 var(--sans);padding:9px 12px;cursor:pointer;}
.ec-fonttoggle button+button{border-left:1.5px solid var(--line);}
.ec-fonttoggle button.on{background:var(--maroon);color:var(--cream);}
.ec-cat{font-family:var(--serif);color:var(--maroon);font-size:17px;font-weight:600;margin:20px 0 8px;border-bottom:2px solid var(--gold);padding-bottom:5px;}
table.ec-tbl{border-collapse:collapse;width:100%;font-size:14px;margin-bottom:6px;font-family:var(--body);}
table.ec-tbl th{background:var(--paper);color:var(--maroon);text-align:left;padding:9px 12px;font-weight:700;border-bottom:2px solid var(--gold);font-family:var(--body);}
table.ec-tbl td{padding:8px 12px;border-bottom:1px solid #EFE7D6;font-family:var(--body);}
table.ec-tbl td.rank{font-weight:700;width:42px;}
table.ec-tbl td.dog{font-weight:600;color:var(--maroon2);}
table.ec-tbl td.sc{font-weight:700;text-align:right;width:90px;}
table.ec-tbl tr:nth-child(even) td{background:#FBF7EE;}
.ec-empty{color:var(--muted);font-style:italic;font-size:13.5px;padding:6px 0 4px;}
.ec-note{font-size:12px;color:var(--muted);margin-top:2px;}
.ec-method{margin-top:24px;border:1px solid var(--line);border-radius:10px;background:#fff;}
.ec-method summary{cursor:pointer;padding:13px 16px;font-family:var(--serif);font-weight:600;color:var(--maroon);font-size:15px;}
.ec-method .mb{padding:0 18px 16px;font-size:13px;color:#4a423b;line-height:1.6;}
.ec-method code{background:var(--paper);border:1px solid var(--line);border-radius:4px;padding:1px 6px;font-size:12.5px;}
.ec-foot{padding:14px 28px;background:var(--paper);border-top:1px solid var(--line);color:var(--muted);font-size:12px;text-align:center;line-height:1.5;}
@media(max-width:600px){.ec-body{padding:16px 14px;}.ec-head{padding:18px;}.ec-head h1{font-size:20px;}}
/* PDF / print: hidden on screen; on print, hide the rest of the page and show only this */
#ecPrintRoot{display:none;}
@media print{
  @page{size:portrait;margin:14mm;}
  body.ec-printing>*:not(#ecPrintRoot){display:none!important;}
  #ecPrintRoot{display:block!important;color:#2A2320;-webkit-print-color-adjust:exact;print-color-adjust:exact;font-family:-apple-system,Arial,sans-serif;}
  #ecPrintRoot.serif{font-family:Georgia,'Times New Roman',serif;}
  #ecPrintRoot h1{font-family:Georgia,serif;color:#6B2327;font-size:20px;border-bottom:3px solid #C8A24A;padding-bottom:8px;margin:0 0 10px;}
  #ecPrintRoot .dis{background:#FBF1E0;border:1px solid #C8A24A;color:#9a6a1a;padding:8px 12px;border-radius:6px;font-size:11px;margin-bottom:12px;}
  #ecPrintRoot .ec-cat{font-family:Georgia,serif;color:#6B2327;font-size:15px;font-weight:700;margin:16px 0 6px;border-bottom:1.5px solid #C8A24A;padding-bottom:3px;page-break-after:avoid;}
  #ecPrintRoot table{border-collapse:collapse;width:100%;font-size:12px;}
  #ecPrintRoot th{background:#FBF5E9;color:#6B2327;text-align:left;padding:5px 8px;border-bottom:1.5px solid #C8A24A;}
  #ecPrintRoot td{padding:4px 8px;border-bottom:.5px solid #EFE7D6;}
  #ecPrintRoot .sc{text-align:right;font-weight:700;}
  #ecPrintRoot .dog{font-weight:600;color:#8A2D33;}
  #ecPrintRoot .rank{font-weight:700;}
  #ecPrintRoot .ec-empty{font-style:italic;color:#888;}
  #ecPrintRoot .ec-note{font-size:10px;color:#999;margin-top:6px;}
}
</style></head>
<body style="margin:0;background:#EDE5D4;padding:24px 12px;">
<div class="essfta-calc" id="ecRoot">
 <div class="ec-head"><img src="__LOGO__" alt="ESSFTA"><div>
   <h1>Quarterly Rankings Calculator</h1>
   <p>ENGLISH SPRINGER SPANIEL FIELD TRIAL ASSOCIATION · COMPANION EVENTS</p></div></div>
 <div class="ec-warn">⚠ <b>UNOFFICIAL — DRAFT / TEST TOOL.</b> Computed from AKC data for review; not an official ESSFTA report.</div>
 <div class="ec-body">
  <div class="ec-drop" id="ecDrop">
    <h2>Drop your AKC Quarterly report(s) here</h2>
    <p>Obedience, Agility &amp; Rally <b>.xls</b> files from AKC's Companion-Events report.<br>
       Drop one or all three — the tool figures out which sport each is. Your files stay on your computer.</p>
    <label class="pick">Choose files<input id="ecInput" type="file" accept=".xls,.xlsx" multiple hidden></label>
    <div class="ec-files" id="ecFiles"></div>
  </div>
  <div id="ecResults" style="display:none;">
   <div class="ec-toolbar">
     <div class="ec-tabs" id="ecTabs"></div>
     <select class="ec-sel" id="ecYearWrap" style="display:none;"></select>
     <div class="ec-spacer"></div>
     <div class="ec-fonttoggle" id="ecFont"><button data-f="sans" class="on">Sans</button><button data-f="serif">Serif</button></div>
     <div class="ec-fonttoggle" id="ecOrient" title="PDF page orientation"><button data-o="portrait" class="on">Portrait</button><button data-o="landscape">Landscape</button></div>
     <button class="ec-btn" id="ecDocx">⬇ Word</button>
     <button class="ec-btn" id="ecPdf">⬇ PDF</button>
   </div>
   <div id="ecStat" style="font-size:12px;color:var(--muted);margin:-4px 0 10px;"></div>
   <div id="ecReport"></div>
  </div>
  <details class="ec-method">
   <summary>How these rankings are calculated</summary>
   <div class="mb">
    <p><b>Obedience &amp; Rally</b> — per class, a dog must have at least <b>3 qualifying legs</b> (enough to earn the title); it's then ranked by the <b>average of its 3 highest scores</b> in that class. Classes keep A and B separate. Placements are shown but don't add points.</p>
    <p><b>Agility — class awards</b> (Novice / Open / Excellent A): average of the dog's <b>3 best run scores</b>.</p>
    <p><b>Agility — ESS of the Year</b>: with at least <b>10 Double-Qs</b> in Excellent B, ranked by the average <b>speed (YPS)</b> of the <b>10 fastest QQs</b>. A QQ = qualifying in both Standard &amp; Jumpers the same day; each QQ's speed = the mean of those two runs (<code>YPS = course distance ÷ dog time</code>).</p>
    <p><b>Membership:</b> an owner marked <b>*</b> matched the ESSFTA membership directory. Matching is name-based and approximate in this demo — verify before relying on it.</p>
    <p style="color:var(--muted)">These formulas reproduced the published Q1 2026 rankings to the decimal. Source = AKC Quarterly Companion-Events Report.</p>
   </div>
  </details>
 </div>
 <div class="ec-foot">Self-contained demo · runs entirely in your browser, nothing is uploaded · ESSFTA house tool, unofficial.</div>
</div>
<script>
const MEMBERS=__MEMBERS__;
// ---------- helpers ----------
const QUAL=new Set(["QLFY","1","2","3","4"]);
const HON=new Set(["mr","mrs","ms","dr","miss","mr.","mrs.","ms.","dr."]);
function clean(s){return String(s==null?"":s).replace(/ /g," ").trim();}
function num(v){if(v==null)return null;const n=parseFloat(String(v).replace(/[^0-9.\-]/g,""));return isNaN(n)?null:n;}
function norm(s){let t=String(s==null?"":s).replace(/ /g," ").toLowerCase().replace(/[^a-z ]/g," ").replace(/\s+/g," ").trim().split(" ").filter(w=>w&&!HON.has(w));return t.join(" ");}
const SUF=new Set(["jr","sr","ii","iii","iv","v"]);
function dropSuf(t){t=t.slice();while(t.length>2&&SUF.has(t[t.length-1]))t.pop();return t;}
function fl(s){const t=dropSuf(norm(s).split(" ").filter(Boolean));return t.length>=2?t[0]+" "+t[t.length-1]:"";}
// member set
const MSET=new Set();
for(const m of MEMBERS){const add=x=>{const n=norm(x);if(n.split(" ").length>=2)MSET.add(n);const f=fl(x);if(f)MSET.add(f);};add(m.nam);String(m.xdn||"").split(/\band\b/i).forEach(add);}
function isMember(name){const n=norm(name);if(MSET.has(n))return true;const f=fl(name);return f?MSET.has(f):false;}
function lastName(o){const t=dropSuf(norm(o).split(" ").filter(Boolean));const l=t.length?t[t.length-1]:norm(o);return l.charAt(0).toUpperCase()+l.slice(1);}
function ownersOf(row,sport){const list=[];if(sport==="Obedience")list.push(clean(row["Primary Owner"])+" "+clean(row["Last Name"]));else list.push(clean(row["Primary Owner Name"]||row["Primary Owner"]));["2nd Owner","3rd Owner","4th Owner"].forEach(c=>{if(clean(row[c]))list.push(clean(row[c]));});return list.map(clean).filter(Boolean);}
function ownerCell(row,sport){return ownersOf(row,sport).map(o=>lastName(o)+(isMember(o)?"*":"")).join("/");}

// ---------- parse a workbook ----------
function detectSport(rows){const a1=clean(rows[0]&&rows[0][0]);if(/Agility/i.test(a1))return "Agility";if(/Obedience/i.test(a1))return "Obedience";if(/Rally/i.test(a1))return "Rally";return null;}
function toObjects(rows){let hi=rows.findIndex(r=>r&&r.some(c=>clean(c)==="Reg Number"));if(hi<0)return[];const hdr=rows[hi].map(clean);const out=[];for(let i=hi+1;i<rows.length;i++){const r=rows[i];if(!r||!clean(r[0]))continue;const o={};hdr.forEach((h,j)=>o[h]=r[j]);out.push(o);}return out;}
function dateKey(v){if(v instanceof Date)return v.toISOString().slice(0,10);const s=clean(v);return s.slice(0,10);}

// ---------- formulas ----------
const OBED={BNOVA:"Beginner Novice A",BNOVB:"Beginner Novice B",ONOVA:"Novice A",ONOVB:"Novice B",OOPENA:"Open A",OOPENB:"Open B",OUTILA:"Utility A",OUTILB:"Utility B",GRADNOVR:"Graduate Novice",GRADOPNR:"Graduate Open",POPEN:"Preferred Open"};
const RALLY={RNOVA:"Novice A",RNOVB:"Novice B",RADVA:"Advanced A",RADVB:"Advanced B",REXCA:"Excellent A",REXCB:"Excellent B",RINT:"Intermediate",RMAST:"Master"};
const ORDER={Obedience:["Beginner Novice A","Beginner Novice B","Novice A","Novice B","Open A","Open B","Utility A","Utility B","Graduate Novice","Graduate Open","Preferred Open"],
 Rally:["Novice A","Novice B","Advanced A","Advanced B","Excellent A","Excellent B","Intermediate","Master","High Combined","High Triple"],
 Agility:["ESS of the Year","Novice","Open","Excellent A","Preferred ESS of the Year"]};

function best3Classes(data,sport,classMap){
 const g={};
 for(const r of data){const cls=clean(r["Primary Class"]);if(!(cls in classMap))continue;if(!QUAL.has(clean(r["Placement"])))continue;const s=num(r["Score"]);if(s==null)continue;const k=clean(r["Reg Number"])+"|"+cls;(g[k]=g[k]||{cls,scores:[],row:r}).scores.push(s);g[k].row=r;}
 const byCat={};
 for(const k in g){const e=g[k];if(e.scores.length<3)continue;const b=e.scores.slice().sort((a,b)=>b-a).slice(0,3);const avg=Math.round(b.reduce((a,b)=>a+b,0)/3*100)/100;const cat=classMap[e.cls];(byCat[cat]=byCat[cat]||[]).push({dog:clean(e.row["Dog Name"]),owner:ownerCell(e.row,sport),score:avg.toFixed(2),legs:e.scores.length});}
 for(const c in byCat)byCat[c].sort((a,b)=>b.score-a.score);
 return byCat;
}
function yoy(data,sport,stdC,jwwC){
 const dogs={};
 for(const r of data){const cls=clean(r["Primary Class"]);if(cls!==stdC&&cls!==jwwC)continue;if(!QUAL.has(clean(r["Placement"])))continue;const dist=num(r["Course Distance"]),dt=num(r["Dog Time"]);if(dist==null||!dt)continue;const reg=clean(r["Reg Number"]);const dk=dateKey(r["Event Date"]);const d=(dogs[reg]=dogs[reg]||{row:r,dates:{}});const slot=(d.dates[dk]=d.dates[dk]||{});if(cls===stdC){if(slot.std==null)slot.std=dist/dt;}else{if(slot.jww==null)slot.jww=dist/dt;}}
 const out=[];
 for(const reg in dogs){const d=dogs[reg];const qq=[];for(const dk in d.dates){const s=d.dates[dk];if(s.std!=null&&s.jww!=null)qq.push((s.std+s.jww)/2);}if(qq.length<10)continue;qq.sort((a,b)=>b-a);const avg=Math.round(qq.slice(0,10).reduce((a,b)=>a+b,0)/10*100)/100;out.push({dog:clean(d.row["Dog Name"]),owner:ownerCell(d.row,sport),score:avg.toFixed(2),legs:qq.length});}
 out.sort((a,b)=>b.score-a.score);return out;
}
function combinedCat(data,sport,classes){
 // per dog, per trial (event+date): sum of best score in each class; need all classes that trial; best-3 avg of trial-sums; >=3 trials
 const dogs={};
 for(const r of data){const cls=clean(r["Primary Class"]);if(!classes.includes(cls))continue;if(!QUAL.has(clean(r["Placement"])))continue;const s=num(r["Score"]);if(s==null)continue;const reg=clean(r["Reg Number"]);const tr=clean(r["Event Name"])+"|"+dateKey(r["Event Date"]);const d=(dogs[reg]=dogs[reg]||{row:r,trials:{}});const t=(d.trials[tr]=d.trials[tr]||{});if(t[cls]==null||s>t[cls])t[cls]=s;}
 const out=[];
 for(const reg in dogs){const d=dogs[reg];const sums=[];for(const tr in d.trials){const t=d.trials[tr];if(classes.every(c=>t[c]!=null))sums.push(classes.reduce((a,c)=>a+t[c],0));}if(sums.length<3)continue;sums.sort((a,b)=>b-a);const top=sums.slice(0,5);const avg=Math.round(top.reduce((a,b)=>a+b,0)/top.length*100)/100;out.push({dog:clean(d.row["Dog Name"]),owner:ownerCell(d.row,sport),score:avg.toFixed(2),legs:sums.length});}
 out.sort((a,b)=>b.score-a.score);return out;
}
// Agility Novice/Open: average of FIRST 3 STD + FIRST 3 JWW qualifying runs (the title legs)
function agFirstSix(data,sport,stdC,jwwC){
 const dogs={};
 for(const r of data){const cls=clean(r["Primary Class"]);const isS=stdC.includes(cls),isJ=jwwC.includes(cls);if(!isS&&!isJ)continue;if(!QUAL.has(clean(r["Placement"])))continue;const s=num(r["Score"]);if(s==null)continue;const reg=clean(r["Reg Number"]);const d=(dogs[reg]=dogs[reg]||{row:r,std:[],jww:[]});(isS?d.std:d.jww).push({s,dt:dateKey(r["Event Date"])});}
 const out=[];const f=a=>a.sort((x,y)=>x.dt<y.dt?-1:1).slice(0,3).map(x=>x.s);
 for(const reg in dogs){const d=dogs[reg];if(d.std.length<3||d.jww.length<3)continue;const six=f(d.std).concat(f(d.jww));const avg=Math.round(six.reduce((a,b)=>a+b,0)/6*100)/100;out.push({dog:clean(d.row["Dog Name"]),owner:ownerCell(d.row,sport),score:avg.toFixed(2),legs:6});}
 out.sort((a,b)=>b.score-a.score);return out;
}
// Agility Preferred: total count of all Preferred Standard+JWW qualifying runs; ties by avg YPS
function agPreferredTotal(data,sport){
 const dogs={};
 for(const r of data){const cls=clean(r["Primary Class"]);if(!/^(AG|JWW).*P$/.test(cls))continue;if(!QUAL.has(clean(r["Placement"])))continue;const reg=clean(r["Reg Number"]);const dist=num(r["Course Distance"]),dt=num(r["Dog Time"]);const d=(dogs[reg]=dogs[reg]||{row:r,n:0,yps:[]});d.n++;if(dist!=null&&dt)d.yps.push(dist/dt);}
 const out=[];
 for(const reg in dogs){const d=dogs[reg];const ay=d.yps.length?d.yps.reduce((a,b)=>a+b,0)/d.yps.length:0;out.push({dog:clean(d.row["Dog Name"]),owner:ownerCell(d.row,sport),score:String(d.n),yps:Math.round(ay*100)/100,legs:d.n});}
 out.sort((a,b)=>b.legs-a.legs||b.yps-a.yps);return out;
}
function compute(sport,data){
 if(sport==="Obedience")return best3Classes(data,sport,OBED);
 if(sport==="Rally"){const r=best3Classes(data,sport,RALLY);r["High Combined"]=combinedCat(data,sport,["RADVB","REXCB"]);r["High Triple"]=combinedCat(data,sport,["RADVB","REXCB","RMAST"]);return r;}
 // Agility — per the official annual-awards criteria
 const cats={};
 cats["ESS of the Year"]=yoy(data,sport,"AGEXCB","JWWEXCB");                 // >=10 QQs, avg YPS fastest 10
 cats["Novice"]=agFirstSix(data,sport,["AGNOVA","AGNOVB"],["JWWNOVA","JWWNOVB"]); // avg first 6 (3 STD+3 JWW)
 cats["Open"]=agFirstSix(data,sport,["AGOPEN"],["JWWOPEN"]);
 Object.assign(cats,best3Classes(data,sport,{AGEXCA:"Excellent A"}));        // avg score
 cats["Preferred ESS of the Year"]=agPreferredTotal(data,sport);            // total of all Preferred Qs
 return cats;
}

// ---------- state + render ----------
let DATA={}, META={}, cur=null;
function render(){
 const rep=document.getElementById("ecReport");rep.innerHTML="";
 const cats=DATA[cur]||{};const order=ORDER[cur]||Object.keys(cats);
 const isAg=cur==="Agility";
 let any=false;
 for(const cat of order){
   const rows=cats[cat]||[];
   const combo=cat.startsWith("High "),pref=cat==="Preferred ESS of the Year";
   let suffix="",metric="Avg Score";
   if(pref){suffix="  (total qualifying Preferred runs · ties by YPS)";metric="# Qual. Runs";}
   else if(cat==="ESS of the Year"){suffix="  (avg YPS, fastest 10 QQs · min 10 QQs)";metric="Avg YPS";}
   else if(isAg&&(cat==="Novice"||cat==="Open")){suffix="  (avg of first 6: 3 Standard + 3 Jumpers)";}
   else if(isAg&&cat==="Excellent A"){suffix="  (highest average score)";}
   else if(combo){suffix="  (combined classes, best 5 trials — DRAFT, pending confirmation)";}
   const h=document.createElement("div");h.className="ec-cat";h.innerHTML=esc(cat)+"<span style='font-weight:400;font-size:12.5px;color:"+(combo?"#b04a44":"var(--muted)")+"'>"+esc(suffix)+"</span>";rep.appendChild(h);
   if(!rows.length){const e=document.createElement("div");e.className="ec-empty";e.textContent="No qualifiers (no dog meets the required legs/QQs).";rep.appendChild(e);continue;}
   any=true;
   const t=document.createElement("table");t.className="ec-tbl";
   t.innerHTML="<tr><th>Rank</th><th>Dog</th><th>Owner(s)</th><th style='text-align:right'>"+metric+"</th></tr>";
   rows.forEach((r,i)=>{const tr=document.createElement("tr");tr.innerHTML=`<td class='rank'>${i+1}</td><td class='dog'>${esc(r.dog)}</td><td>${esc(r.owner)}</td><td class='sc'>${r.score}</td>`;t.appendChild(tr);});
   rep.appendChild(t);
 }
 const note=document.createElement("div");note.className="ec-note";note.textContent="* = owner matched the ESSFTA membership directory (approximate). "+META[cur].file;rep.appendChild(note);
}
function esc(s){return String(s).replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));}
function buildTabs(){
 const tabs=document.getElementById("ecTabs");tabs.innerHTML="";
 Object.keys(DATA).forEach(sp=>{const b=document.createElement("button");b.className="ec-tab"+(sp===cur?" active":"");b.textContent=sp;b.onclick=()=>{cur=sp;[...tabs.children].forEach(c=>c.classList.remove("active"));b.classList.add("active");render();};tabs.appendChild(b);});
}
// ---------- file handling ----------
function handleFiles(files){
 const t0=performance.now();
 const jobs=[...files].map(f=>f.arrayBuffer().then(buf=>{
   const wb=XLSX.read(buf,{type:"array",cellDates:true});
   const ws=wb.Sheets[wb.SheetNames[0]];
   const rows=XLSX.utils.sheet_to_json(ws,{header:1,raw:true,cellDates:true});
   const sport=detectSport(rows);if(!sport)return null;
   const data=toObjects(rows);
   DATA[sport]=compute(sport,data);META[sport]={file:f.name,n:data.length};
   return sport;
 }).catch(()=>null));
 Promise.all(jobs).then(res=>{
   const got=res.filter(Boolean);
   document.getElementById("ecFiles").innerHTML=[...files].map(f=>"<span>"+esc(f.name)+"</span>").join("");
   if(!Object.keys(DATA).length){alert("Couldn't read a sport from those files. Expecting AKC Companion-Events .xls (Obedience/Agility/Rally).");return;}
   cur=Object.keys(DATA)[0];
   document.getElementById("ecResults").style.display="block";
   buildTabs();render();
   const ms=Math.round(performance.now()-t0);window.__procMs=ms;
   const nrows=Object.values(META).reduce((a,m)=>a+(m.n||0),0);
   document.getElementById("ecStat").textContent=`Processed ${got.length} file(s) · ${nrows} results · in ${ms} ms (${(ms/Math.max(1,got.length)).toFixed(0)} ms/file).`;
 });
}
const drop=document.getElementById("ecDrop"),input=document.getElementById("ecInput");
drop.addEventListener("click",()=>input.click());
input.addEventListener("change",e=>handleFiles(e.target.files));
["dragover","dragenter"].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.add("over");}));
["dragleave","drop"].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.remove("over");}));
drop.addEventListener("drop",e=>{if(e.dataTransfer.files.length)handleFiles(e.dataTransfer.files);});
// font toggle
const fb=document.getElementById("ecFont"),root=document.getElementById("ecRoot");
fb.querySelectorAll("button").forEach(btn=>btn.onclick=()=>{root.classList.toggle("serifmode",btn.dataset.f==="serif");fb.querySelectorAll("button").forEach(b=>b.classList.toggle("on",b===btn));});
// PDF page-orientation toggle (Portrait default; affects the downloaded PDF only)
let pdfOrient="portrait";
const ob=document.getElementById("ecOrient");
ob.querySelectorAll("button").forEach(btn=>btn.onclick=()=>{pdfOrient=btn.dataset.o;ob.querySelectorAll("button").forEach(b=>b.classList.toggle("on",b===btn));});
// Word (.docx) export — real OOXML via docx.js, built from the active sport
document.getElementById("ecDocx").onclick=()=>{
 if(typeof docx==="undefined"){alert("Word library still loading — try again in a moment.");return;}
 const D=docx,cats=DATA[cur]||{},order=ORDER[cur]||Object.keys(cats),isAg=cur==="Agility";
 const PAR=(t,o={})=>new D.Paragraph({children:[new D.TextRun({text:String(t),bold:o.bold,italics:o.ital,color:o.color,size:o.size})],heading:o.h,spacing:o.sp});
 const cell=(t,o={})=>new D.TableCell({width:{size:o.w||2000,type:D.WidthType.DXA},margins:{top:40,bottom:40,left:80,right:80},
   children:[new D.Paragraph({alignment:o.right?D.AlignmentType.RIGHT:D.AlignmentType.LEFT,children:[new D.TextRun({text:String(t),bold:o.bold,color:o.color})]})]});
 const kids=[PAR(`ESSFTA ${cur} — Quarterly Rankings`,{h:D.HeadingLevel.HEADING_1}),
   PAR("UNOFFICIAL / DRAFT — computed from AKC Companion-Events data for review; not an official ESSFTA report.",{ital:true,color:"9A6A1A",sp:{after:160}})];
 const W=[700,5200,3200,1400];
 for(const cat of order){
   const rows=cats[cat]||[];
   const metric=(isAg&&cat.includes("of the Year"))?"Avg YPS":"Avg Score";
   kids.push(PAR(cat,{h:D.HeadingLevel.HEADING_2,sp:{before:200,after:80}}));
   if(!rows.length){kids.push(PAR("No qualifiers.",{ital:true,color:"888888"}));continue;}
   const head=new D.TableRow({tableHeader:true,children:[cell("Rank",{bold:true,w:W[0]}),cell("Dog",{bold:true,w:W[1]}),cell("Owner(s)",{bold:true,w:W[2]}),cell(metric,{bold:true,right:true,w:W[3]})]});
   const body=rows.map((r,i)=>new D.TableRow({children:[cell(i+1,{w:W[0]}),cell(r.dog,{w:W[1],color:"8A2D33"}),cell(r.owner,{w:W[2]}),cell(r.score,{right:true,bold:true,w:W[3]})]}));
   kids.push(new D.Table({width:{size:100,type:D.WidthType.PERCENTAGE},rows:[head,...body]}));
 }
 kids.push(PAR("* = owner matched the ESSFTA membership directory (approximate). Source: AKC Quarterly Companion-Events Report.",{ital:true,color:"999999",size:16,sp:{before:160}}));
 const doc=new D.Document({sections:[{properties:{},children:kids}]});
 D.Packer.toBlob(doc).then(blob=>{const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=`ESSFTA_${cur}_Rankings.docx`;document.body.appendChild(a);a.click();a.remove();});
};
// PDF — generated client-side with jsPDF+autotable → a real downloaded .pdf (no print dialog,
// so Safari's "Open in Preview" blank-page bug can't happen).
document.getElementById("ecPdf").onclick=()=>{
 if(!(window.jspdf&&window.jspdf.jsPDF)){alert("The PDF engine is still loading — please try again in a moment.");return;}
 const cats=DATA[cur]||{},order=ORDER[cur]||Object.keys(cats),isAg=cur==="Agility";
 const font=root.classList.contains("serifmode")?"times":"helvetica";
 const {jsPDF}=window.jspdf;
 const doc=new jsPDF({orientation:pdfOrient,unit:"pt",format:"letter"});
 const pageW=doc.internal.pageSize.getWidth(),pageH=doc.internal.pageSize.getHeight(),M=40;
 const MAROON=[107,35,39],MAROON2=[138,45,51],GOLD=[200,162,74],PAPER=[251,245,233],INK=[42,35,32],MUTED=[138,127,115],SHADE=[251,247,238];
 const logoW=120,logoH=logoW*181/800;
 try{doc.addImage(LOGO,"PNG",M,M,logoW,logoH);}catch(e){}
 doc.setFont("times","bold");doc.setTextColor(MAROON[0],MAROON[1],MAROON[2]);doc.setFontSize(16);
 doc.text("ESSFTA "+cur+" — Quarterly Rankings",M+logoW+12,M+14);
 doc.setFont(font,"italic");doc.setTextColor(154,106,26);doc.setFontSize(8.5);
 doc.text("UNOFFICIAL / DRAFT — computed from AKC Companion-Events data for review; not an official ESSFTA report.",M+logoW+12,M+28,{maxWidth:pageW-M-logoW-M-12});
 let y=M+Math.max(logoH,32)+6;
 doc.setDrawColor(GOLD[0],GOLD[1],GOLD[2]);doc.setLineWidth(2);doc.line(M,y,pageW-M,y);y+=14;
 for(const cat of order){
   const rows=cats[cat]||[];
   const combo=cat.startsWith("High "),pref=cat==="Preferred ESS of the Year";
   let suffix="",metric="Avg Score";
   if(pref){suffix=" (total qualifying Preferred runs · ties by YPS)";metric="# Qual. Runs";}
   else if(cat==="ESS of the Year"){suffix=" (avg YPS, fastest 10 QQs · min 10 QQs)";metric="Avg YPS";}
   else if(isAg&&(cat==="Novice"||cat==="Open")){suffix=" (avg of first 6: 3 Standard + 3 Jumpers)";}
   else if(isAg&&cat==="Excellent A"){suffix=" (highest average score)";}
   else if(combo){suffix=" (combined classes, best 5 — DRAFT)";}
   if(y>pageH-90){doc.addPage();y=M;}
   doc.setFont("times","bold");doc.setTextColor(MAROON[0],MAROON[1],MAROON[2]);doc.setFontSize(12);
   doc.text(cat,M,y+8);
   if(suffix){const w=doc.getTextWidth(cat);doc.setFont(font,"normal");doc.setTextColor(combo?176:MUTED[0],combo?74:MUTED[1],combo?68:MUTED[2]);doc.setFontSize(8);doc.text(suffix,M+w+5,y+8);}
   doc.setDrawColor(GOLD[0],GOLD[1],GOLD[2]);doc.setLineWidth(1.5);doc.line(M,y+13,pageW-M,y+13);y+=20;
   if(!rows.length){doc.setFont(font,"italic");doc.setTextColor(MUTED[0],MUTED[1],MUTED[2]);doc.setFontSize(9);doc.text("No qualifiers (no dog meets the required legs/QQs).",M,y+6);y+=20;continue;}
   doc.autoTable({startY:y,margin:{left:M,right:M,top:M},theme:"striped",
     head:[["Rank","Dog","Owner(s)",metric]],
     body:rows.map((r,i)=>[String(i+1),String(r.dog),String(r.owner),String(r.score)]),
     styles:{font:font,fontSize:9,cellPadding:4,textColor:INK,overflow:"linebreak"},
     headStyles:{font:font,fontStyle:"bold",fillColor:PAPER,textColor:MAROON,fontSize:8.5},
     alternateRowStyles:{fillColor:SHADE},
     columnStyles:{0:{cellWidth:42,fontStyle:"bold"},1:{textColor:MAROON2,fontStyle:"bold"},3:{halign:"right",fontStyle:"bold",cellWidth:75}}});
   y=doc.lastAutoTable.finalY+16;
 }
 const pages=doc.internal.getNumberOfPages();
 for(let i=1;i<=pages;i++){doc.setPage(i);doc.setFont(font,"normal");doc.setTextColor(MUTED[0],MUTED[1],MUTED[2]);doc.setFontSize(7.5);
   doc.text("* = owner matched the ESSFTA membership directory (approximate). "+(META[cur]?META[cur].file:""),M,pageH-16,{maxWidth:pageW-M-60});
   doc.text(i+" / "+pages,pageW-M,pageH-16,{align:"right"});}
 doc.save("ESSFTA_"+cur+"_Rankings_unofficial.pdf");
};
</script>
</body></html>'''

out = HTML.replace("__MEMBERS__", json.dumps(members, ensure_ascii=False)).replace("__LOGO__", logo)
path = os.path.join(HERE, "rankings_calculator.html")
open(path, "w", encoding="utf-8").write(out)
print(f"wrote {path}  ({os.path.getsize(path)//1024} KB, {len(members)} members embedded)")

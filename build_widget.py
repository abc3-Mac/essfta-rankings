#!/usr/bin/env python3
"""Build the self-contained ESSFTA "Quarterly Rankings" widget.

Top-level tabs by SPORT — Breed/Group · Obedience · Agility · Rally. Each sport
carries its own category selector, year filter, search and click-sort with
sport-appropriate columns. Maroon/gold/cream ESSFTA house style + logo. One
self-contained HTML string, portable to a Ghost Lexical html card and WordPress.

Names/owners come pre-cleaned + Title-Cased from dataprep (sport names untouched).
"""
import json, base64, os, re
from dataprep import load_conformation, load_sports

HERE = os.path.dirname(os.path.abspath(__file__))
conf = load_conformation()
sports = load_sports()

# ---------------------------------------------------------------- conformation
BREED_STATS = [("bob_shows", "#BOB"), ("bob_spec", "BOB Spec"), ("bob_pts", "BOB Pts"),
               ("bos_shows", "#BOS"), ("bos_spec", "BOS Spec"), ("bos_pts", "BOS Pts"),
               ("total", "Total")]
GROUP_STATS = [("bis_n", "#BIS"), ("bis_pts", "BIS Pts"),
               ("grp1_n", "#GRP1"), ("grp1_pts", "GRP1 Pts"),
               ("grp2_n", "#GRP2"), ("grp2_pts", "GRP2 Pts"),
               ("grp3_n", "#GRP3"), ("grp3_pts", "GRP3 Pts"),
               ("grp4_n", "#GRP4"), ("grp4_pts", "GRP4 Pts"), ("total", "Total")]
CONF_SECTIONS = [
    ("Breed - Dogs",    "Breed · Dogs",    "Dog",   BREED_STATS),
    ("Breed - Bitches", "Breed · Bitches", "Bitch", BREED_STATS),
    ("Group - Dogs",    "Group · Dogs",    "Dog",   GROUP_STATS),
    ("Group - Bitches", "Group · Bitches", "Bitch", GROUP_STATS),
]


def rank_cell(r):
    return f"{r['rank']} (T)" if r.get("tie") else str(r["rank"])


def newest_first(rows, yi=0, ri=2):
    def k(row):
        yr = -int(row[yi]) if str(row[yi]).isdigit() else 0
        rk = int(re.sub(r"\D", "", str(row[ri])) or 0)
        return (yr, rk)
    return sorted(rows, key=k)


def build_conformation():
    views = {}
    cats = []
    for section, label, namehdr, stats in CONF_SECTIONS:
        headers = ["Year", "Qtr", "Rank", namehdr, "Owner"] + [h for _, h in stats]
        numeric = [True, False, True, False, False] + [True] * len(stats)
        rows = []
        for r in conf:
            if r["section"] != section:
                continue
            row = [r["year"], r["quarter"], rank_cell(r), r["name"], r["owner"]]
            row += [r.get(k, "") for k, _ in stats]
            rows.append(row)
        rows = newest_first(rows)
        cats.append(label)
        views[label] = {"headers": headers, "numeric": numeric, "rows": rows}
    years = sorted({r["year"] for r in conf}, reverse=True)
    return {"label": "Breed / Group", "kind": "sections",
            "cats": cats, "views": views, "years": years}


# ------------------------------------------------------- obedience/agility/rally
def norm_category(sport, c):
    """Collapse near-duplicate category labels for a clean dropdown."""
    c = c.strip()
    if sport == "Agility":
        c = re.sub(r"\s*\(Highest Average Score\)\s*", "", c)
        c = re.sub(r"\s+Agility\b", "", c).strip()
    elif sport == "Rally":
        if c.startswith("High Combined"):
            c = "High Combined"
        if c == "Masters":
            c = "Master"
    return c or "Overall"


def build_sport(sport, score_hdrs):
    """score_hdrs: list of (key, Header) for the trailing numeric columns."""
    headers = ["Year", "Qtr", "Class", "Rank", "Dog", "Owner"] + [h for _, h in score_hdrs]
    numeric = [True, False, False, True, False, False] + [True] * len(score_hdrs)
    rows = []
    for r in sports:
        if r["sport"] != sport:
            continue
        cat = norm_category(sport, r["category"])
        row = [r["year"], r["quarter"], cat, rank_cell(r), r["dog"], r["owner"]]
        row += [r.get(k, "") for k, _ in score_hdrs]
        rows.append(row)
    rows = newest_first(rows, yi=0, ri=3)
    cats = ["All classes"] + sorted({row[2] for row in rows})
    years = sorted({row[0] for row in rows}, reverse=True)
    return {"label": sport, "kind": "classes", "catCol": 2,
            "headers": headers, "numeric": numeric, "rows": rows,
            "cats": cats, "years": years}


DATA = {
    "breedgroup": build_conformation(),
    "obedience":  build_sport("Obedience", [("score", "Score")]),
    "agility":    build_sport("Agility",   [("score", "Avg Score"), ("score2", "YPS")]),
    "rally":      build_sport("Rally",      [("score", "Score")]),
}
ORDER = ["breedgroup", "obedience", "agility", "rally"]

all_years = sorted({r["year"] for r in conf} | {r["year"] for r in sports})
span = f"{all_years[0]}–{all_years[-1]}"
total_rows = len(conf) + len(sports)
logo_b64 = base64.b64encode(open(os.path.join(HERE, "essfta-logo.png"), "rb").read()).decode()

# ---- per-sport explainer (AKC title/class changes) + data-coverage notes ----
# Sourced from AKC: GCH 2010 & its tiers 2011; Obedience optional classes 2010-11;
# Agility MACH 2004 / FAST 2007 / T2B & PACH 2011 / Premier 2015; Rally revamp
# (RACH + Master + Intermediate) Nov 2017.
EXPLAINERS = {
    "breedgroup": {
        "title": "How Breed/Group titles changed",
        "notes": [
            ("2010", "Grand Champion (GCH) title introduced — above the traditional Champion (CH)."),
            ("2011", "GCH levels added: Bronze, Silver, Gold, Platinum (GCHB / GCHS / GCHG / GCHP). Repeated Platinum shows as GCHP2, GCHP3…"),
        ],
        "blurb": "Rankings are by parent-club points. Because GCH and its tiers predate this data, you'll see CH through GCHP across all years.",
    },
    "obedience": {
        "title": "How Obedience classes changed",
        "notes": [
            ("2010", "Beginner Novice (BN) introduced as an optional titling class."),
            ("2011", "Graduate Novice (GN) & Graduate Open (GO) added; Preferred classes (PCD/PCDX/PUD) too."),
        ],
        "blurb": "“Optional” and “Preferred” classes appear as their own categories from these years on; Regular Novice/Open/Utility run throughout.",
    },
    "agility": {
        "title": "How Agility titles & reports changed",
        "notes": [
            ("2004", "MACH (Master Agility Champion) established."),
            ("2007", "FAST class added (NF / OF / XF titles)."),
            ("2011", "Time 2 Beat (T2B) and Preferred Agility Champion (PACH) introduced."),
            ("2015", "Premier classes added."),
        ],
        "blurb": "AKC changed the Agility ranking-report format several times, so some historical years are partial or were never published in a usable form (see coverage below).",
    },
    "rally": {
        "title": "How Rally titles & classes changed",
        "notes": [
            ("2005", "AKC Rally began; RAE (Rally Advanced Excellent) was the pinnacle title."),
            ("2017", "Major revamp: RACH (Rally Champion) title plus new Master and Intermediate (RI) classes. Earlier years top out at RAE — Master/Intermediate categories and RACH appear only from 2017."),
        ],
        "blurb": "If a class or top title seems missing in an early year, it likely didn't exist yet.",
    },
}

# Data coverage: which years in the overall span are missing for each sport.
for k, d in DATA.items():
    present = set(map(str, d["years"]))
    missing = [y for y in all_years if y not in present]
    d["explainer"] = EXPLAINERS[k]
    d["coverage"] = {"missing": missing,
                     "note": EXPLAINERS[k].get("coverage_note", "")}

HTML = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ESSFTA Quarterly Rankings</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600;700&display=swap');
  .essfta-qr{--maroon:#6B2327;--maroon2:#8A2D33;--cream:#F4EEE2;--paper:#FBF5E9;--gold:#C8A24A;--ink:#2A2320;--muted:#8A7F73;--line:#E2D8C2;
    --serif:'Fraunces',Georgia,'Times New Roman',serif;--sans:'Inter',-apple-system,'Helvetica Neue',Arial,sans-serif;
    font-family:var(--sans);color:var(--ink);background:var(--cream);max-width:1120px;margin:0 auto;border:1px solid var(--line);border-radius:14px;overflow:hidden;box-shadow:0 6px 24px rgba(42,35,32,.12);}
  .essfta-qr *{box-sizing:border-box;}
  .qr-head{background:linear-gradient(180deg,#7A2A2F,#5E1F23);padding:24px 28px;display:flex;align-items:center;gap:22px;border-bottom:4px solid var(--gold);}
  .qr-head img{height:66px;width:auto;background:var(--cream);padding:7px 12px;border-radius:8px;}
  .qr-head h1{font-family:var(--serif);font-weight:600;color:var(--cream);font-size:30px;margin:0;letter-spacing:.3px;}
  .qr-head p{color:#E7D6A8;margin:6px 0 0;font-size:12.5px;letter-spacing:1px;font-weight:500;text-transform:uppercase;}
  .qr-tabs{display:flex;flex-wrap:wrap;justify-content:center;background:var(--maroon);padding:0 8px;}
  .qr-tab{appearance:none;border:0;background:transparent;color:#E7D6A8;font:600 15px/1.15 var(--sans);padding:14px 22px;cursor:pointer;border-bottom:3px solid transparent;white-space:nowrap;letter-spacing:.2px;}
  .qr-tab:hover{color:#fff;}
  .qr-tab.active{color:#fff;border-bottom-color:var(--gold);background:rgba(0,0,0,.16);}
  .qr-body{padding:20px 26px 26px;}
  .qr-help{color:#6a6258;font-size:13px;line-height:1.55;margin-bottom:14px;padding:10px 15px;background:var(--paper);border-left:3px solid var(--gold);border-radius:6px;}
  .qr-help b{color:var(--maroon);}
  .qr-toolbar{display:flex;align-items:center;gap:10px;margin-bottom:14px;flex-wrap:wrap;}
  .qr-sel{padding:10px 12px;border:1.5px solid var(--line);border-radius:8px;font-size:14px;background:#fff;color:var(--ink);font-weight:600;font-family:var(--sans);max-width:260px;}
  .qr-search{flex:1;min-width:180px;max-width:320px;padding:10px 13px;border:1.5px solid var(--line);border-radius:8px;font-size:15px;background:#fff;font-family:var(--sans);}
  .qr-search:focus,.qr-sel:focus{outline:none;border-color:var(--gold);}
  .qr-count{color:var(--muted);font-size:14px;white-space:nowrap;margin-left:auto;}
  .qr-info{appearance:none;border:1.5px solid var(--gold);background:var(--paper);color:var(--maroon);font:600 13px/1 var(--sans);padding:9px 13px;border-radius:8px;cursor:pointer;white-space:nowrap;display:inline-flex;align-items:center;gap:6px;}
  .qr-info:hover{background:#F1E7D0;}
  .qr-pdf{font-weight:700;}
  .qr-info .ic{display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;border-radius:50%;background:var(--maroon);color:var(--cream);font-size:11px;font-weight:700;}
  .qr-panel{display:none;margin-bottom:14px;border:1px solid var(--line);border-left:3px solid var(--maroon);border-radius:8px;background:#fff;padding:16px 18px;}
  .qr-panel.open{display:block;}
  .qr-panel h3{font-family:var(--serif);color:var(--maroon);font-size:18px;margin:0 0 10px;font-weight:600;}
  .qr-timeline{list-style:none;margin:0 0 4px;padding:0;}
  .qr-timeline li{display:flex;gap:12px;padding:7px 0;border-bottom:1px dashed var(--line);font-size:13.5px;line-height:1.5;color:#4a423b;}
  .qr-timeline li:last-child{border-bottom:0;}
  .qr-timeline .yr{flex:0 0 auto;min-width:46px;font-weight:700;color:var(--gold);font-family:var(--serif);}
  .qr-panel .blurb{font-size:13px;color:#6a6258;margin:10px 0 0;line-height:1.55;}
  .qr-panel .cov{margin-top:12px;padding:9px 13px;background:#FBF1E0;border-radius:6px;font-size:13px;color:#7a5a23;line-height:1.5;}
  .qr-panel .cov b{color:var(--maroon);}
  .qr-miss{margin:-4px 0 14px;font-size:12.5px;color:#9a6a1a;background:#FBF1E0;border-radius:6px;padding:7px 12px;display:none;}
  .qr-miss.show{display:block;}
  .qr-scrollbox{position:relative;}
  .qr-tablewrap{overflow-x:auto;border-radius:10px;border:1px solid var(--line);background:#fff;-webkit-overflow-scrolling:touch;}
  .qr-fade{position:absolute;top:0;bottom:0;width:48px;pointer-events:none;opacity:0;transition:opacity .2s;z-index:5;border-radius:10px;}
  .qr-fade.r{right:0;background:linear-gradient(to right,rgba(255,255,255,0),rgba(107,35,39,.16));}
  .qr-scrollbox.can-r .qr-fade.r{opacity:1;}
  .qr-scrollhint{position:absolute;right:14px;bottom:12px;background:var(--maroon);color:var(--cream);font:600 12.5px/1 var(--sans);padding:7px 13px;border-radius:16px;pointer-events:none;opacity:0;transition:opacity .25s;z-index:6;box-shadow:0 2px 10px rgba(0,0,0,.25);white-space:nowrap;}
  .qr-scrollbox.can-r .qr-scrollhint{opacity:.94;}
  table.qr-tbl{border-collapse:collapse;width:100%;font-size:13.5px;}
  table.qr-tbl thead th{background:var(--paper);color:var(--maroon);text-align:left;padding:10px 11px;font-weight:700;cursor:pointer;white-space:nowrap;border-bottom:2px solid var(--gold);position:sticky;top:0;user-select:none;}
  table.qr-tbl thead th:hover{background:#F1E7D0;}
  table.qr-tbl thead th .ar{color:var(--gold);font-size:11px;}
  table.qr-tbl td{padding:8px 11px;border-bottom:1px solid #EFE7D6;vertical-align:top;white-space:nowrap;}
  table.qr-tbl td.name{white-space:normal;min-width:210px;font-weight:600;color:var(--maroon2);}
  table.qr-tbl td.owner{white-space:normal;min-width:160px;color:#5b524a;}
  table.qr-tbl td.cls{white-space:normal;min-width:120px;color:#6a6258;}
  table.qr-tbl td.tot{font-weight:700;}
  table.qr-tbl tbody tr:nth-child(even){background:#FBF7EE;}
  table.qr-tbl tbody tr:hover{background:#F4ECD9;}
  table.qr-tbl tbody td.empty{text-align:center;color:var(--muted);padding:26px;font-style:italic;}
  .qr-pager{display:flex;align-items:center;justify-content:center;gap:10px;margin-top:16px;}
  .qr-pager button{background:#fff;border:1.5px solid var(--line);border-radius:7px;padding:8px 14px;cursor:pointer;font-size:14px;color:var(--maroon);font-weight:600;font-family:var(--sans);}
  .qr-pager button:disabled{opacity:.4;cursor:default;}
  .qr-pager span{color:var(--muted);font-size:14px;}
  .qr-foot{padding:14px 28px;background:var(--paper);border-top:1px solid var(--line);color:var(--muted);font-size:12.5px;text-align:center;line-height:1.5;}
  @media(max-width:820px){.qr-body{padding:16px 14px 20px;}.qr-head{padding:18px;gap:16px;}.qr-tab{padding:12px 15px;font-size:14px;}.qr-head h1{font-size:24px;}}
  @media(max-width:600px){.qr-head{flex-wrap:wrap;gap:12px;}.qr-head h1{font-size:20px;}.qr-head img{height:48px;}.qr-head p{font-size:10.5px;letter-spacing:.4px;}.qr-tab{padding:11px 12px;font-size:13px;}.qr-count{margin-left:0;}table.qr-tbl{font-size:12.5px;}}
</style></head>
<body style="margin:0;background:#EDE5D4;padding:24px 12px;">
<div class="essfta-qr" id="essftaQR">
  <div class="qr-head"><img alt="ESSFTA" src="data:image/png;base64,__LOGO__"><div><h1>Quarterly Rankings</h1><p>English Springer Spaniel Field Trial Association · Parent Club · __SPAN__</p></div></div>
  <div class="qr-tabs" id="qrTabs"></div>
  <div class="qr-body">
    <div class="qr-help"><b>How to use:</b> pick a <b>sport</b> above, choose a <b>category</b> and <b>year</b>, type in <b>search</b> to filter by dog or owner, click a column heading to <b>sort</b>, and <b>scroll the table sideways</b> to see every column. Standings are year-end (labeled Q4); the latest year shows progress to date.</div>
    <div class="qr-toolbar">
      <select class="qr-sel" id="qrCat"></select>
      <select class="qr-sel" id="qrYear"></select>
      <input class="qr-search" id="qrSearch" placeholder="Search dog or owner…">
      <button class="qr-info" id="qrInfo" type="button"><span class="ic">i</span><span id="qrInfoLbl">About this sport</span></button>
      <button class="qr-info qr-pdf" id="qrPdf" type="button" title="Download the current view as a PDF">⬇ PDF</button>
      <div class="qr-count" id="qrCount"></div>
    </div>
    <div class="qr-panel" id="qrPanel"></div>
    <div class="qr-miss" id="qrMiss"></div>
    <div class="qr-scrollbox"><div class="qr-tablewrap" id="qrWrap"><table class="qr-tbl"><thead id="qrHead"></thead><tbody id="qrBody"></tbody></table></div><div class="qr-fade r"></div><div class="qr-scrollhint">swipe / scroll →</div></div>
    <div class="qr-pager"><button id="qrPrev">‹ Prev</button><span id="qrPage"></span><button id="qrNext">Next ›</button></div>
  </div>
  <div class="qr-foot">Data compiled from ESSFTA quarterly ranking reports (AKC electronic records) across Breed/Group, Obedience, Agility &amp; Rally · __TOTAL__ standings rows · digitized __SPAN__ · self-contained widget, portable to Ghost &amp; WordPress.<br>Points/scores follow each AKC program. “(T)” marks a tie.</div>
</div>
<script>
const DATA=__PAYLOAD__, ORDER=__ORDER__, PER=30;
const LOGO=document.querySelector('.qr-head img').src;
let cur=ORDER[0];
const st={};
ORDER.forEach(k=>{st[k]={cat:DATA[k].cats[0],year:'',q:'',sort:-1,dir:1,page:0};});
const tabsEl=document.getElementById('qrTabs');
ORDER.forEach(k=>{const b=document.createElement('button');b.className='qr-tab'+(k===cur?' active':'');b.textContent=DATA[k].label;b.onclick=()=>{cur=k;[...tabsEl.children].forEach(c=>c.classList.remove('active'));b.classList.add('active');syncControls();render();};tabsEl.appendChild(b);});
const catSel=document.getElementById('qrCat'),yearSel=document.getElementById('qrYear'),searchEl=document.getElementById('qrSearch');
const panelEl=document.getElementById('qrPanel'),missEl=document.getElementById('qrMiss'),infoBtn=document.getElementById('qrInfo');
function buildPanel(){const d=DATA[cur],e=d.explainer;
  const tl=e.notes.map(n=>`<li><span class="yr">${n[0]}</span><span>${n[1]}</span></li>`).join('');
  let cov='';const miss=d.coverage.missing;
  if(miss.length)cov=`<div class="cov"><b>Data coverage:</b> no published ${d.label} report for ${miss.join(', ')}. Some other early years may be partial — AKC changed these report formats over time.</div>`;
  panelEl.innerHTML=`<h3>${e.title}</h3><ul class="qr-timeline">${tl}</ul><p class="blurb">${e.blurb}</p>${cov}`;
  // inline always-visible missing-years badge
  if(miss.length){missEl.textContent='⚠ No published '+d.label+' report for: '+miss.join(', ')+'.';missEl.classList.add('show');}
  else missEl.classList.remove('show');}
function syncControls(){const d=DATA[cur],s=st[cur];
  catSel.innerHTML=d.cats.map(c=>`<option${c===s.cat?' selected':''}>${c}</option>`).join('');
  yearSel.innerHTML='<option value="">All years</option>'+d.years.map(y=>`<option value="${y}"${String(y)===s.year?' selected':''}>${y}</option>`).join('');
  searchEl.value=s.q;
  panelEl.classList.remove('open');buildPanel();}
infoBtn.onclick=()=>panelEl.classList.toggle('open');
function esc(s){return String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
function downloadPDF(){const d=DATA[cur],s=st[cur],v=viewFor(),rows=filtered(v);
  const bits=[d.label];if(s.cat&&s.cat!==d.cats[0])bits.push(s.cat);bits.push(s.year?s.year:'All years');if(s.q)bits.push('“'+s.q+'”');
  const sub=bits.join(' · ');
  const head='<tr>'+v.headers.map(h=>'<th>'+esc(h)+'</th>').join('')+'</tr>';
  const body=rows.map(r=>'<tr>'+r.map(c=>'<td>'+esc(c)+'</td>').join('')+'</tr>').join('');
  const when=new Date().toLocaleDateString(undefined,{year:'numeric',month:'long',day:'numeric'});
  const miss=d.coverage.missing.length?'<p class="cov">No published '+esc(d.label)+' report for: '+d.coverage.missing.join(', ')+'.</p>':'';
  const doc=`<!doctype html><html><head><meta charset="utf-8"><title>ESSFTA Rankings — ${esc(sub)}</title>
  <style>
    @page{size:landscape;margin:14mm 12mm;}
    body{font-family:-apple-system,'Helvetica Neue',Arial,sans-serif;color:#2A2320;margin:0;}
    .h{display:flex;align-items:center;gap:16px;border-bottom:3px solid #C8A24A;padding-bottom:12px;margin-bottom:6px;}
    .h img{height:54px;}
    .h h1{font-family:Georgia,serif;color:#6B2327;font-size:22px;margin:0;}
    .h .s{color:#6a6258;font-size:13px;margin-top:3px;}
    .cov{color:#9a6a1a;font-size:11.5px;margin:4px 0 0;}
    table{border-collapse:collapse;width:100%;font-size:10.5px;margin-top:10px;}
    th{background:#FBF5E9;color:#6B2327;text-align:left;padding:5px 7px;border-bottom:1.5px solid #C8A24A;font-size:10px;}
    td{padding:4px 7px;border-bottom:0.5px solid #EFE7D6;vertical-align:top;}
    tbody tr:nth-child(even){background:#FBF7EE;}
    thead{display:table-header-group;}
    .ft{margin-top:12px;color:#8A7F73;font-size:10px;border-top:1px solid #E2D8C2;padding-top:8px;}
  </style></head><body onload="window.print()">
    <div class="h"><img src="${LOGO}"><div><h1>ESSFTA Quarterly Rankings</h1><div class="s">${esc(sub)} — ${rows.length} entr${rows.length===1?'y':'ies'}</div>${miss}</div></div>
    <table><thead>${head}</thead><tbody>${body}</tbody></table>
    <div class="ft">Compiled from ESSFTA quarterly ranking reports (AKC electronic records) · generated ${when} · “(T)” marks a tie.</div>
  </body></html>`;
  const w=window.open('','_blank');
  if(!w){alert('Please allow pop-ups to download the PDF.');return;}
  w.document.write(doc);w.document.close();}
document.getElementById('qrPdf').onclick=downloadPDF;
function viewFor(){const d=DATA[cur],s=st[cur];
  if(d.kind==='sections'){const v=d.views[s.cat]||d.views[d.cats[0]];return{headers:v.headers,numeric:v.numeric,rows:v.rows};}
  let rows=d.rows;if(s.cat&&s.cat!==d.cats[0])rows=rows.filter(r=>r[d.catCol]===s.cat);
  return{headers:d.headers,numeric:d.numeric,rows};}
function filtered(v){const s=st[cur];let rows=v.rows;
  if(s.year)rows=rows.filter(r=>String(r[0])===s.year);
  if(s.q){const q=s.q.toLowerCase();rows=rows.filter(r=>r.some(c=>String(c).toLowerCase().includes(q)));}
  if(s.sort>=0){const sc=s.sort,nu=v.numeric[sc];rows=rows.slice().sort((a,b)=>{let x=a[sc],y=b[sc];if(nu){const nx=parseFloat(String(x).replace(/[^\d.-]/g,'')),ny=parseFloat(String(y).replace(/[^\d.-]/g,''));if(!isNaN(nx)&&!isNaN(ny))return(nx-ny)*s.dir;if(isNaN(nx))return 1;if(isNaN(ny))return -1;}return String(x).localeCompare(String(y))*s.dir;});}
  return rows;}
function render(){const d=DATA[cur],s=st[cur],v=viewFor();
  const head=document.getElementById('qrHead');head.innerHTML='';const tr=document.createElement('tr');
  v.headers.forEach((h,i)=>{const th=document.createElement('th');th.innerHTML=h+(s.sort===i?(' <span class="ar">'+(s.dir>0?'▲':'▼')+'</span>'):'');th.onclick=()=>{if(s.sort===i)s.dir=-s.dir;else{s.sort=i;s.dir=1;}s.page=0;render();};tr.appendChild(th);});head.appendChild(tr);
  const rows=filtered(v);const pages=Math.max(1,Math.ceil(rows.length/PER));if(s.page>=pages)s.page=pages-1;if(s.page<0)s.page=0;const slice=rows.slice(s.page*PER,s.page*PER+PER);
  const nameIdx=v.headers.findIndex(h=>h==='Dog'||h==='Bitch'),ownIdx=v.headers.indexOf('Owner'),clsIdx=v.headers.indexOf('Class'),totIdx=Math.max(v.headers.lastIndexOf('Total'),v.headers.indexOf('Score'),v.headers.indexOf('Avg Score'));
  const body=document.getElementById('qrBody');body.innerHTML='';
  if(!rows.length){body.innerHTML=`<tr><td class="empty" colspan="${v.headers.length}">No rows match — try “All classes”, “All years”, or clear the search.</td></tr>`;}
  slice.forEach(r=>{const trr=document.createElement('tr');r.forEach((c,i)=>{const td=document.createElement('td');td.textContent=c;if(i===nameIdx)td.className='name';else if(i===ownIdx)td.className='owner';else if(i===clsIdx)td.className='cls';else if(i===totIdx)td.className='tot';trr.appendChild(td);});body.appendChild(trr);});
  document.getElementById('qrCount').textContent=rows.length.toLocaleString()+' row'+(rows.length===1?'':'s');
  document.getElementById('qrPage').textContent='Page '+(s.page+1)+' / '+pages;
  document.getElementById('qrPrev').disabled=s.page<=0;document.getElementById('qrNext').disabled=s.page>=pages-1;updateHints();}
function updateHints(){const w=document.getElementById('qrWrap'),box=w.parentElement;box.classList.toggle('can-r',w.scrollWidth-w.clientWidth-w.scrollLeft>4);}
catSel.addEventListener('change',e=>{st[cur].cat=e.target.value;st[cur].page=0;st[cur].sort=-1;render();});
yearSel.addEventListener('change',e=>{st[cur].year=e.target.value;st[cur].page=0;render();});
searchEl.addEventListener('input',e=>{st[cur].q=e.target.value;st[cur].page=0;render();});
document.getElementById('qrPrev').onclick=()=>{st[cur].page--;render();};
document.getElementById('qrNext').onclick=()=>{st[cur].page++;render();};
document.getElementById('qrWrap').addEventListener('scroll',updateHints,{passive:true});
window.addEventListener('resize',updateHints);
syncControls();render();
</script>
</body></html>'''

out = (HTML.replace("__LOGO__", logo_b64)
           .replace("__SPAN__", span)
           .replace("__TOTAL__", f"{total_rows:,}")
           .replace("__PAYLOAD__", json.dumps(DATA, ensure_ascii=False))
           .replace("__ORDER__", json.dumps(ORDER)))
path = os.path.join(HERE, "quarterly_rankings_widget.html")
open(path, "w", encoding="utf-8").write(out)
print("sports:", {k: (len(v["views"]) if v["kind"] == "sections" else len(v["rows"]))
                  for k, v in DATA.items()})
for k in ORDER:
    d = DATA[k]
    n = sum(len(x["rows"]) for x in d["views"].values()) if d["kind"] == "sections" else len(d["rows"])
    print(f"  {k:11s} {n:5d} rows, {len(d['cats'])} cats, years {d['years'][-1]}–{d['years'][0]}")
print(f"wrote {path}  ({os.path.getsize(path)//1024} KB)")

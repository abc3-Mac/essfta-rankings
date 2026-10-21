#!/usr/bin/env python3
"""One club-styled PDF per sport for a built quarter (see build_quarter.py).

    python3 build_quarter_pdfs.py 2026 Q3

Reads quarters/<YYYY>Q<n>/report_data_<YYYY>Q<n>.json and writes
quarters/<YYYY>Q<n>/ESSFTA_<Sport>_<YYYY>_<window>.pdf — Breed/Group (landscape),
Obedience, Rally, Agility, Juniors. HTML -> PDF with Playwright/Chromium; margins
are set in pg.pdf(), not CSS @page (Chromium would override them).
"""
import base64, datetime, html, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from titlecase import tc_name, tc_owner  # noqa: E402

END = {"Q1": "March 31", "Q2": "June 30", "Q3": "September 30", "Q4": "December 31"}
FILE_WINDOW = {"Q1": "JanMar", "Q2": "JanJun", "Q3": "JanSep", "Q4": "JanDec"}

RALLY_ORDER = ["Novice A", "Novice B", "Advanced A", "Advanced B", "Excellent A", "Excellent B",
               "Master", "Intermediate", "Choice", "High Combined", "High Triple"]
RALLY_GROUPS = [("Regular titling classes", RALLY_ORDER[:7]), ("Optional titling classes", RALLY_ORDER[7:9]),
                ("Combined awards", RALLY_ORDER[9:])]
OBED_GROUPS = [("Regular classes", ["Regular: Novice A", "Regular: Novice B", "Regular: Open A", "Regular: Open B",
                                    "Regular: Utility A", "Regular: Utility B", "Regular: Combined Open B/Utility"]),
               ("Optional and Preferred classes", ["Optional: Beginner Novice A", "Optional: Beginner Novice B",
                                                   "Optional: Graduate Novice", "Optional: Graduate Open",
                                                   "Alternative: Preferred Novice", "Alternative: Preferred Open",
                                                   "Alternative: Preferred Utility"])]
AGIL_GROUPS = [("ESS of the Year — fastest 10 QQs", ["Excellent B", "Preferred Excellent B"]),
               ("Class awards — average score", ["Novice", "Open", "Excellent A", "Preferred Novice",
                                                 "Preferred Open", "Preferred Excellent A"])]
METRIC = {
    "Regular: Combined Open B/Utility": "Avg combined score — best five trials (Open B + Utility)",
    "High Combined": "Avg of the best three Advanced B + Excellent B days",
    "High Triple": "Avg of the best three Advanced B + Excellent B + Master days",
    "Excellent B": "Avg yards per second of the fastest 10 QQs (Excellent B Standard + Jumpers, same day; 10 QQs to list)",
    "Preferred Excellent B": "Avg yards per second of the fastest 10 Preferred QQs (10 QQs to list)",
    "Novice": "Avg of the 3 Standard + 3 Jumpers legs that earned this year's two titles",
    "Open": "Avg of the 3 Standard + 3 Jumpers legs that earned this year's two titles",
    "Preferred Novice": "Avg of the 3 Standard + 3 Jumpers legs that earned this year's two titles",
    "Preferred Open": "Avg of the 3 Standard + 3 Jumpers legs that earned this year's two titles",
    "Excellent A": "Avg of the 3 Standard + 3 Jumpers legs that earned this year's two titles",
    "Preferred Excellent A": "Avg of the 3 Standard + 3 Jumpers legs that earned this year's two titles",
}

CSS = """
:root{--maroon:#6B2327;--gold:#C8A24A;--ink:#2b2523;--muted:#7a6f6a;--rule:#e6ddd3;--shade:#faf6f0}
*{box-sizing:border-box}
body{margin:0;background:#fff;color:var(--ink);font:10.5px/1.45 Inter,Helvetica,Arial,sans-serif}
.kicker{letter-spacing:.18em;text-transform:uppercase;font-size:8px;color:var(--muted);font-weight:600}
.mast{display:flex;align-items:center;gap:14px;border-bottom:2px solid var(--gold);padding-bottom:8px;margin-bottom:10px}
.mast img{height:40px}
h1{font:600 22px/1.15 Fraunces,Georgia,serif;color:var(--maroon);margin:2px 0 3px}
.sub{color:var(--muted);font-size:9.5px}
.note{border:1px solid #ecd9a8;background:#fdf7e8;border-radius:4px;padding:6px 9px;margin:8px 0 2px;font-size:9px;color:#5c4a24}
h2{font:600 9px Inter,sans-serif;letter-spacing:.16em;text-transform:uppercase;color:var(--gold);margin:16px 0 4px}
h3{font:600 14px Fraunces,Georgia,serif;color:var(--maroon);margin:10px 0 1px}
.metric{color:var(--muted);font-size:8.5px;margin-bottom:3px}
section{break-inside:avoid}
table{width:100%;border-collapse:collapse;margin-bottom:4px}
th{font-size:8px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);text-align:left;
   border-bottom:1px solid var(--maroon);padding:3px 5px;font-weight:600}
td{padding:3.5px 5px;border-bottom:1px solid var(--rule);vertical-align:top}
tr:nth-child(even) td{background:var(--shade)}
td.n,th.n{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
td.r{width:24px;color:var(--muted)}
td.dog{font-weight:600;color:var(--maroon)}
.empty{color:var(--muted);font-style:italic;padding:2px 0 6px}
.foot{margin-top:14px;border-top:1px solid var(--rule);padding-top:6px;color:var(--muted);font-size:8.5px}
"""


def esc(x):
    return html.escape(str(x if x is not None else ""))


def fmt(x):
    if x in ("", None):
        return ""
    try:
        return f"{float(x):.2f}"
    except ValueError:
        return esc(x)


def fmt3(x):
    if x in ("", None):
        return ""
    try:
        return f"{float(x):.3f}"
    except ValueError:
        return esc(x)


def agility_title_note(d, year):
    """What the agility title rule did (Novice, Open, Excellent A and their Preferred classes)."""
    why = {"OLD LEG": "a title leg was run in an earlier year", "PRIOR YEAR": "a title was earned before " + year}
    parts = [f"Novice, Open and Excellent A awards count the three Standard and three Jumpers legs that earned "
             f"the two titles, checked against the AKC New Titles file: a dog is listed only when both titles are "
             f"dated {year} and all six legs were run in {year}."]
    for n in d.get("agility_title_removed", []):
        bad = n["std"] if n["std"]["verdict"] in why else n["jww"]
        parts.append(f"Not listed in {esc(n['category'])}: {esc(n['dog'])} — {why[bad['verdict']]} "
                     f"({esc(bad['title'])}{', dated ' + esc(bad['date']) if bad['date'] else ''}).")
    for n in d.get("agility_title_flagged", []):
        missing = [x["title"] for x in (n["std"], n["jww"]) if x["verdict"].startswith("NO TITLE")]
        if missing:
            parts.append(f"To confirm: {esc(n['dog'])} ({esc(n['category'])}) has its six legs this year but no "
                         f"{esc(' / '.join(missing))} title on the AKC file yet.")
    return " ".join(parts)


def page(title, sub, body, notes, foot, logo):
    return f"""<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@600&family=Inter:wght@400;600&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<div class="mast"><img src="data:image/png;base64,{logo}" alt=""><div>
<div class="kicker">English Springer Spaniel Field Trial Association</div>
<h1>{esc(title)}</h1><div class="sub">{sub}</div></div></div>
{''.join(f'<div class="note">{n}</div>' for n in notes)}
{body}
<div class="foot">{foot}</div></body></html>"""


def table(cols, rows):
    head = "".join(f'<th class="{c[2]}">{esc(c[0])}</th>' for c in cols)
    trs = []
    for r in rows:
        tds = "".join(f'<td class="{c[2]}">{c[1](r)}</td>' for c in cols)
        trs.append(f"<tr>{tds}</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(trs)}</tbody></table>"


def sport_body(rows, groups, cols_for):
    by_cat = {}
    for r in rows:
        by_cat.setdefault(r["category"], []).append(r)
    out = []
    for gname, cats in groups:
        present = [c for c in cats if c in by_cat]
        if not present:
            continue
        out.append(f"<h2>{esc(gname)}</h2>")
        for cat in present:
            label = cat.split(": ", 1)[-1]
            metric = METRIC.get(cat, "Avg of the best three qualifying scores (three to list)")
            out.append(f'<section><h3>{esc(label)}</h3><div class="metric">{esc(metric)}</div>'
                       f'{table(cols_for(cat), by_cat[cat])}</section>')
    rest = [c for c in by_cat if all(c not in cs for _, cs in groups)]
    if rest:
        raise SystemExit(f"categories with no place in the report: {rest}")
    return "".join(out)


def title_note(d, year):
    """What the title check (check_title_eligibility.py) did to the titling classes."""
    why = {"OLD LEG": "its title is dated " + year + " but one of the three title legs was run in an earlier year",
           "PRIOR YEAR": "its title was earned before " + year}
    parts = [f"Titling classes are checked against the AKC New Titles file: a dog is listed only in the year its "
             f"title is dated, with all three title legs that year."]
    for r in d.get("title_removed", []):
        v = r["title_verdict"]
        parts.append(f"Not listed in {esc(v['category'].split(': ', 1)[-1])}: {esc(r['dog'])} — "
                     f"{why[v['verdict']]} (title dated {esc(v['title_date'])}).")
    for v in d.get("title_flagged", []):
        parts.append(f"To confirm: {esc(v['dog'])} ({esc(v['category'].split(': ', 1)[-1])}) has three qualifying "
                     f"scores this year but no {esc(v['title'])} title on the AKC file yet.")
    return " ".join(parts)


def main():
    year, quarter = sys.argv[1], sys.argv[2].upper()
    tag = f"{year}{quarter}"
    qdir = os.path.join(HERE, "quarters", tag)
    d = json.load(open(os.path.join(qdir, f"report_data_{tag}.json")))
    logo = base64.b64encode(open(os.path.join(HERE, "essfta-logo.png"), "rb").read()).decode()
    window = f"January 1 through {END[quarter]}, {year}"
    qs = " + ".join(f"{i}Q" for i in range(1, int(quarter[1]) + 1))
    today = datetime.date.today().strftime("%B %-d, %Y")
    member = "* = ESSFTA member."
    computed = (f"Computed from the AKC results exports ({qs} {year}) under the club's confirmed scoring rules. "
                f"Tied dogs share a rank and are listed alphabetically by registered name.")
    foot = (f"English Springer Spaniel Field Trial Association · {window} · generated {today} · "
            f"also at essfta.info")
    sports = d["sports"]
    rank = ("#", lambda r: esc(r["rank"]), "r")
    dog = ("Dog", lambda r: esc(r["dog"]), "dog")
    owner = ("Owner(s)", lambda r: esc(r["owner"]), "")
    docs = {}

    rows = [r for r in sports if r["sport"] == "Obedience"]
    docs["Obedience"] = ("portrait", page(
        f"Obedience Rankings — {window}", f"{computed} {member}",
        sport_body(rows, OBED_GROUPS, lambda c: [rank, dog, owner, ("Avg score", lambda r: fmt(r["score"]), "n")]),
        ["S lines (a run recorded a second time in a concurrent specialty's judge's book) are not counted."]
        + [title_note(d, year)],
        foot, logo))

    rows = [r for r in sports if r["sport"] == "Rally"]
    docs["Rally"] = ("portrait", page(
        f"Rally Rankings — {window}", f"{computed} Top ten per class. {member}",
        sport_body(rows, RALLY_GROUPS, lambda c: [rank, dog, owner, ("Avg score", lambda r: fmt(r["score"]), "n")]),
        [], foot, logo))

    rows = [r for r in sports if r["sport"] == "Agility"]

    def agil_cols(cat):
        if cat in ("Excellent B", "Preferred Excellent B"):
            return [rank, dog, owner, ("QQs", lambda r: esc(r["legs"]), "n"), ("Avg YPS", lambda r: fmt3(r["score2"]), "n")]
        return [rank, dog, owner, ("Qs", lambda r: esc(r["legs"]), "n"), ("Avg score", lambda r: fmt(r["score"]), "n"),
                ("Avg YPS", lambda r: fmt3(r["score2"]), "n")]
    docs["Agility"] = ("portrait", page(
        f"Agility Rankings — {window}",
        f"Computed from the AKC results exports ({qs} {year}) by the methods of the club's agility card. "
        f"Equal scores are ordered by average yards per second.",
        sport_body(rows, AGIL_GROUPS, agil_cols),
        ["YPS = course yards ÷ the dog's time; on Novice and Open Standard courses the 5-second table count "
         "is taken off the time first. In the class awards the YPS column is the average over the runs "
         "counted and breaks ties in average score. Rankings use the unrounded values, so two dogs can show "
         "the same printed figure in different places.",
         agility_title_note(d, year)],
        foot, logo))

    conf = d["conformation"]
    def cc(label, key):
        return (label, lambda r: esc(r[key]), "n")
    breed_cols = [rank, ("Dog", lambda r: esc(tc_name(r["name"])), "dog"), ("Owner(s)", lambda r: esc(tc_owner(r["owner"])), ""),
                  cc("#BOB", "bob_shows"), cc("BOB spec", "bob_spec"), cc("BOB pts", "bob_pts"),
                  cc("#BOS", "bos_shows"), cc("BOS spec", "bos_spec"), cc("BOS pts", "bos_pts"), cc("Total", "total")]
    group_cols = [rank, ("Dog", lambda r: esc(tc_name(r["name"])), "dog"), ("Owner(s)", lambda r: esc(tc_owner(r["owner"])), ""),
                  cc("BIS", "bis_n"), cc("BIS pts", "bis_pts"), cc("G1", "grp1_n"), cc("G1 pts", "grp1_pts"),
                  cc("G2", "grp2_n"), cc("G2 pts", "grp2_pts"), cc("G3", "grp3_n"), cc("G3 pts", "grp3_pts"),
                  cc("G4", "grp4_n"), cc("G4 pts", "grp4_pts"), cc("Total", "total")]
    body = []
    for sec in ("Breed - Dogs", "Breed - Bitches", "Group - Dogs", "Group - Bitches"):
        rs = [r for r in conf if r["section"] == sec]
        body.append(f'<section><h3>{esc(sec.replace(" - ", " · "))}</h3>'
                    + (table(breed_cols if sec.startswith("Breed") else group_cols, rs) if rs
                       else '<div class="empty">No qualifying entries.</div>') + "</section>")
    docs["BreedGroup"] = ("landscape", page(
        f"Breed & Group Rankings — {window}",
        f"Computed from the AKC conformation results exports ({qs} {year}). Top 15 per section, ties at 15 included.",
        "".join(body),
        ["Points: BOB = dogs defeated; BOS = same-sex dogs defeated, plus the opposite-sex Winners entry when Best "
         "of Winners went to the BOS dog's sex; Group and BIS = dogs defeated (a BIS day's group points fold into BIS). "
         "“spec” counts wins at specialties, including designated specialties held at all-breed shows "
         "(list compiled from the AKC event search by Alvin Eng)."],
        foot, logo))

    jr = d["juniors"]
    jcols = [rank, ("Junior handler", lambda r: esc(r["handler"]), "dog"), ("Shows", lambda r: esc(r["shows"]), "n"),
             ("Best Junior wins", lambda r: esc(r["best"]), "n"), ("Reserve wins", lambda r: esc(r["reserve"]), "n"),
             ("Class wins", lambda r: esc(r["class_wins"]), "n"),
             ("Total defeated", lambda r: esc(r["total_defeated"]), "n")]
    docs["Juniors"] = ("portrait", page(
        f"Juniors Standings — {window}",
        f"Computed from the AKC Junior Showmanship exports ({qs} {year}) · {len(jr)} junior handlers.",
        f"<h2>Standings by total defeated</h2>{table(jcols, jr)}",
        ["UNOFFICIAL — DRAFT. The club does not currently publish a Juniors ranking (the only one to date was Q4 2016). "
         "Total defeated counts each show once, at the handler's best result: Best Junior = entry − 1, Reserve = entry − 2, "
         "class placement p = class entry − p (Canine Chronicle's convention)."],
        foot, logo))

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        for name, (orient, doc) in docs.items():
            pg = b.new_page()
            pg.set_content(doc, wait_until="networkidle")
            out = os.path.join(qdir, f"ESSFTA_{name}_{year}_{FILE_WINDOW[quarter]}.pdf")
            pg.pdf(path=out, format="Letter", landscape=orient == "landscape", print_background=True,
                   margin={"top": "0.55in", "bottom": "0.55in", "left": "0.6in", "right": "0.6in"})
            pg.close()
            print(out)
        b.close()


if __name__ == "__main__":
    main()

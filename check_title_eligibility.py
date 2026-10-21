#!/usr/bin/env python3
"""Check a built quarter's obedience titling classes against the AKC title master.

    python3 check_title_eligibility.py 2026 Q3

Rule (SCORING-RULES.md, obedience, Betsy 9/16): a dog appears in a titling class
(Novice A/B, Open A, Utility A, Beginner Novice A/B, Graduate Novice/Open, the
Preferred classes) only in the year its title is dated, and only when all three
title legs fall in that year. Open B, Utility B and Combined are not titling classes.

Dogs are matched by AKC registration number (names grow titles through the year):
the quarter's rows (quarters/<tag>/report_data_<tag>.json) carry the dog name the
engine printed, which is mapped to a Reg Number through the raw obedience exports;
titles come from raw_akc/New Titles 2026.xlsx, sheet Cumulative.

Verdicts per listed dog:
  OK          title dated this year, and the dog's three qualifying legs in that class
              this year fall on or before the title date
  PRIOR YEAR  title dated before this year -> not eligible, remove
  OLD LEG     title dated this year but fewer than three legs this year up to the title
              date (A and B legs both count) -> a leg came from last year (the Lawman
              case), remove
  NO TITLE    three legs this year but no title on file yet; the title file runs to
              its newest date, so a third leg after that is AKC lag (keep); one before
              it needs a human look
Writes quarters/<tag>/title_check_<tag>.csv and prints the table.
"""
import collections, csv, datetime, json, os, sys

import openpyxl
import xlrd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_quarter import QUAL, clean, key_name, raw_files  # noqa: E402

TITLE_CLASS = {  # report category -> AKC title name
    "Regular: Novice A": "Companion Dog", "Regular: Novice B": "Companion Dog",
    "Regular: Open A": "Companion Dog Excellent", "Regular: Utility A": "Utility Dog",
    "Optional: Beginner Novice A": "Beginner Novice", "Optional: Beginner Novice B": "Beginner Novice",
    "Optional: Graduate Novice": "Graduate Novice", "Optional: Graduate Open": "Graduate Open",
    "Alternative: Preferred Novice": "Preferred Companion Dog",
    "Alternative: Preferred Open": "Preferred Companion Dog Excellent",
    "Alternative: Preferred Utility": "Preferred Utility Dog",
}
# raw class codes whose qualifying runs are legs toward each title (A and B both count)
TITLE_LEGS = {
    "Companion Dog": ("ONOVA", "ONOVB"), "Companion Dog Excellent": ("OOPENA", "OOPENB"),
    "Utility Dog": ("OUTILA", "OUTILB"), "Beginner Novice": ("BNOVA", "BNOVB"),
    "Graduate Novice": ("GRADNOVR",), "Graduate Open": ("GRADOPNR",),
    "Preferred Companion Dog": ("PNOV",), "Preferred Companion Dog Excellent": ("POPEN",),
    "Preferred Utility Dog": ("PUTIL",),
}
EXCLUDE = {"PRIOR YEAR", "OLD LEG"}
MASTER = os.path.join(HERE, "raw_akc", "New Titles 2026.xlsx")


def legs(year, quarter):
    out = []
    for p in raw_files("Obedience", year, quarter):
        sh = xlrd.open_workbook(p).sheet_by_index(0)
        grid = [[sh.cell_value(i, j) for j in range(sh.ncols)] for i in range(sh.nrows)]
        hi = next(i for i, r in enumerate(grid) if any(clean(c) == "Reg Number" for c in r))
        hdr = [clean(c) for c in grid[hi]]
        for r in grid[hi + 1:]:
            d = dict(zip(hdr, r))
            if not clean(d.get("Reg Number")):
                continue
            ev = d.get("Event Date")
            ev = xlrd.xldate_as_datetime(ev, 0).date() if isinstance(ev, float) else \
                datetime.datetime.strptime(clean(ev)[:10], "%m/%d/%Y").date()
            out.append({"reg": clean(d["Reg Number"]), "dog": clean(d["Dog Name"]), "date": ev,
                        "cls": clean(d["Primary Class"]), "place": clean(d["Placement"]),
                        "score": d.get("Score")})
    return out


def titles():
    wb = openpyxl.load_workbook(MASTER, read_only=True)
    out = collections.defaultdict(list)
    newest = datetime.date.min
    for r in wb["Cumulative"].iter_rows(min_row=2, values_only=True):
        if r[0] and r[5] and r[7]:
            d = r[7].date() if isinstance(r[7], datetime.datetime) else r[7]
            out[(clean(r[5]), clean(r[0]))].append(d)
            newest = max(newest, d)
    return out, newest


def verdicts(year, quarter, rows):
    """One verdict per obedience titling-class row in rows (see the module docstring)."""
    all_legs = legs(year, quarter)
    reg_of = {}
    for lg in all_legs:
        reg_of.setdefault(key_name(lg["dog"]), set()).add(lg["reg"])
    tmap, newest = titles()
    y = int(year)
    report = []
    for r in rows:
        if r["sport"] != "Obedience" or r["category"] not in TITLE_CLASS:
            continue
        tname = TITLE_CLASS[r["category"]]
        regs = reg_of.get(key_name(r["dog"]), set())
        if len(regs) != 1:
            raise SystemExit(f"cannot match {r['dog']} to one Reg Number: {regs}")
        reg = next(iter(regs))
        q = sorted(lg["date"] for lg in all_legs
                   if lg["reg"] == reg and lg["cls"] in TITLE_LEGS[tname] and lg["place"] in QUAL)
        dates = sorted(tmap.get((reg, tname), []))
        tdate = dates[-1] if dates else None
        if tdate is None:
            verdict = "NO TITLE" + (" (AKC lag)" if q[2] > newest else " (check)")
        elif tdate.year < y:
            verdict = "PRIOR YEAR"
        elif len([d for d in q if d <= tdate]) < 3:
            verdict = "OLD LEG"
        else:
            verdict = "OK"
        report.append({"category": r["category"], "rank": r["rank"], "dog": r["dog"], "reg": reg,
                       "title": tname, "title_date": str(tdate or ""), "legs_this_year": len(q),
                       "legs_by_title_date": len([d for d in q if tdate and d <= tdate]),
                       "verdict": verdict})
    return report, newest


def main():
    year, quarter = sys.argv[1], sys.argv[2].upper()
    tag = f"{year}{quarter}"
    qdir = os.path.join(HERE, "quarters", tag)
    data = json.load(open(os.path.join(qdir, f"report_data_{tag}.json")))
    # check what was computed, including any rows the build already removed
    rows = data["sports"] + data.get("title_removed", [])
    report, newest = verdicts(year, quarter, rows)
    out = os.path.join(qdir, f"title_check_{tag}.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(report[0].keys()))
        w.writeheader()
        w.writerows(report)
    print(f"title master newest date: {newest}")
    for x in report:
        print(f"{x['verdict']:18} {x['category'][-22:]:22} #{x['rank']:<3} {x['dog'][:44]:44} {x['reg']:11} "
              f"{x['title']:24} titled {x['title_date']:10}  legs {x['legs_this_year']} "
              f"by title date {x['legs_by_title_date']}")
    print(collections.Counter(x["verdict"] for x in report))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()

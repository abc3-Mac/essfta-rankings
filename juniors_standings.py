#!/usr/bin/env python3
"""ESSFTA Juniors quarterly standings from raw AKC Junior Showmanship exports.

Methodology (validated 2026-09-14 against Canine Chronicle's Juniors Breed Top 10
for ESS — the same source the club's one published Juniors quarterly, Q4 2016,
reprinted; the club's annual-awards page states the same points idea):

  Total Defeated (the ranking metric) — per EVENT, the handler's single best
  credit (no double counting a class win and the BJH win at the same show):
      BJH row:            Num Competing - 1   (Num Competing on BJH/RBJH rows
      RBJH row:           Num Competing - 2    is the show's TOTAL junior entry)
      class placement p:  Num Competing - p   (class-size scope)
  Win counts (display columns, Canine Chronicle conventions):
      Best Junior wins:   BJH rows with Num Competing > 1 (uncontested excluded)
      Reserve wins:       RBJH rows (CC counts these even at 2-entry shows)
      Class wins:         placement-1 rows with Num Competing > 1

Validation: with Jan-Jun 2026 data vs CC's Jan-Jul table, handlers with no July
activity match EXACTLY (Halfacre 152, Kritzer 146 + all their win counts); all
others run at or below CC's totals, as they must. The additive (per-row) reading
overshoots CC and is therefore wrong.

Inputs: the per-quarter raw files (concatenate quarters - they are windows, not
cumulative). Reads the CSV extracts by default; point RAW1/RAW2 elsewhere as needed.
"""
import csv, collections, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = [os.path.join(HERE, "raw_akc/audit_2026Q2/raw_inspect", f) for f in
       ("ESS_Juniors_1Q_2026__Sheet_1.csv", "ESS_Juniors_2Q_2026__Sheet_1.csv")]

def clean(x): return str(x).replace("\xa0", " ").strip()
def num(x):
    try: return int(float(str(x)))
    except: return 0

def standings(paths):
    rows = []
    for p in paths:
        rows += list(csv.DictReader(open(p, encoding="utf-8")))
    H = collections.defaultdict(lambda: {"events": set(), "best": 0, "reserve": 0,
                                         "clswins": 0, "evcredit": {}})
    for r in rows:
        h = clean(r["Jr Handler Name"]); rc = clean(r["Result Code"])
        nc = num(r["Num Competing"]); ev = clean(r["Event Number"])
        d = H[h]; d["events"].add(ev)
        if rc == "BJH":
            credit = max(nc - 1, 0)
            if nc > 1: d["best"] += 1
        elif rc == "RBJH":
            credit = max(nc - 2, 0)
            d["reserve"] += 1
        elif rc.isdigit():
            credit = max(nc - int(rc), 0)
            if rc == "1" and nc > 1: d["clswins"] += 1
        else:
            continue
        d["evcredit"][ev] = max(d["evcredit"].get(ev, 0), credit)
    out = []
    for h, d in H.items():
        out.append({"handler": h, "shows": len(d["events"]), "best": d["best"],
                    "reserve": d["reserve"], "class_wins": d["clswins"],
                    "total_defeated": sum(d["evcredit"].values())})
    out.sort(key=lambda r: -r["total_defeated"])
    return out

if __name__ == "__main__":
    st = standings(RAW)
    print(f"{'#':>3} {'Junior Handler':26} {'Shows':>5} {'Best':>5} {'Res':>4} {'ClsW':>5} {'Defeated':>9}")
    for i, r in enumerate(st, 1):
        print(f"{i:>3} {r['handler']:26} {r['shows']:>5} {r['best']:>5} {r['reserve']:>4} "
              f"{r['class_wins']:>5} {r['total_defeated']:>9}")
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(st[0].keys())); w.writeheader()
            for r in st: w.writerow(r)
        print(f"\nwrote {sys.argv[1]}")

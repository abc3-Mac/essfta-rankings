#!/usr/bin/env python3
"""Build one cumulative quarter (e.g. 2026 Q3 = Jan 1 - Sep 30) from the raw AKC
per-quarter exports in raw_akc/, in the canonical shapes the archive and the
essfta.info rankings importer take:

  quarters/<YYYY>Q<n>/sports_<YYYY>Q<n>.json        Obedience / Rally / Agility rows (sports.json schema)
  quarters/<YYYY>Q<n>/conformation_<YYYY>Q<n>.json  Breed/Group rows (breed_group.json schema)
  quarters/<YYYY>Q<n>/juniors_<YYYY>Q<n>.csv        Junior Showmanship standings (no archive table yet)

Sources and rules (all validated against published cards — see SCORING-RULES.md):
  Obedience, Rally  the rankings calculator engine (rankings_calculator.html) driven
                    headlessly; final club rules of 16 Sept 2026 (no S lines, best 3,
                    shared ranks, ties alphabetical by registered name). Rally cards
                    list the top 10 per class (ties at 10 kept); obedience lists all.
  Agility           Patty's card methods (reproduced her Q2 sheet exactly):
                      Excellent B / Preferred Excellent B = avg YPS of the fastest 10 QQs (>= 10 QQs)
                      Novice, Open, Excellent A (+ Preferred) = avg of the six title legs: the
                        3 STD + 3 JWW legs that earned this year's two titles, all run this year
                        (AKC title master; Linda, 21 Oct 2026)
                    YPS = yards / time; Novice and Open Standard subtract the 5-second table
                    count from the time. Ranked at full precision; every speed prints three
                    decimals; score ties broken by avg YPS.
  Conformation      compute_conformation.py (top 15 per section, ties at 15 kept); #Spec
                    includes designated specialties, listed from the AKC event search by
                    fetch_designated_specialties.py (run automatically when the list does
                    not yet reach the quarter's end).
  Juniors           juniors_standings.py (Total Defeated, Canine Chronicle convention).

CLI:  python3 build_quarter.py 2026 Q3            build the quarter
      python3 build_quarter.py 2026 Q2 --check    rebuild a published quarter and diff it
                                                  against the essfta.info platform copy
"""
import collections, csv, datetime, json, os, re, sqlite3, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw_akc")
PLATFORM_DB = os.path.expanduser("~/Developer/essfta-platform/data/platform.db")
sys.path.insert(0, HERE)

QUAL = {"QLFY", "1", "2", "3", "4"}


def clean(x):
    return " ".join(str(x if x is not None else "").replace("\xa0", " ").split())


def raw_files(sport, year, quarter):
    n = int(quarter[1])
    out = []
    for q in range(1, n + 1):
        for ext in (".xls", ".xlsx"):
            p = os.path.join(RAW, f"ESS {sport} {q}Q {year}{ext}")
            if os.path.exists(p):
                out.append(p)
                break
        else:
            raise SystemExit(f"missing raw file: ESS {sport} {q}Q {year}")
    return out


def rank_rows(rows, key):
    """Competition ranking on key(row); equal keys share a rank, later ones carry tie 'T'."""
    prev, rank = object(), 0
    for i, r in enumerate(rows, 1):
        k = key(r)
        if k != prev:
            rank, tie = i, ""
        else:
            tie = "T"
        r["rank"], r["tie"], prev = rank, tie, k
    return rows


# ------------------------------------------------------------ obedience + rally
OBED_LABEL = {
    "Beginner Novice A": "Optional: Beginner Novice A", "Beginner Novice B": "Optional: Beginner Novice B",
    "Graduate Novice": "Optional: Graduate Novice", "Graduate Open": "Optional: Graduate Open",
    "Versatility": "Optional: Versatility",
    "Preferred Novice": "Alternative: Preferred Novice", "Preferred Open": "Alternative: Preferred Open",
    "Preferred Utility": "Alternative: Preferred Utility",
}


def run_engine(year, quarter):
    from playwright.sync_api import sync_playwright
    files = [f for s in ("Obedience", "Rally") for f in raw_files(s, year, quarter)]
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page()
        page.goto(f"file://{HERE}/rankings_calculator.html")
        page.wait_for_function("typeof XLSX!=='undefined'")
        page.set_input_files("#ecInput", files)
        page.wait_for_function("Object.keys(DATA).length===2", timeout=30000)
        data, meta = page.evaluate("DATA"), page.evaluate("META")
        b.close()
    return data, meta


def engine_rows(data, year, quarter):
    out = []
    for sport in ("Obedience", "Rally"):
        for cat, rows in data[sport].items():
            label = OBED_LABEL.get(cat, f"Regular: {cat}") if sport == "Obedience" else cat
            rows = [dict(r) for r in rows]
            # the engine's order is final (score, then registered name); rank by score
            rank_rows(rows, key=lambda r: r["score"])
            if sport == "Rally":
                rows = [r for r in rows if r["rank"] <= 10]
            for r in rows:
                out.append({"sport": sport, "year": str(year), "quarter": quarter, "category": label,
                            "rank": r["rank"], "tie": r["tie"], "dog": clean(r["dog"]),
                            "owner": clean(r["owner"]), "score": r["score"], "score2": "",
                            "legs": r.get("legs", "")})
    return out


# ---------------------------------------------------------------------- agility
def read_agility(paths):
    import xlrd
    rows, order = [], 0
    for p in paths:
        sh = xlrd.open_workbook(p).sheet_by_index(0)
        grid = [[sh.cell_value(i, j) for j in range(sh.ncols)] for i in range(sh.nrows)]
        hi = next(i for i, r in enumerate(grid) if any(clean(c) == "Reg Number" for c in r))
        hdr = [clean(c) for c in grid[hi]]
        for r in grid[hi + 1:]:
            d = dict(zip(hdr, r))
            if not clean(d.get("Reg Number")):
                continue
            ev = d.get("Event Date")
            if isinstance(ev, float):
                ev = xlrd.xldate_as_datetime(ev, 0).date().isoformat()
            order += 1
            owners = [clean(d.get(k)) for k in ("Primary Owner Name", "2nd Owner", "3rd Owner", "4th Owner")]
            rows.append({"reg": clean(d["Reg Number"]), "dog": clean(d["Dog Name"]),
                         "owner": ",".join(o for o in owners if o), "date": str(ev)[:10],
                         "event": clean(d["Event Name"]), "cls": clean(d["Primary Class"]),
                         "place": clean(d["Placement"]), "score": d.get("Score"),
                         "dist": d.get("Course Distance"), "time": d.get("Dog Time"), "order": order})
    return rows


# Novice and Open Standard courses (and their Preferred classes) have a table; the AKC time
# includes its 5-second count, so speed = course yards / (dog's time - 5). Excellent Standard
# has no table any more and Jumpers never has one: yards / time. (Linda, 21 Oct 2026.)
TABLE_CLASSES = {"AGNOVA", "AGNOVB", "AGNOVP", "AGOPEN", "AGOPENP"}
TABLE_COUNT = 5.0


def _yps(r):
    try:
        t = float(r["time"]) - (TABLE_COUNT if r["cls"] in TABLE_CLASSES else 0.0)
        return float(r["dist"]) / t if t > 0 else None
    except (TypeError, ValueError, ZeroDivisionError):
        return None


# Title-year rule for the agility titling classes (Linda, 21 Oct 2026): a dog is ranked only
# when both the Standard and the Jumpers title are dated this year and all six legs that earned
# them were run this year; only those six legs count. Excellent B and Preferred Excellent B are
# exempt. Titles come from the AKC title master (raw_akc/New Titles <year>.xlsx, Cumulative).
AG_TITLES = {  # category -> ((Standard title, leg classes), (Jumpers title, leg classes))
    "Novice": (("Novice Agility", ("AGNOVA", "AGNOVB")), ("Novice Agility Jumper", ("JWWNOVA", "JWWNOVB"))),
    "Open": (("Open Agility", ("AGOPEN",)), ("Open Agility Jumper", ("JWWOPEN",))),
    "Excellent A": (("Agility Excellent", ("AGEXCA",)), ("Excellent Agility Jumper", ("JWWEXCA",))),
    "Preferred Novice": (("Novice Agility Preferred", ("AGNOVP",)),
                         ("Novice Agility Jumper Preferred", ("JWWNOVP",))),
    "Preferred Open": (("Open Agility Preferred", ("AGOPENP",)), ("Open Agility Jumper Preferred", ("JWWOPENP",))),
    "Preferred Excellent A": (("Agility Excellent Preferred", ("AGEXCAP",)),
                              ("Excellent Agility Jumper Preferred", ("JWWEXCAP",))),
}
AG_EXCLUDE = {"OLD LEG", "PRIOR YEAR"}


def _title_legs(runs, classes, tdates, year, newest):
    """The three legs that earned one title, and a verdict.

    runs: this year's qualifying runs for one dog, oldest first. Returns (legs or None, verdict,
    title date). OK = title dated this year with three legs this year on or before it (the three
    latest are used); OLD LEG = title dated this year but a leg came from an earlier year;
    PRIOR YEAR = title earned before this year; NO TITLE = three legs this year but no title on
    the AKC file yet (AKC lag when the third leg is newer than the file; kept, flagged).
    """
    q = [r for r in runs if r["cls"] in classes]
    if len(q) < 3:
        return None, "UNDER 3", None
    this = sorted(d for d in tdates if d.year == year)
    if this:
        tdate = this[-1]
        upto = [r for r in q if datetime.date.fromisoformat(r["date"]) <= tdate]
        if len(upto) < 3:
            return None, "OLD LEG", tdate
        return upto[-3:], ("OK" if len(upto) == 3 else f"CHECK ({len(upto)} legs by title date)"), tdate
    if tdates:
        return None, "PRIOR YEAR", max(tdates)
    third = datetime.date.fromisoformat(q[2]["date"])
    return q[:3], ("NO TITLE (AKC lag)" if third > newest else "NO TITLE (check)"), None


def agility_rows(year, quarter, log=None):
    """Agility rankings. log, when a dict, receives 'removed' and 'flagged' title-rule verdicts."""
    from check_title_eligibility import titles
    tmap, newest = titles()
    y = int(year)
    removed, flagged = [], []
    runs = [r for r in read_agility(raw_files("Agility", year, quarter)) if r["place"] in QUAL]
    by_dog = collections.defaultdict(list)
    for r in runs:
        by_dog[r["reg"]].append(r)
    latest = {reg: max(rs, key=lambda r: (r["date"], r["order"])) for reg, rs in by_dog.items()}

    def fmt(x):
        return f"{x:.2f}"

    out = []

    def emit(cat, entries, yps_ranked):
        # Ranked on the full-precision values (Linda, 21 Oct 2026: two Excellent B dogs both
        # print 3.84 but differ by 0.005); every agility speed prints three decimals.
        if yps_ranked:
            entries.sort(key=lambda e: (-e["yps"], e["dog"]))
            rank_rows(entries, key=lambda e: e["yps"])
        else:
            entries.sort(key=lambda e: (-e["score"], -e["yps"], e["dog"]))
            rank_rows(entries, key=lambda e: (e["score"], e["yps"]))
        for e in entries:
            out.append({"sport": "Agility", "year": str(year), "quarter": quarter, "category": cat,
                        "rank": e["rank"], "tie": e["tie"], "dog": e["dog"], "owner": e["owner"],
                        "score": "" if yps_ranked else fmt(e["score"]),
                        "score2": f"{e['yps']:.3f}",
                        "legs": e["legs"]})

    # Excellent B / Preferred Excellent B: QQ = Q in both STD and JWW the same day
    for cat, std, jww in (("Excellent B", "AGEXCB", "JWWEXCB"), ("Preferred Excellent B", "AGEXCBP", "JWWEXCBP")):
        entries = []
        for reg, rs in by_dog.items():
            days = collections.defaultdict(lambda: {"s": [], "j": []})
            for r in rs:
                if r["cls"] == std:
                    days[r["date"]]["s"].append(_yps(r))
                elif r["cls"] == jww:
                    days[r["date"]]["j"].append(_yps(r))
            qq = []
            for d in days.values():
                for s, j in zip(sorted(d["s"], reverse=True), sorted(d["j"], reverse=True)):
                    qq.append((s + j) / 2)
            if len(qq) >= 10:
                qq.sort(reverse=True)
                entries.append({"dog": latest[reg]["dog"], "owner": latest[reg]["owner"],
                                "yps": sum(qq[:10]) / 10, "legs": len(qq)})
        emit(cat, entries, True)

    # titling classes: the three Standard + three Jumpers legs that earned this year's titles
    for cat in ("Novice", "Open", "Preferred Novice", "Preferred Open", "Excellent A", "Preferred Excellent A"):
        (stitle, scls), (jtitle, jcls) = AG_TITLES[cat]
        entries = []
        for reg, rs in by_dog.items():
            rs = sorted(rs, key=lambda r: (r["date"], r["order"]))
            s_legs, s_v, s_d = _title_legs(rs, scls, tmap.get((reg, stitle), []), y, newest)
            j_legs, j_v, j_d = _title_legs(rs, jcls, tmap.get((reg, jtitle), []), y, newest)
            if "UNDER 3" in (s_v, j_v):
                continue                      # not yet three and three: never listed
            note = {"sport": "Agility", "category": cat, "dog": latest[reg]["dog"], "reg": reg,
                    "std": {"title": stitle, "date": str(s_d or ""), "verdict": s_v},
                    "jww": {"title": jtitle, "date": str(j_d or ""), "verdict": j_v}}
            if s_v in AG_EXCLUDE or j_v in AG_EXCLUDE:
                removed.append(note)
                continue
            if s_v != "OK" or j_v != "OK":
                flagged.append(note)
            legs = s_legs + j_legs
            entries.append({"dog": latest[reg]["dog"], "owner": latest[reg]["owner"],
                            "score": sum(float(r["score"]) for r in legs) / 6,
                            "yps": sum(_yps(r) for r in legs) / 6, "legs": 6})
        emit(cat, entries, False)
    if isinstance(log, dict):
        log["removed"], log["flagged"] = removed, flagged
    for n in removed:
        print(f"agility title rule: removed {n['dog']} from {n['category']} "
              f"(Standard {n['std']['verdict']}, Jumpers {n['jww']['verdict']})")
    for n in flagged:
        print(f"agility title rule: flagged {n['dog']} in {n['category']} "
              f"(Standard {n['std']['verdict']}, Jumpers {n['jww']['verdict']})")
    return out


# ----------------------------------------------------------------- conformation
QUARTER_END = {"Q1": "03-31", "Q2": "06-30", "Q3": "09-30", "Q4": "12-31"}


def ensure_designated_specialties(year, quarter):
    """Make sure raw_akc/designated_specialties_<year>.csv covers the quarter: its
    '# fetched ... events through <date>' line must reach the quarter's end, otherwise
    fetch_designated_specialties.py refreshes it from the AKC event search."""
    import subprocess
    end = f"{year}-{QUARTER_END[quarter]}"
    path = os.path.join(RAW, f"designated_specialties_{year}.csv")
    covered = ""
    if os.path.exists(path):
        m = re.search(r"events through (\d{4}-\d{2}-\d{2})", open(path, encoding="utf-8-sig").read())
        covered = m.group(1) if m else ""
    if covered >= end:
        return
    print(f"designated specialties: list covers {covered or 'nothing'}, quarter ends {end} - fetching from AKC")
    subprocess.run([sys.executable, os.path.join(HERE, "fetch_designated_specialties.py"), year,
                    "--through", end], check=True)


def conformation_rows(year, quarter):
    from updater.engine.adapters import conformation_from_xls
    ensure_designated_specialties(year, quarter)
    return conformation_from_xls(raw_files("Conformation", year, quarter), year, quarter)


# ---------------------------------------------------------------------- juniors
def juniors_rows(year, quarter):
    import juniors_standings
    from compute_conformation import read_raw
    tmp = []
    for p in raw_files("Juniors", year, quarter):
        rows = read_raw(p)
        f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="", encoding="utf-8")
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
        f.close()
        tmp.append(f.name)
    st = juniors_standings.standings(tmp)
    for t in tmp:
        os.unlink(t)
    st.sort(key=lambda r: (-r["total_defeated"], r["handler"]))
    return rank_rows(st, key=lambda r: r["total_defeated"])


# ------------------------------------------------------------------------ check
def check_against_platform(year, quarter, sports, conf):
    """Diff the rebuilt quarter against the platform's published copy."""
    con = sqlite3.connect(PLATFORM_DB)
    from compute_conformation import core_name

    def key_name(dog):
        # titles are the all-caps / digit tokens; the registered name is mixed case
        words = [w for w in re.split(r"[\s/]+", str(dog).replace("\u2019", "'"))
                 if w and not (w.isupper() and len(w) > 1) and not re.search(r"\d", w)]
        return re.sub(r"[^a-z]", "", " ".join(words).lower())[:24]
    lines = []
    pub = collections.defaultdict(dict)
    for sp, cat, dog, score, score2 in con.execute(
            "select sport,category,dog,score,score2 from rankings_sports where year=? and quarter=?",
            (str(year), quarter)):
        pub[(sp, cat)][key_name(dog)] = (score, score2)
    mine = collections.defaultdict(dict)
    for r in sports:
        mine[(r["sport"], r["category"])][key_name(r["dog"])] = (r["score"], r["score2"])
    for key in sorted(set(pub) | set(mine)):
        a, b = pub.get(key, {}), mine.get(key, {})
        same = 0
        for d in sorted(set(a) | set(b)):
            pa, pb = a.get(d), b.get(d)
            if pa and pb and all((not x and not y) or (x and y and abs(float(x) - float(y)) < 0.006)
                                 for x, y in zip(pa, pb)):
                same += 1
            else:
                lines.append(f"  {key[0]} / {key[1]}: {d[:50]:50}  published={pa}  computed={pb}")
        print(f"{key[0]:10} {key[1]:38} published {len(a):3}  computed {len(b):3}  same {same}")
    print("\n".join(lines) or "  no sports differences")
    n = 0
    for sec, dog, total in con.execute(
            "select section,name,total from rankings_conformation where year=? and quarter=?", (str(year), quarter)):
        m = [r for r in conf if r["section"] == sec and core_name(r["name"]) == core_name(dog)]
        if not m or str(m[0]["total"]) != str(total):
            n += 1
            print(f"  conformation {sec}: {dog}  published total {total}  computed {m[0]['total'] if m else None}")
    print(f"conformation: {n} total mismatches")


def key_name(dog):
    """Registered name without titles: titles are the all-caps / digit tokens."""
    words = [w for w in re.split(r"[\s/]+", str(dog).replace("\u2019", "'"))
             if w and not (w.isupper() and len(w) > 1) and not re.search(r"\d", w)]
    return re.sub(r"[^a-z]", "", " ".join(words).lower())


def latest_names(rows):
    """One dog, one name: titles only accumulate, so the longest title string is the newest."""
    best = {}
    for r in rows:
        k = key_name(r["dog"])
        if len(r["dog"]) > len(best.get(k, "")):
            best[k] = r["dog"]
    for r in rows:
        r["dog"] = best[key_name(r["dog"])]
    return rows


def apply_title_rule(sports, year, quarter):
    """Obedience titling classes list a dog only in the year its title is dated, with all
    three title legs that year (check_title_eligibility.py). Removes the rows that fail,
    re-ranks those classes, and returns (rows, removed, flagged-for-a-human)."""
    from check_title_eligibility import EXCLUDE, verdicts
    report, _ = verdicts(year, quarter, sports)
    bad = {(v["category"], v["dog"]): v for v in report if v["verdict"] in EXCLUDE}
    flagged = [v for v in report if v["verdict"] not in EXCLUDE and v["verdict"] != "OK"]
    removed = [dict(r, title_verdict=bad[(r["category"], r["dog"])]) for r in sports
               if (r["category"], r["dog"]) in bad]
    keep = [r for r in sports if (r["category"], r["dog"]) not in bad]
    for cat in {r["category"] for r in removed}:
        rank_rows([r for r in keep if r["sport"] == "Obedience" and r["category"] == cat],
                  key=lambda r: r["score"])
    for r in removed:
        print(f"title rule: removed {r['dog']} from {r['category']} ({r['title_verdict']['verdict']})")
    for v in flagged:
        print(f"title rule: flagged {v['dog']} in {v['category']} ({v['verdict']})")
    return keep, removed, flagged


def main():
    year, quarter = sys.argv[1], sys.argv[2].upper()
    data, meta = run_engine(year, quarter)
    ag_log = {}
    sports = latest_names(engine_rows(data, year, quarter)) + agility_rows(year, quarter, ag_log)
    sports, removed, flagged = apply_title_rule(sports, year, quarter)
    conf = conformation_rows(year, quarter)
    juniors = juniors_rows(year, quarter)
    if "--check" in sys.argv:
        check_against_platform(year, quarter, sports, conf)
        return
    outdir = os.path.join(HERE, "quarters", f"{year}{quarter}")
    os.makedirs(outdir, exist_ok=True)
    tag = f"{year}{quarter}"
    json.dump([{k: v for k, v in r.items() if k != "legs"} for r in sports],
              open(os.path.join(outdir, f"sports_{tag}.json"), "w"), indent=1, ensure_ascii=False)
    json.dump(conf, open(os.path.join(outdir, f"conformation_{tag}.json"), "w"), indent=1, ensure_ascii=False)
    with open(os.path.join(outdir, f"juniors_{tag}.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(juniors[0].keys()))
        w.writeheader()
        w.writerows(juniors)
    # full rows with leg counts, for the PDF reports
    json.dump({"generated": datetime.datetime.now().isoformat(timespec="seconds"), "meta": meta,
               "sports": sports, "conformation": conf, "juniors": juniors,
               "title_removed": removed, "title_flagged": flagged,
               "agility_title_removed": ag_log.get("removed", []),
               "agility_title_flagged": ag_log.get("flagged", [])},
              open(os.path.join(outdir, f"report_data_{tag}.json"), "w"), indent=1, ensure_ascii=False)
    c = collections.Counter(r["sport"] for r in sports)
    print(f"{tag}: sports {dict(c)}, conformation {len(conf)}, juniors {len(juniors)} -> {outdir}")


if __name__ == "__main__":
    main()

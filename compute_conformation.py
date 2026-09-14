#!/usr/bin/env python3
"""Compute ESSFTA conformation quarterly-report rows from raw AKC per-result
exports ("ESS Conformation NQ YYYY.xls/.xlsx" — the AKC Electronic Report).

Rules validated cell-by-cell against the published 2026 Q1 and Jan–Jun reports
(805 cells, all four sections exact; see comparison_Q2_2026.md):
  #BOB / #BOS  = counts of (BOB,BOB) / (BOB,OS) result rows
  BOB Pts      = sum of Dogs Defeated over (BOB,BOB) rows (NOT Grand Champion Points)
  BOS Pts      = sum over (BOB,OS) rows of Same Sex Dogs Defeated
                 + opposite-sex Winners-class size IF Best of Winners went to the
                   BOS dog's own sex (the BW defeat-chain credit — the club's
                   published rule, per englishspringerspaniels.org/annual-awards)
  Group pts    = Dogs Defeated on BISPRT/GRP1-4 rows, except a BIS-winning day's
                 group points fold into the BIS points (subtracted from GRPn,
                 the placement still counted)
  BIS Pts      = Dogs Defeated on (BIS,BIS) rows
  #Spec        = Competition Type S or PS. KNOWN LIMIT: the club also counts
                 club-designated supported entries at all-breed shows, which are
                 not derivable from the AKC export — those cells can undercount
                 until the club's supported-entry list is available.
  Sex M/F splits the Dogs/Bitches sections; OH (BOBOH) and Bred-By/Puppy series
  are excluded (their result codes never match the ones tallied here).

RAW FILES ARE PER-QUARTER WINDOWS, not cumulative: a Jan–Jun report needs the
1Q AND 2Q files concatenated. Pass every relevant quarter's rows to
compute_canonical() (the updater adapter does this).

CLI:  python3 compute_conformation.py  — validates the computer against the
repo's published data: breed_group.json 2026 Q1 rows (from the 1Q raw file) and
an in-memory parse of pdfs/2026-Conformation-Q2.pdf (from 1Q+2Q concatenated).
Expected: zero cell diffs outside the *_spec columns.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))

BREED_COLS = ["bob_shows", "bob_spec", "bob_pts", "bos_shows", "bos_spec", "bos_pts", "total"]
GROUP_COLS = ["bis_n", "bis_pts", "grp1_n", "grp1_pts", "grp2_n", "grp2_pts",
              "grp3_n", "grp3_pts", "grp4_n", "grp4_pts", "total"]
SECTIONS = ["Breed - Dogs", "Breed - Bitches", "Group - Dogs", "Group - Bitches"]


def num(x):
    try:
        return int(float(str(x).replace(",", "")))
    except (ValueError, TypeError):
        return 0


def _cell(v):
    if v is None:
        return ""
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v).strip()


def read_raw(path):
    """One raw AKC conformation export (.xls or .xlsx) -> list of row dicts.

    The header row is located by its 'Dog Reg Num' cell (the files carry a
    few title/date-range rows above it); every cell is normalized to str.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext == ".xls":
        import xlrd
        wb = xlrd.open_workbook(path)
        sh = wb.sheet_by_index(0)
        grid = [[sh.cell_value(i, j) for j in range(sh.ncols)] for i in range(sh.nrows)]
    else:
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        grid = [list(row) for row in wb.worksheets[0].iter_rows(values_only=True)]
        wb.close()
    hdr_i = None
    for i, row in enumerate(grid):
        if any(_cell(c) == "Dog Reg Num" for c in row):
            hdr_i = i
            break
    if hdr_i is None:
        raise ValueError(f"no 'Dog Reg Num' header row in {os.path.basename(path)} — not an AKC conformation export?")
    hdr = [_cell(c) for c in grid[hdr_i]]
    rows = []
    for r in grid[hdr_i + 1:]:
        d = {h: _cell(r[j]) if j < len(r) else "" for j, h in enumerate(hdr) if h}
        if d.get("Dog Reg Num", ""):
            rows.append(d)
    return rows


def aggregate(rows, spec_types=("S", "PS")):
    """Raw result rows -> per-dog tallies (the validated rules above)."""
    win_ncls, bw_sex, bis_events = {}, {}, set()
    for r in rows:
        ev = r["Event Number"]
        if r["Comp Primary Class"] == "WIN" and r["Result Code"] == "WIN":
            win_ncls[(ev, r["Sex"])] = num(r["Number in Class Same Sex"])
        if r["Comp Primary Class"] == "BOB" and r["Result Code"] == "BW":
            bw_sex[ev] = r["Sex"]
        if r["Comp Primary Class"] == "BIS" and r["Result Code"] == "BIS":
            bis_events.add((r["Dog Reg Num"], ev))
    dogs = {}
    for r in rows:
        reg = r["Dog Reg Num"]
        if not reg:
            continue
        d = dogs.setdefault(reg, {
            "name": "", "owner": "", "sex": r["Sex"],
            "bob_n": 0, "bob_spec": 0, "bob_pts": 0,
            "bos_n": 0, "bos_spec": 0, "bos_pts": 0,
            "bis_n": 0, "bis_pts": 0,
            "grp": {i: [0, 0] for i in (1, 2, 3, 4)},   # n, pts
        })
        # keep the longest name/owner seen (titles accrue over the year)
        if len(r["Dog Name"]) >= len(d["name"]):
            d["name"] = r["Dog Name"]
        if r["Owner(s)"] and len(r["Owner(s)"]) >= len(d["owner"]):
            d["owner"] = r["Owner(s)"]
        cls, res = r["Comp Primary Class"], r["Result Code"]
        dd = num(r["Dogs Defeated"])
        spec = r["Competition Type"] in spec_types
        if cls == "BOB" and res == "BOB":
            d["bob_n"] += 1
            d["bob_pts"] += dd
            if spec:
                d["bob_spec"] += 1
        elif cls == "BOB" and res == "OS":
            sex = r["Sex"]
            opp = "F" if sex == "M" else "M"
            add = win_ncls.get((r["Event Number"], opp), 0) if bw_sex.get(r["Event Number"]) == sex else 0
            d["bos_n"] += 1
            d["bos_pts"] += num(r["Same Sex Dogs Defeated"]) + add
            if spec:
                d["bos_spec"] += 1
        elif cls == "BISPRT" and re.fullmatch(r"GRP[1-4]", res):
            i = int(res[-1])
            d["grp"][i][0] += 1
            if (reg, r["Event Number"]) not in bis_events:   # BIS day: group pts fold into BIS pts
                d["grp"][i][1] += dd
        elif cls == "BIS" and res == "BIS":
            d["bis_n"] += 1
            d["bis_pts"] += dd
    return dogs


def _rank(rows):
    prev, rk = None, 0
    for i, r in enumerate(rows, 1):
        if r["total"] == prev:
            r["rank"], r["tie"] = rk, "T"
        else:
            r["rank"], r["tie"], rk = i, "", i
        prev = r["total"]
    return rows


def breed_rows(dogs, sex):
    out = []
    for d in dogs.values():
        if d["sex"] != sex:
            continue
        tot = d["bob_pts"] + d["bos_pts"]
        if tot <= 0:
            continue
        out.append({"name": d["name"], "owner": d["owner"],
                    "bob_shows": d["bob_n"], "bob_spec": d["bob_spec"], "bob_pts": d["bob_pts"],
                    "bos_shows": d["bos_n"], "bos_spec": d["bos_spec"], "bos_pts": d["bos_pts"],
                    "total": tot})
    out.sort(key=lambda r: -r["total"])
    return _rank(out)


def group_rows(dogs, sex):
    out = []
    for d in dogs.values():
        if d["sex"] != sex:
            continue
        gp = d["grp"]
        tot = d["bis_pts"] + sum(gp[i][1] for i in gp)
        npl = d["bis_n"] + sum(gp[i][0] for i in gp)
        if npl <= 0:
            continue
        row = {"name": d["name"], "owner": d["owner"],
               "bis_n": d["bis_n"], "bis_pts": d["bis_pts"], "total": tot}
        for i in (1, 2, 3, 4):
            row[f"grp{i}_n"], row[f"grp{i}_pts"] = gp[i]
        out.append(row)
    out.sort(key=lambda r: -r["total"])
    return _rank(out)


def compute_canonical(rows, year, quarter, spec_types=("S", "PS"), top_n=15):
    """Concatenated raw rows -> canonical conformation rows (breed_group.json
    schema: str stats, ALL-CAPS names/owners like the PDF parser emits;
    dataprep.py Title-Cases at build time).

    top_n: the published reports list the top 15 per section, ties at the
    cutoff included (historically up to 16 rows) — matched here by keeping
    every row with rank <= top_n. Pass None for the full standings."""
    dogs = aggregate(rows, spec_types=spec_types)
    out = []
    for sec, rws, cols in (("Breed - Dogs", breed_rows(dogs, "M"), BREED_COLS),
                           ("Breed - Bitches", breed_rows(dogs, "F"), BREED_COLS),
                           ("Group - Dogs", group_rows(dogs, "M"), GROUP_COLS),
                           ("Group - Bitches", group_rows(dogs, "F"), GROUP_COLS)):
        if top_n is not None:
            rws = [r for r in rws if r["rank"] <= top_n]
        for r in rws:
            out.append({"year": str(year), "quarter": quarter, "section": sec,
                        "rank": r["rank"], "tie": r["tie"],
                        "name": r["name"].upper(), "owner": r["owner"].upper(),
                        **{k: str(r[k]) for k in cols}})
    return out


# ------------------------------------------------------------------ validation
_TITLE_TOK = set("""CH GCH GCHB GCHS GCHG GCHP DC AFC FC NAFC OTCH MACH PACH AGCH RACH VCCH
CD CDX UD UDX BN GN GO RN RA RE RM RI NA NAJ OA OAJ AX AXJ MX MXJ XF NF OF JH SH MH
FDC CGC CGCA CGCU TKN TKI TKA TKE TKP ATT BCAT DCAT FCAT CA CAX ACT1 ACT2 ACT1J ACT2J
SWN SWA SWE SCN SCA SCE SEN SEA SEE SIN SIA SIE SBN SHDN RATN RATO RATS DS DSA DJ DN DM
STR OHP OHG VHMP VSWB VSWE FITB FITS FITG FTN FTI FTR HT PT NAP NJP OAP OJP AXP AJP T2B
BM SEM SBM PCD PUD VER TD TDX THD THDN""".split())


def core_name(name):
    """Strip titles/suffix codes for matching published vs computed rows."""
    s = str(name).replace("\xa0", " ").replace("’", "'").upper()
    words = re.sub(r"[^A-Z0-9' ]", " ", s).split()
    keep = [w for w in words if w not in _TITLE_TOK and not re.fullmatch(
        r"(MX|MJ|MF|MXP|MJP|MFP|PAX|T2B|T2BP|RAE|RM|UDX|OM|OGM|MXB|MXS|MXG|MXC|MJB|MJS|MJG|MJC|PAD|PJD|PDS|PJS|TQX|TQXP|BN-V)\d*", w)]
    return " ".join(keep)


def validate(published, computed, label):
    """Cell-compare published rows vs computed rows; returns (n_diffs, n_spec_diffs)."""
    ndiff = nspec = nmiss = 0
    for sec in SECTIONS:
        pub = [r for r in published if r["section"] == sec]
        cmp_ = {core_name(c["name"]): c for c in computed if c["section"] == sec}
        keys = BREED_COLS if sec.startswith("Breed") else GROUP_COLS
        for p in pub:
            pc = core_name(p["name"])
            c = cmp_.get(pc)
            if c is None:
                for k, v in cmp_.items():
                    if pc and (pc in k or k in pc):
                        c = v
                        break
            if c is None:
                nmiss += 1
                print(f"  NO-MATCH  {label} {sec}: {p['name']}")
                continue
            for k in keys + ["rank"]:
                if num(p[k]) != num(c[k]):
                    if k.endswith("_spec"):
                        nspec += 1
                    else:
                        ndiff += 1
                        print(f"  DIFF  {label} {sec} {p['name'][:40]} {k}: pub {p[k]} vs calc {c[k]}")
    print(f"{label}: {len([r for r in published])} published rows -> "
          f"{ndiff} cell diffs, {nspec} spec-count diffs (expected; supported entries), {nmiss} unmatched")
    return ndiff + nmiss


def _invariants(rows, label):
    """The parse.py-era checks: total == component sum, ranks contiguous-with-ties, totals descending."""
    bad = 0
    for sec in SECTIONS:
        sec_rows = [r for r in rows if r["section"] == sec]
        comp = (["bob_pts", "bos_pts"] if sec.startswith("Breed")
                else ["bis_pts"] + [f"grp{i}_pts" for i in (1, 2, 3, 4)])
        prev_tot, prev_rank = None, 0
        for i, r in enumerate(sec_rows, 1):
            if num(r["total"]) != sum(num(r[c]) for c in comp):
                bad += 1
                print(f"  INVARIANT total!=sum: {label} {sec} {r['name']}")
            if prev_tot is not None and num(r["total"]) > prev_tot:
                bad += 1
                print(f"  INVARIANT not descending: {label} {sec} {r['name']}")
            want = prev_rank if num(r["total"]) == prev_tot else i
            if num(r["rank"]) != want:
                bad += 1
                print(f"  INVARIANT rank: {label} {sec} {r['name']} rank {r['rank']} want {want}")
            prev_tot, prev_rank = num(r["total"]), num(r["rank"])
    print(f"{label}: invariants {'OK' if not bad else f'{bad} FAILURES'}")
    return bad


if __name__ == "__main__":
    import json
    raw1 = read_raw(os.path.join(HERE, "raw_akc", "ESS Conformation 1Q 2026.xlsx"))
    raw2 = read_raw(os.path.join(HERE, "raw_akc", "ESS Conformation 2Q 2026.xls"))
    print(f"raw rows: 1Q {len(raw1)}, 2Q {len(raw2)}")

    fails = 0
    # Q1: computed from the 1Q window alone vs the repo's published Q1 rows
    q1_pub = [r for r in json.load(open(os.path.join(HERE, "breed_group.json"), encoding="utf-8"))
              if r["year"] == "2026" and r["quarter"] == "Q1"]
    q1_calc = compute_canonical(raw1, "2026", "Q1")
    fails += _invariants(q1_calc, "Q1 computed")
    fails += validate(q1_pub, q1_calc, "Q1 vs breed_group.json")

    # Jan–Jun: computed from 1Q+2Q concatenated vs an in-memory parse of the published PDF
    from parse import parse_pdf
    q2_pub = parse_pdf(os.path.join(HERE, "pdfs", "2026-Conformation-Q2.pdf"))
    q2_calc = compute_canonical(raw1 + raw2, "2026", "Q2")
    fails += _invariants(q2_calc, "JanJun computed")
    fails += validate(q2_pub, q2_calc, "JanJun vs 2026-Conformation-Q2.pdf")

    sys.exit(1 if fails else 0)

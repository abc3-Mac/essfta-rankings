#!/usr/bin/env python3
"""Reconcile parsed rankings against the source PDFs to find missing/dropped rows.

Two independent signals (neither reuses the main parsers' row objects):

  A. Rank-contiguity gaps — within each ranking list (sport/section · year · qtr ·
     category) ranks must run 1,2,3,… (ties share a rank, then the next rank skips
     ahead by the tie count: 1,2,2,4 is valid). A *new* rank that doesn't equal the
     row's 1-based position means a row is missing before it. Catches partial drops.

  B. Raw-PDF data-line count — independently count plausible data lines per PDF
     straight from `pdftotext -layout`, to (a) confirm which PDFs yielded 0 rows
     and (b) estimate the true row count of the fully-dropped Agility files.
"""
import json, os, re, subprocess, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__))
PDFS = os.path.join(HERE, "pdfs")

conf = json.load(open(os.path.join(HERE, "breed_group.json"), encoding="utf-8"))
sports = json.load(open(os.path.join(HERE, "sports.json"), encoding="utf-8"))


# ---------- A. rank-contiguity gap detection -------------------------------
def gaps_in(rows):
    """rows: list of dicts each with int 'rank'. Return list of (expected, found)
    where a new rank group starts at the wrong position (missing rows before it)."""
    rows = sorted(rows, key=lambda r: int(r["rank"]))
    issues = []
    prev_rank = None
    for pos, r in enumerate(rows, start=1):     # 1-based position
        rk = int(r["rank"])
        if rk != prev_rank:                     # first row of a new rank group
            if rk != pos:
                issues.append((pos, rk))
        prev_rank = rk
    return issues


def audit(rows, keyfn, label):
    groups = collections.defaultdict(list)
    for r in rows:
        groups[keyfn(r)].append(r)
    flagged = 0
    detail = []
    for k, g in sorted(groups.items()):
        iss = gaps_in(g)
        if iss:
            flagged += 1
            # number of missing rows ≈ sum of (found_rank - expected_pos) at each break,
            # net of ties; report first break and the list size.
            first = iss[0]
            detail.append((k, len(g), max(int(r["rank"]) for r in g), iss))
    print(f"\n=== A. rank-gap audit: {label} ===")
    print(f"{len(groups)} ranking lists, {flagged} with gaps")
    for k, n, mx, iss in detail:
        print(f"  GAP {k}: {n} rows, max rank {mx}, breaks(expectedPos→foundRank)={iss[:6]}")
    return detail


audit(conf, lambda r: (r["section"], r["year"], r["quarter"]), "Conformation")
audit(sports, lambda r: (r["sport"], r["year"], r["quarter"], r["category"]), "Sports")


# ---------- B. raw-PDF data-line count -------------------------------------
SCORE = re.compile(r"\d+\.\d+|\b\d{2,4}\b")
NOISE = re.compile(r"SCORECARD|Results|compiled|Average|Springer|Rankings|Page|"
                   r"Owner|^\s*$|Trials|Combined Open|No Dogs", re.I)


def raw_dataline_count(path, sport):
    """Independent, parser-free count of plausible data lines: a line with a name
    (letters) AND a trailing-ish numeric token, that isn't obvious noise."""
    txt = subprocess.run(["pdftotext", "-layout", path, "-"],
                         capture_output=True, text=True).stdout
    n = 0
    for ln in txt.split("\n"):
        s = ln.strip()
        if not s or NOISE.search(s):
            continue
        if not re.search(r"[A-Za-z]{3,}", s):       # needs a real word (a name)
            continue
        chunks = [c for c in re.split(r"\s{2,}", s) if c.strip()]
        if len(chunks) >= 2 and re.match(r"^\d+(\.\d+)?$", chunks[-1].strip()):
            n += 1
        elif re.match(r"^\d+\.?\s+\S", s) and SCORE.search(s):   # rank-led w/ a number
            n += 1
    return n


print("\n=== B. raw PDF data-line count vs parsed rows ===")
parsed_by_file = collections.Counter()
# map parsed sport rows back to their file via (sport, year-ish) — use manifest
manifest = json.load(open(os.path.join(HERE, "sports_manifest.json")))
file_of = {(m["sport"], m["year"]): m["file"] for m in manifest}
sp_parsed = collections.Counter((r["sport"], r["year"]) for r in sports)

print(f"{'PDF':30} {'parsed':>7} {'raw~':>6}  note")
for path in sorted(glob.glob(os.path.join(PDFS, "*.pdf"))):
    base = os.path.basename(path)
    m = re.match(r"(\d{4})-(\w+)-(Q\d)", base)
    year, sport, q = m.group(1), m.group(2), m.group(3)
    if sport == "Conformation":
        parsed = sum(1 for r in conf if r["year"] == year)
    else:
        parsed = sp_parsed.get((sport, year), 0)
    raw = raw_dataline_count(path, sport)
    note = ""
    if parsed == 0 and raw > 0:
        note = "<<< PDF HAS DATA BUT 0 PARSED (recoverable)"
    elif raw and parsed < 0.6 * raw:
        note = f"<<< parsed {parsed}/{raw} ~ {round(100*parsed/raw)}% (possible drops)"
    print(f"{base:30} {parsed:7d} {raw:6d}  {note}")

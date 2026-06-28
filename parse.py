#!/usr/bin/env python3
"""Parse ESSFTA Breed/Group quarterly-ranking PDFs into structured CSV/JSON.

Handles both layout generations (2013-2019 'old', 2020-2026 'new') by reading
column x-positions live from each page's header rather than hardcoding them.

Sections per report (each its own page):
  Breed Competition - Dogs      (7 stat cols: #BOB #SpecBOB BOBpts #BOS #SpecBOS BOSpts Total)
  Breed Competition - Bitches
  Group Competition - Dogs      (11 stat cols: BIS#/pts GRP1#/pts ... GRP4#/pts Total)
  Group Competition - Bitches
"""
import pdfplumber, re, csv, json, os, glob

HERE = os.path.dirname(os.path.abspath(__file__))
PDFS = os.path.join(HERE, "pdfs")

NUM_RE = re.compile(r'^\(?-?\d+\)?$')          # 75  (8)  1277
RANK_RE = re.compile(r'^\d+$')

BREED_COLS = ["bob_shows", "bob_spec", "bob_pts", "bos_shows", "bos_spec", "bos_pts", "total"]
GROUP_COLS = ["bis_n", "bis_pts", "grp1_n", "grp1_pts", "grp2_n", "grp2_pts",
              "grp3_n", "grp3_pts", "grp4_n", "grp4_pts", "total"]


def clean_num(t):
    """'(8)' -> '8', '()' -> '', '1,277' -> '1277'."""
    t = t.replace("(", "").replace(")", "").replace(",", "").strip()
    return t


def lines_from_words(words, ytol=3.0):
    """Group words into visual lines by top coordinate."""
    ws = sorted(words, key=lambda w: (round(w["top"], 1), w["x0"]))
    lines = []
    for w in ws:
        placed = False
        for ln in lines:
            if abs(ln["top"] - w["top"]) <= ytol:
                ln["words"].append(w)
                ln["top"] = (ln["top"] * ln["n"] + w["top"]) / (ln["n"] + 1)
                ln["n"] += 1
                placed = True
                break
        if not placed:
            lines.append({"top": w["top"], "n": 1, "words": [w]})
    for ln in lines:
        ln["words"].sort(key=lambda w: w["x0"])
    lines.sort(key=lambda l: l["top"])
    return lines


def find_header(lines):
    """Return (dog_x, owner_x, numzone_x) from the 'Rank Dog Owners ...' line
    and the stat-header tokens to its right."""
    STAT_HDR = {"#BOB", "#BOS", "BOB", "BOS", "Points", "Total", "BIS",
                "GRP1", "GRP2", "GRP3", "GRP4", "Shows", "#Spec", "#"}
    for i, ln in enumerate(lines):
        txt = [w["text"] for w in ln["words"]]
        if "Rank" in txt and ("Dog" in txt or "Bitch" in txt) and "Owners" in txt:
            def ctr(name):
                w = next(w for w in ln["words"] if w["text"] == name)
                return (w["x0"] + w["x1"]) / 2
            rank_w = next(w for w in ln["words"] if w["text"] == "Rank")
            dog_cx = ctr("Dog") if any(w["text"] == "Dog" for w in ln["words"]) else ctr("Bitch")
            owner_cx = ctr("Owners")
            # Header LABELS are centered over their columns but the DATA is
            # left-aligned far to the left, so split name vs owner at the midpoint
            # between the two label centers, and start names just after the rank.
            name_left = rank_w["x1"] + 1
            mid = (dog_cx + owner_cx) / 2
            cand = []
            for ln2 in lines[max(0, i - 2):i + 1]:
                for w in ln2["words"]:
                    if w["x0"] > owner_cx + 20 and (w["text"] in STAT_HDR or NUM_RE.match(w["text"])):
                        cand.append(w["x0"])
            numzone_x = min(cand) - 6 if cand else owner_cx + 80
            # Stat-column centers straight from the header. Among the header lines,
            # take the one with the most labels right of the number zone (Group's
            # "BIS BIS GRP1 GRP1 ... Total" line gives 11; new-format Breed's Rank
            # line gives 7) — far more reliable than clustering sparse data.
            hdr_centers = []
            for ln2 in lines[max(0, i - 2):i + 2]:
                cs = sorted((w["x0"] + w["x1"]) / 2 for w in ln2["words"]
                            if w["x0"] >= numzone_x - 4 and w["text"] in STAT_HDR)
                if len(cs) > len(hdr_centers):
                    hdr_centers = cs
            return name_left, mid, numzone_x, ln["top"], hdr_centers
    return None


def cluster_centers(xs, k):
    """1-D cluster x-centers into k columns by largest gaps."""
    xs = sorted(xs)
    if len(xs) <= k:
        return xs
    # gaps between consecutive points
    gaps = sorted(range(1, len(xs)), key=lambda i: xs[i] - xs[i - 1], reverse=True)
    cuts = sorted(gaps[:k - 1])
    clusters, start = [], 0
    for c in cuts + [len(xs)]:
        seg = xs[start:c]
        clusters.append(sum(seg) / len(seg))
        start = c
    return clusters


def parse_page(lines, section, year, quarter):
    hdr = find_header(lines)
    if not hdr:
        return []
    name_left, mid, numzone_x, header_top, hdr_centers = hdr
    # restrict to the data region: drop title / "Results compiled" / the header row itself
    lines = [ln for ln in lines if ln["top"] > header_top + 1]
    is_group = section.startswith("Group")
    ncols = 11 if is_group else 7
    colnames = GROUP_COLS if is_group else BREED_COLS

    rank_zone = name_left                       # rank int sits left of the Dog column

    # A data/stat row is any line carrying numeric tokens in the number zone.
    # The rank number is printed only on the FIRST of a set of tied dogs; tied
    # rows have a blank rank and must inherit the previous rank.
    anchors = []                       # (line, rank_or_None)
    for ln in lines:
        left = [w for w in ln["words"] if w["x0"] < rank_zone]
        nums_right = [w for w in ln["words"] if w["x0"] >= numzone_x and NUM_RE.match(w["text"])]
        if len(nums_right) >= 2:
            rank_tok = next((w for w in left if RANK_RE.match(w["text"])), None)
            anchors.append((ln, int(rank_tok["text"]) if rank_tok else None))

    if not anchors:
        return []

    # fill blank (tied) ranks from the previous printed rank
    filled = []
    prev = 0
    for ln, rk in anchors:
        if rk is None:
            rk, tie = prev, True
        else:
            prev, tie = rk, False
        filled.append((ln, rk, tie))
    anchors = [(ln, rk) for ln, rk, _ in filled]
    tie_flags = {id(ln): tie for ln, _, tie in filled}

    # column centers from all anchor numeric tokens (x-center)
    xs = []
    for ln, _ in anchors:
        for w in ln["words"]:
            if w["x0"] >= numzone_x and NUM_RE.match(w["text"]):
                xs.append((w["x0"] + w["x1"]) / 2)
    # Prefer header-derived centers (robust on sparse/zero-heavy sections like
    # Group-Bitches); fall back to clustering the data if the header didn't yield
    # exactly the expected number of columns.
    centers = hdr_centers if len(hdr_centers) == ncols else cluster_centers(xs, ncols)

    # Name/owner boundary: the OWNER column is left-aligned — nearly every owner
    # starts at the same x (its leading initial / honorific). Past the name block
    # (x > name_left+40, which drops the "GCH CH " call-name pseudo-column), the
    # owner's left edge is the most-frequent x0; secondary multi-owner columns
    # sit further right but appear in fewer rows. So take the LEFTMOST of the
    # near-universal modes — taking the rightmost would swallow a stray owner
    # initial into the name on multi-owner entries.
    from collections import Counter
    x0c = Counter()
    for ln in lines:
        for w in ln["words"]:
            if not NUM_RE.match(w["text"]) and name_left + 40 < w["x0"] < numzone_x:
                x0c[round(w["x0"])] += 1
    if x0c:
        maxc = max(x0c.values())
        strong = [x for x, n in x0c.items() if n >= 0.8 * maxc]
        mid = min(strong) - 5

    anchor_tops = [ln["top"] for ln, _ in anchors]
    anchor_set = {id(ln) for ln, _ in anchors}
    body_lines = [ln for ln in lines if id(ln) not in anchor_set
                  and any(name_left - 6 <= w["x0"] < numzone_x for w in ln["words"])]

    def cx(w):
        return (w["x0"] + w["x1"]) / 2

    # A conformation name never begins with a bare owner initial ("K. ..."); when
    # one bleeds across the column boundary, strip the leading initials back onto
    # the owner. (Titleless names start with a kennel word, never "X.", so safe.)
    TITLE = re.compile(r"^(GCH[A-Z]?\d?|CH|DC|NOHS|FC|AFC)\b")
    LEAK = re.compile(r"^((?:[A-Z]\.\s+)+)(\S.*)$")

    def fix_leak(name, owner):
        m = LEAK.match(name)
        if m and (TITLE.match(m.group(2)) or len(m.group(2)) > 6):
            return m.group(2), (m.group(1).strip() + " " + owner).strip()
        return name, owner

    def build(wrap_below):
        """Group body (wrap) lines onto anchors under one of two layout models:
        wrap_below (2013-2019: block grows downward from the rank line) or
        centered (2020-2025: rank line sits in the middle of the block)."""
        extra = {i: [] for i in range(len(anchors))}
        for ln in body_lines:
            if wrap_below:
                cand = [k for k in range(len(anchors)) if anchor_tops[k] <= ln["top"] + 1]
                j = max(cand, key=lambda k: anchor_tops[k]) if cand else 0
            else:
                j = min(range(len(anchors)), key=lambda k: abs(anchor_tops[k] - ln["top"]))
            if abs(anchor_tops[j] - ln["top"]) <= 34:
                extra[j].append(ln)
        out = []
        for idx, (ln, rank) in enumerate(anchors):
            # order by LINE (top), then left-to-right within each line; using each
            # token's own top would scramble same-line tokens that differ sub-pixel.
            ent = sorted([ln] + extra[idx], key=lambda l: l["top"])
            toks = [w for el in ent for w in sorted(el["words"], key=lambda w: w["x0"])]
            name = " ".join(w["text"] for w in toks
                            if name_left - 6 <= cx(w) < mid
                            and not (w["x0"] < rank_zone and RANK_RE.match(w["text"])))
            owner = " ".join(w["text"] for w in toks if mid <= cx(w) < numzone_x)
            name = re.sub(r"\s+", " ", name).strip()
            owner = re.sub(r"\s+", " ", owner).strip()
            name, owner = fix_leak(name, owner)
            stats = [""] * ncols
            for w in ln["words"]:
                if w["x0"] >= numzone_x and NUM_RE.match(w["text"]):
                    ci = min(range(len(centers)), key=lambda c: abs(centers[c] - cx(w)))
                    v = clean_num(w["text"])
                    stats[ci] = v if stats[ci] == "" else (stats[ci] + "/" + v)
            row = {"year": year, "quarter": quarter, "section": section,
                   "rank": rank, "tie": "T" if tie_flags.get(id(ln)) else "",
                   "name": name, "owner": owner}
            for cn, sv in zip(colnames, stats):
                row[cn] = sv
            out.append(row)
        return out

    # Self-correcting: the right layout model yields cleaner names. Score a row
    # set by how many names start with a conformation title and carry no owner
    # bleed ('/' belongs to owners), then keep the better model.
    TITLE = re.compile(r"^(GCH[A-Z]?|CH|DC|NOHS|FC|AFC)\b")

    def score(rows):
        s = 0
        for r in rows:
            if TITLE.match(r["name"]):
                s += 2
            if "/" in r["name"]:
                s -= 2
            if not r["owner"]:
                s -= 1
        return s

    cand_below, cand_center = build(True), build(False)
    return cand_below if score(cand_below) >= score(cand_center) else cand_center


def parse_table_page(table, section, year, quarter):
    """Parse the bordered-table layout (2026+) via pdfplumber's grid cells."""
    is_group = section.startswith("Group")
    colnames = GROUP_COLS if is_group else BREED_COLS
    rows = []
    prev = 0
    for r in table:
        cells = [(c or "").replace("\n", " ").strip() for c in r]
        if not cells or not any(cells):
            continue
        if cells[0] == "Rank":            # header row (repeats on continuation pages)
            continue
        rank_raw = cells[0]
        tie = ""
        if RANK_RE.match(rank_raw):
            rank = int(rank_raw); prev = rank
        else:                              # blank rank = tie with the dog above
            rank = prev; tie = "T"
        name = cells[1] if len(cells) > 1 else ""
        owner = cells[2] if len(cells) > 2 else ""
        m = re.match(r"^((?:[A-Z]\.\s+)+)(\S.*)$", name)
        if m and (re.match(r"^(GCH[A-Z]?\d?|CH|DC|NOHS|FC|AFC)\b", m.group(2)) or len(m.group(2)) > 6):
            name, owner = m.group(2), (m.group(1).strip() + " " + owner).strip()
        stats = [clean_num(c) for c in cells[3:3 + len(colnames)]]
        stats += [""] * (len(colnames) - len(stats))
        if not name and not any(stats):
            continue
        row = {"year": year, "quarter": quarter, "section": section,
               "rank": rank, "tie": tie, "name": name, "owner": owner}
        for cn, sv in zip(colnames, stats):
            row[cn] = sv
        rows.append(row)
    return rows


def is_bordered(page):
    """2026+ reports draw real cell borders (line objects); older ones don't."""
    return len(page.lines) > 20


def section_of(page_text):
    t = page_text
    # Matches both "Breed Competition - Dogs" (2013-2025) and
    # "2026 Breed Ranking Jan to Mar - Dogs" (2026+).
    for sec_re, sec in [
        (r"Breed (?:Competition|Ranking[^\n]*?)\s*[-‐]\s*Dogs", "Breed - Dogs"),
        (r"Breed (?:Competition|Ranking[^\n]*?)\s*[-‐]\s*Bitches", "Breed - Bitches"),
        (r"Group (?:Competition|Ranking[^\n]*?)\s*[-‐]\s*Dogs", "Group - Dogs"),
        (r"Group (?:Competition|Ranking[^\n]*?)\s*[-‐]\s*Bitches", "Group - Bitches"),
    ]:
        if re.search(sec_re, t):
            return sec
    return None


def is_continuation(txt):
    """A title-less page that still carries a data table (Rank ... Owners header)."""
    for line in txt.splitlines():
        if "Rank" in line and "Owners" in line and ("Dog" in line or "Bitch" in line):
            return True
    return False


def parse_pdf(path):
    base = os.path.basename(path)
    m = re.match(r"(\d{4})-Conformation-(Q\d)", base)
    if not m:                       # pdfs/ also holds Obedience/Agility/Rally files
        return []
    year, quarter = m.group(1), m.group(2)

    out = []
    cur = None                                  # current section (carried across continuation pages)
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            sec = section_of(txt)
            if sec:
                cur = sec
            elif cur and is_continuation(txt):
                sec = cur                       # title-less continuation page
            else:
                continue
            if is_bordered(page):
                table = page.extract_table()
                if table:
                    out.extend(parse_table_page(table, sec, year, quarter))
            else:
                words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
                lines = lines_from_words(words)
                out.extend(parse_page(lines, sec, year, quarter))
    return out


def main():
    allrows = []
    for path in sorted(glob.glob(os.path.join(PDFS, "*.pdf"))):
        rows = parse_pdf(path)
        by_sec = {}
        for r in rows:
            by_sec[r["section"]] = by_sec.get(r["section"], 0) + 1
        print(f"{os.path.basename(path):32s} -> {len(rows):3d} rows  {by_sec}")
        allrows.extend(rows)

    base = ("year", "quarter", "section", "rank", "tie", "name", "owner")
    fields = list(base) + \
             sorted({k for r in allrows for k in r if k not in base},
                    key=lambda x: (GROUP_COLS + BREED_COLS).index(x) if x in (GROUP_COLS + BREED_COLS) else 99)
    with open(os.path.join(HERE, "breed_group.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in allrows:
            w.writerow(r)
    json.dump(allrows, open(os.path.join(HERE, "breed_group.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\nTOTAL {len(allrows)} rows -> breed_group.csv / .json")


if __name__ == "__main__":
    main()

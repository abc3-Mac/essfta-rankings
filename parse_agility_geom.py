#!/usr/bin/env python3
"""Coordinate-based parser for the older Agility 'Standings' reports.

These reports shuffle their columns year to year (owner before vs after the
scores, ranks present or absent, dog names wrapping across lines). Reading by
x-position instead of token order handles all of them:

  * rank   = a number at the far left (x < ~60)
  * scores = the other numbers; Avg Score is 0-100 (>12), YPS is small (<12)
  * owner  = text in the owner column, located by its left-aligned x0 mode,
             which sits either left or right of the score block per the header
  * dog    = the remaining left-hand text (accumulated across wrapped lines)
"""
import pdfplumber, re
from collections import defaultdict, Counter

NUM = re.compile(r"^\d+(?:\.\d+)?$")
LEVEL = re.compile(r"^(Preferred\s+)?(Novice|Open|Excellent|Master|Veteran)\b", re.I)
YPS_MAX = 12.0


def _lines(page):
    d = defaultdict(list)
    for w in page.extract_words(use_text_flow=False, keep_blank_chars=False):
        d[round(w["top"])].append(w)
    return [sorted(d[t], key=lambda w: w["x0"]) for t in sorted(d)]


def _is_colheader(toks):
    j = " ".join(t["text"] for t in toks)
    return bool(re.search(r"Owner", j) and re.search(r"YPS|Avg|Score", j))


def _owner_after(toks):
    ox = [t["x0"] for t in toks if t["text"].startswith("Owner")]
    sx = [t["x0"] for t in toks if re.match(r"Avg|Score|YPS|Average", t["text"])]
    return (min(ox) > min(sx)) if ox and sx else None


def _score_cols(toks):
    """From a column-header line, return (owner_label_x, score_lo)."""
    ox = [t["x0"] for t in toks if t["text"].startswith("Owner")]
    sx = [t["x0"] for t in toks if re.match(r"Avg|Score|YPS|Average", t["text"])]
    return (min(ox) if ox else None), (min(sx) if sx else None)


def parse_agility_geom(path, year, quarter):
    rows = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            lines = _lines(page)
            # score column position + owner order from the header labels, which
            # may be split across a couple of short header lines (e.g. 2015)
            owner_lx = score_lo = None
            for toks in lines[:30]:
                if len(toks) > 6:               # skip prose lines
                    continue
                for t in toks:
                    if owner_lx is None and re.match(r"Owner", t["text"]):
                        owner_lx = t["x0"]
                    if re.match(r"Avg|Score|YPS|Average", t["text"]):
                        score_lo = t["x0"] if score_lo is None else min(score_lo, t["x0"])
                if owner_lx is not None and score_lo is not None:
                    break
            if score_lo is None:
                continue
            score_lo -= 18                      # numbers are right-aligned under labels
            owner_after = owner_lx is not None and owner_lx > score_lo

            def scoretoks(toks):                # numeric tokens in the score band
                return [t for t in toks if NUM.match(t["text"]) and t["x0"] >= score_lo
                        and (not owner_after or owner_lx is None or t["x0"] < owner_lx - 6)]

            # owner column left edge = dominant left-aligned x0 mode in its region
            region = Counter()
            for toks in lines:
                st = scoretoks(toks)
                if not st:
                    continue
                smax = max(t["x0"] for t in st)
                for t in toks:
                    if NUM.match(t["text"]):
                        continue
                    if owner_after and t["x0"] > smax + 6:
                        region[round(t["x0"])] += 1
                    elif (not owner_after) and 60 < t["x0"] < score_lo - 6:
                        region[round(t["x0"])] += 1
            # owner's first column = leftmost strong left-aligned mode in the
            # vicinity of the header's Owner label (avoids dog columns far to the
            # left and 2nd-owner sub-columns to the right)
            owner_left = None
            if region:
                mx = max(region.values())
                strong = [x for x, n in region.items() if n >= 0.4 * mx]
                near = [x for x in strong if owner_lx is not None
                        and owner_lx - 55 <= x <= owner_lx + 12]
                owner_left = min(near) if near else min(strong, key=lambda x: abs(x - (owner_lx or 0)))

            category, pending, seq = "", [], 0
            for toks in lines:
                txt = " ".join(t["text"] for t in toks)
                st = scoretoks(toks)
                lm = LEVEL.match(txt)
                if lm and not st:
                    category = ("Preferred " if lm.group(1) else "") + lm.group(2).title()
                    pending, seq = [], 0
                    continue
                if not st:
                    frag = " ".join(t["text"] for t in toks if not NUM.match(t["text"])
                                    and 60 < t["x0"] < (owner_left or score_lo) - 6).strip()
                    label = re.search(r"\b(Ave|Avg|Average|Score|YPS|Owner|qualifying|legs|Ranked)\b", frag)
                    if frag and category and not label and len(frag) < 70:
                        pending.append(frag)
                    continue
                if not category:
                    continue
                # ---- anchor (scored) line ----
                vals = [float(t["text"]) for t in st]
                avg = next((f"{v:g}" for v in vals if 12 < v <= 100), "")
                yps = next((f"{v:g}" for v in vals if 0 < v <= 12), "")
                if not avg:                      # not an average-score row (e.g. PACH points)
                    pending = []
                    continue
                rank_tok = next((t for t in toks if NUM.match(t["text"]) and t["x0"] < 60), None)
                if owner_after:
                    dog_x = (owner_left and min(owner_left, score_lo)) or score_lo
                    dog = [t for t in toks if not NUM.match(t["text"]) and 40 < t["x0"] < score_lo - 4]
                    own = [t for t in toks if not NUM.match(t["text"])
                           and owner_left is not None and t["x0"] >= owner_left - 6]
                else:
                    cut = (owner_left - 22) if owner_left is not None else score_lo - 4
                    dog = [t for t in toks if not NUM.match(t["text"]) and 40 < t["x0"] < cut]
                    own = [t for t in toks if not NUM.match(t["text"])
                           and cut <= t["x0"] < score_lo - 4]
                name = " ".join(pending + [t["text"] for t in dog]).strip()
                owner = " ".join(t["text"] for t in own).strip()
                pending = []
                if not name:
                    continue
                if rank_tok:
                    rank = int(rank_tok["text"]); seq = rank
                else:
                    seq += 1; rank = seq
                rows.append({"sport": "Agility", "year": year, "quarter": quarter,
                             "category": category, "rank": rank, "tie": "",
                             "dog": name, "owner": owner, "score": avg, "score2": yps})
    return rows


if __name__ == "__main__":
    import sys
    for path, yr in [("pdfs/2013-Agility-Q4.pdf", "2013"),
                     ("pdfs/2015-Agility-Q4.pdf", "2015"),
                     ("pdfs/2020-Agility-Q4.pdf", "2019")]:
        rs = parse_agility_geom(path, yr, "Q4")
        cats = {}
        for r in rs:
            cats[r["category"]] = cats.get(r["category"], 0) + 1
        print(f"\n### {yr}: {len(rs)} rows  {cats} ###")
        for r in rs[:6]:
            print(f"  [{r['category'][:10]:10}] {r['rank']:>2} {r['dog'][:42]:42} | {r['owner'][:22]:22} | {r['score']} / {r['score2']}")

#!/usr/bin/env python3
"""Recovery parsers for three Agility quarterly PDFs that defeat every existing
parser (parse_sports.py / parse_agility_geom.py): 2020-Agility-Q4,
2025-Agility-Q2, 2025-Agility-Q3. Held back from the 2026-09-16/17 ingest
because the standard parsers either dropped rows or leaked header/owner text
into dog names -- see spotlight-siblings/COVERAGE.md's "Parser hazards"
section and the 2020 off-by-one note for the background.

Does NOT touch parse_agility_geom.py or its behaviour for 2013/2015/2019
(those ship as-is, already published). This is a sibling module, used only
for the three quarters above.

Two independent techniques, one per failure mode:

  parse_agility_2020()      -- 2020-Agility-Q4. Columns are clean (Dog / Owner
      / Co-Owner / Ave YPS / Ave Score, x-positions read from the file's own
      header line, never hardcoded) but the report prints no rank numbers and
      rows wrap onto continuation lines (more AKC titles, or the rest of a
      long owner/co-owner name). Works at word level (pdfplumber
      extract_words); a continuation line has no score and is folded into the
      row ABOVE it, per column. Ranks are assigned in DENSE order (1,2,2T,3,
      ...) since the club's own card doesn't print any for this file -- see
      HANDOFF.md's note that this era's cards use dense ranking after a tie.

  parse_agility_charcols()  -- 2025-Agility-Q2 / Q3. The PDF text layer
      renders the dog-name/title column and the owner column as two
      PHYSICALLY OVERLAPPING text runs whenever a title is long enough to
      reach into the owner column's x-range (and, on one row, a long
      co-owner list overlaps the trailing score number). pdfplumber's
      extract_words() merges the interleaved characters into garbage tokens
      (e.g. "T2BJ5e" from "T2B5" + "Je" of "Jenny"). The fix works at the
      CHARACTER level (page.chars), in ORIGINAL STREAM ORDER (never sorted by
      x0): each overlapping run is still internally contiguous and
      monotonically increasing in x0 in the stream, so splitting on a
      backward x0 jump (a second run starting) or a wide forward gap (a
      normal column boundary within one unbroken flow) recovers each run
      intact; every run is then bucketed into rank / name / owner / score /
      yps by its own start position. Column x's (owner_x) are derived from
      the data itself, not the header label (which is off-column here).
"""
import re
from collections import defaultdict, Counter

import pdfplumber

NUM = re.compile(r"^\d+(?:\.\d+)?$")


# ============================================================== 2020-Agility-Q4
def _lines_2020(page, tol=3.0):
    """Group words into visual lines by 'top', tolerating a couple of px of
    baseline jitter between runs on the same row (digits and letters in this
    file's font don't always share an exact baseline -- a wrapped row's score
    can land ~1px below its dog/owner text, which plain round(top) sometimes
    splits into two false lines)."""
    words = sorted(page.extract_words(use_text_flow=False, keep_blank_chars=False),
                    key=lambda w: w["top"])
    lines, cur, cur_top = [], [], None
    for w in words:
        if cur and w["top"] - cur_top > tol:
            lines.append(sorted(cur, key=lambda w: w["x0"]))
            cur, cur_top = [], None
        cur.append(w)
        cur_top = w["top"] if cur_top is None else min(cur_top, w["top"])
    if cur:
        lines.append(sorted(cur, key=lambda w: w["x0"]))
    return lines


_CAT_2020 = re.compile(r"^(Preferred\s+)?(Novice|Open|Excellent)\s+Ess\b", re.I)
_SOTY_2020 = re.compile(r"Springer of the Year", re.I)
_NOQUAL_2020 = re.compile(r"^No\s+Preferred", re.I)


def _clean(s):
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()


def parse_agility_2020(path, year="2020", quarter="Q4"):
    rows = []
    with pdfplumber.open(path) as pdf:
        category = None
        cols = None  # (owner_x, coowner_x) from this page's own header line
        cur = None   # in-progress row
        prev_score = None
        prev_rank = 0

        def finalize():
            nonlocal cur
            if cur is None:
                return
            dog = _clean(" ".join(cur["dog"]))
            owner = _clean(" ".join(cur["owner"]))
            coowner = _clean(" ".join(cur["coowner"]))
            full_owner = f"{owner},{coowner}" if owner and coowner else (owner or coowner)
            if dog:
                rows.append({"sport": "Agility", "year": year, "quarter": quarter,
                             "category": cur["category"], "rank": cur["rank"], "tie": cur["tie"],
                             "dog": dog, "owner": full_owner,
                             "score": cur["score"], "score2": cur["yps"]})
            cur = None

        for page in pdf.pages:
            for toks in _lines_2020(page):
                stxt = " ".join(t["text"] for t in toks).strip()
                if not stxt:
                    continue
                m = _CAT_2020.match(stxt)
                if m:
                    finalize()
                    category = ("Preferred " if m.group(1) else "") + m.group(2).title()
                    prev_score, prev_rank = None, 0
                    continue
                if _SOTY_2020.search(stxt):
                    finalize()
                    category = None   # SOTY tables aren't part of the canonical per-class schema
                    continue
                if _NOQUAL_2020.match(stxt):
                    finalize()
                    continue
                owner_tok = next((t for t in toks if t["text"].startswith("Owner")), None)
                coowner_tok = next((t for t in toks if t["text"].startswith("Co/Owner")), None)
                if owner_tok and coowner_tok:
                    cols = (owner_tok["x0"], coowner_tok["x0"])
                    continue
                if re.match(r"^Dog.?s\s*Name", stxt, re.I) or stxt in ("Average", "YPS") \
                        or re.match(r"^Average\s+Score", stxt, re.I) or stxt == "Score":
                    continue
                if not category or cols is None:
                    continue
                owner_x, coowner_x = cols

                nums = [t for t in toks if NUM.match(t["text"])]
                score_tok = next((t for t in nums if 12 < float(t["text"]) <= 100), None)
                yps_tok = next((t for t in nums if float(t["text"]) <= 12), None)
                is_anchor = score_tok is not None

                nonnum = [t for t in toks if t not in nums]
                right_edge = min([n["x0"] for n in nums], default=1e9)
                dog_bits = [t["text"] for t in nonnum if t["x0"] < owner_x - 2]
                owner_bits = [t["text"] for t in nonnum if owner_x - 2 <= t["x0"] < coowner_x - 2]
                coowner_bits = [t["text"] for t in nonnum if coowner_x - 2 <= t["x0"] < right_edge]

                if is_anchor:
                    finalize()
                    score = f"{float(score_tok['text']):g}"
                    yps = f"{float(yps_tok['text']):g}" if yps_tok else ""
                    if prev_score is not None and score_tok["text"] == prev_score:
                        rank, tie = prev_rank, "T"
                    else:
                        rank = prev_rank + 1
                        tie = ""
                        prev_rank = rank
                    prev_score = score_tok["text"]
                    cur = {"category": category, "rank": rank, "tie": tie,
                           "score": score, "yps": yps,
                           "dog": [" ".join(dog_bits)] if dog_bits else [],
                           "owner": [" ".join(owner_bits)] if owner_bits else [],
                           "coowner": [" ".join(coowner_bits)] if coowner_bits else []}
                else:
                    if cur is None:
                        continue   # stray continuation with nothing to attach to
                    if dog_bits:
                        cur["dog"].append(" ".join(dog_bits))
                    if owner_bits:
                        cur["owner"].append(" ".join(owner_bits))
                    if coowner_bits:
                        cur["coowner"].append(" ".join(coowner_bits))
        finalize()
    return rows


# ============================================================ 2025-Agility-Q2/Q3
def _lines_from_chars(chars):
    """Group chars by visual line (rounded 'top'), preserving ORIGINAL STREAM
    ORDER within each line (never sort by x0) -- when two text runs overlap in
    x-space (garbled dog-title/owner/score columns), content-stream order
    still keeps each run's own characters contiguous and monotonically
    increasing in x0; sorting by x0 is what shreds them into a false
    character-by-character interleave."""
    d = defaultdict(list)
    order = []
    for c in chars:
        t = round(c["top"])
        if t not in d:
            order.append(t)
        d[t].append(c)
    return [d[t] for t in sorted(order)]


def _classify_category(text):
    if re.search(r"10QQs\s+in\s+ExBP", text, re.I):
        return "Preferred Excellent B"
    if re.search(r"10QQs\s+in\s+ExB", text, re.I):
        return "Excellent B"
    m = re.search(r"^(.*?)English Springer Spaniel of the Year", text)
    prefix = m.group(1).strip() if m else ""
    key = re.sub(r"[^a-z]", "", prefix.lower())
    mapping = {
        "novice": "Novice", "novicea": "Novice A", "noviceb": "Novice",
        "open": "Open", "excellenta": "Excellent A",
        "preferrednovice": "Preferred Novice", "preferredopen": "Preferred Open",
        "preferredexcellenta": "Preferred Excellent A",
    }
    return mapping.get(key, prefix or "Overall")


_RANK_MAX_X = 36
_NUM_RUN = re.compile(r"^\d+\.\d+$|^\d+$")
_HEADERISH = re.compile(
    r"^(Dog.?s\s*Name|Owner\s*/?\s*Owners?|Ave\.?$|Score\)?$|YPS$|Ave\s+Score|Ave\s+YPS)", re.I)
_COLUMN_GAP = 15  # px; normal word/NBSP gaps are a few px, real column jumps are 100+


def _find_owner_x(pdf):
    """Owner column left edge, derived from the DATA (the header label's own
    x0 is centered/offset and does not match where row values actually
    start)."""
    votes = Counter()
    for page in pdf.pages:
        words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
        lines = defaultdict(list)
        for w in words:
            lines[round(w["top"])].append(w)
        for toks in lines.values():
            toks = sorted(toks, key=lambda w: w["x0"])
            nums = [w for w in toks if _NUM_RUN.match(w["text"]) and w["x0"] > 600]
            if not nums:
                continue
            band = [w for w in toks if 300 <= w["x0"] < 620]
            if band:
                votes[round(band[0]["x0"])] += 1
    return votes.most_common(1)[0][0] if votes else None


def _text_runs(chars):
    """Split an ORIGINAL-STREAM-ORDER char list into runs. A new run starts
    whenever x0 goes backward relative to the previous char (a second,
    physically-overlapping text object was drawn -- e.g. an overflowing dog
    title/owner list bleeding into the next column) OR whenever there's a
    wide forward gap (a genuine column boundary within an otherwise-unbroken
    stream, e.g. a clean row where rank+name+owner+score is one continuous
    left-to-right flow with no overlap at all)."""
    runs, cur = [], []
    prev_x0 = prev_x1 = None
    for c in chars:
        if prev_x0 is not None and (c["x0"] < prev_x0 - 0.5 or c["x0"] - prev_x1 > _COLUMN_GAP):
            runs.append(cur)
            cur = []
        cur.append(c)
        prev_x0, prev_x1 = c["x0"], c["x1"]
    if cur:
        runs.append(cur)
    return runs


def parse_agility_charcols(path, year, quarter):
    rows = []
    with pdfplumber.open(path) as pdf:
        owner_x = _find_owner_x(pdf)
        category = None
        pending_name, pending_owner = [], []
        for page in pdf.pages:
            for cs in _lines_from_chars(page.chars):
                text = "".join(c["text"] for c in cs)
                stext = text.strip()
                if "English Springer Spaniel of the Year" in text:
                    category = _classify_category(text)
                    pending_name, pending_owner = [], []
                    continue
                if not stext:
                    continue
                if _HEADERISH.match(stext):
                    continue
                if re.match(r"^No\s+Qualifiers", stext, re.I):
                    pending_name, pending_owner = [], []
                    continue
                if re.match(r"^Symbols after Owner", stext, re.I):
                    continue
                if not category:
                    continue

                # 1. leading rank digit(s), stream order, straight off the front
                rest = list(cs)
                rank_bits = []
                if rest and rest[0]["x0"] < _RANK_MAX_X and re.match(r"\d", rest[0]["text"]):
                    k = 0
                    while k < len(rest) and re.match(r"\d", rest[k]["text"]) and rest[k]["x0"] < _RANK_MAX_X:
                        rank_bits.append(rest[k]["text"]); k += 1
                    rest = rest[k:]

                # 2. split into runs (stream order; backward-jump / wide-gap
                # boundaries), classify EACH run by its own content + start
                # position -- the one mechanism that recovers both kinds of
                # corruption (garbled name/owner text, and a score/yps number
                # overlapping the tail of a long owner list).
                runs = _text_runs(rest)
                text_runs, num_bits = [], []
                for run in runs:
                    txt_all = "".join(c["text"] for c in run).strip()
                    if txt_all and run[0]["x0"] > 600 and _NUM_RUN.match(txt_all):
                        num_bits.append((run[0]["x0"], txt_all))
                    else:
                        text_runs.append(run)
                # Does any run already legitimately start in the owner column
                # (from a backward jump / wide gap -- a real second text
                # object), or has earlier continuation-line owner text already
                # been captured for this row? If so, trust it and leave every
                # other run alone even where its OWN characters later cross
                # owner_x (a long title can genuinely extend that far). Only
                # when NEITHER holds do we know the owner text has no run of
                # its own -- it's glued, zero-gap, onto the tail of a name run
                # (e.g. "...T2B3Laura Schreiner*") -- and only then do we
                # split that run at the owner_x boundary.
                has_owner_run = (any(run[0]["x0"] >= owner_x - 1 for run in text_runs)
                                  or bool(pending_owner))
                name_bits, owner_bits = [], []
                for run in text_runs:
                    if run[0]["x0"] >= owner_x - 1:
                        segs = [run]
                    elif not has_owner_run:
                        split_at = next((i for i, c in enumerate(run) if c["x0"] >= owner_x - 1), None)
                        segs = [run] if split_at is None else [run[:split_at], run[split_at:]]
                    else:
                        segs = [run]
                    for seg in segs:
                        txt = "".join(c["text"] for c in seg).strip()
                        if not txt:
                            continue
                        if seg[0]["x0"] < owner_x - 1:
                            name_bits.append(txt)
                        else:
                            owner_bits.append(txt)

                is_anchor = len(num_bits) >= 1
                if name_bits:
                    pending_name.append(" ".join(name_bits))
                if owner_bits:
                    pending_owner.append(" ".join(owner_bits))
                if not is_anchor:
                    continue

                rank_txt = "".join(rank_bits).strip()
                rank = int(rank_txt) if re.match(r"^\d+$", rank_txt) else ""
                dog = _clean(" ".join(pending_name))
                owner = _clean(" ".join(pending_owner))
                pending_name, pending_owner = [], []
                num_bits.sort(key=lambda t: t[0])
                nums = [v for _, v in num_bits]
                if len(nums) >= 2:
                    score, score2 = nums[0], nums[1]
                elif len(nums) == 1:
                    score, score2 = "", nums[0]
                else:
                    continue
                rows.append({"sport": "Agility", "year": year, "quarter": quarter,
                             "category": category, "rank": rank, "tie": "",
                             "dog": dog, "owner": owner, "score": score, "score2": score2})
    return rows


if __name__ == "__main__":
    import sys
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    HERE = "spotlight-siblings"

    def show(rows, label):
        print(f"\n==== {label}: {len(rows)} rows ====")
        for r in rows:
            print(f"[{r['category']:22}] {str(r['rank']):>3}{r.get('tie',''):1} "
                  f"{r['dog'][:52]:52} | {r['owner'][:38]:38} | "
                  f"score={r['score']!r:8} score2={r['score2']!r}")

    if which in ("all", "2020"):
        show(parse_agility_2020(f"{HERE}/2020-Agility-Q4.pdf"), "2020 Q4")
    if which in ("all", "q2"):
        show(parse_agility_charcols(f"{HERE}/2025-Agility-Q2.pdf", "2025", "Q2"), "2025 Q2")
    if which in ("all", "q3"):
        show(parse_agility_charcols(f"{HERE}/2025-Agility-Q3.pdf", "2025", "Q3"), "2025 Q3")

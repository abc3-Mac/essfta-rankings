#!/usr/bin/env python3
"""Parse ESSFTA Obedience / Agility / Rally quarterly reports.

These three sports share a simple visual layout (unlike conformation):
    <rank>  <Dog Name + AKC titles>      <Owner(s)>      <Score> [<Score2>]
grouped into class / award categories. pdftotext -layout preserves the column
gaps, so we split each data line on runs of 2+ spaces.
"""
import subprocess, re, csv, json, os, glob, collections
import pdfplumber

HERE = os.path.dirname(os.path.abspath(__file__))
PDFS = os.path.join(HERE, "pdfs")

NUMERIC = re.compile(r"^\d+(?:\.\d+)?$")
RANK_LEAD = re.compile(r"^(\d+)\.?\s+(.*)$")     # "1 Dog…" or "1. Dog…"

# lines that are never data and never a category header
NOISE = re.compile(r"SCORECARD|Trials |Results taken|Average of|January|"
                   r"No Dogs Eligible|^Page|^\d+\s*$|rankings based|based on the|"
                   r"Springer Showcase|Springer of the Year|Rankings \d{4}|"
                   r"highest combined|Combined Open B/Utility", re.I)


def layout_lines(path):
    out = subprocess.run(["pdftotext", "-layout", path, "-"],
                         capture_output=True, text=True).stdout
    return out.split("\n")


def is_division(line):
    """Obedience super-sections: '... TITLING CLASSES' / 'REGULAR CLASSES'."""
    return bool(re.search(r"\bCLASSES\b", line)) and line.upper() == line


RANK_SCORE = re.compile(r"^(\d+)\.?\s+(\d+(?:\.\d+)?)$")   # "1. 89.8"  (score-second layout)


def split_row(stripped):
    """Return (rank|None, tie, dog, owner, [scores]) or None if not a data row.

    Handles two column orders: score-trailing (Rank Dog Owner Score) and
    score-second (Rank Score Dog Owner, e.g. 2024 Rally)."""
    chunks = re.split(r"\s{2,}", stripped)
    chunks = [c.strip() for c in chunks if c.strip() != ""]
    if len(chunks) < 2:
        return None

    # score-second: first chunk is "<rank> <score>", remaining = Dog, Owner
    m = RANK_SCORE.match(chunks[0])
    if m and len(chunks) >= 3:
        rank = int(m.group(1)); score = m.group(2)
        return rank, "", chunks[1], " / ".join(chunks[2:]), [score]

    # score-trailing: peel trailing numeric chunks as scores (Agility may have 2)
    scores = []
    while chunks and NUMERIC.match(chunks[-1]):
        scores.insert(0, chunks.pop())
    if not scores or not chunks:
        return None
    owner = chunks[-1]
    head = " ".join(chunks[:-1]) if len(chunks) > 1 else ""
    m = RANK_LEAD.match(head)
    if m:
        rank, dog = int(m.group(1)), m.group(2).strip()
        tie = ""
    else:
        rank, dog, tie = None, head.strip(), "T"     # blank rank -> tie
    if not dog:
        return None
    return rank, tie, dog, owner, scores


AG_CLASS = re.compile(r"^(Preferred\s+)?(Novice|Open|Excellent|Master|Veteran)\b", re.I)
AG_LABELS = re.compile(r"Owner|Dog|Name|Average|Avg|YPS|Score|Co[\s/-]?Owner", re.I)


def parse_agility_standings(lines, year, quarter):
    """Older Agility 'Standings' layout (2013-2023). Variants differ a lot:
    single-line-with-rank (2013-16) vs multi-line names (2017-20); the two
    trailing numbers (Avg Score 0-100 and YPS 0-~8) appear in either order, so
    we assign them by magnitude rather than position."""
    rows = []
    category = ""
    pending = []          # accumulated name fragments (continuation lines)
    rank = 0
    for raw in lines:
        s = raw.strip()
        if not s or NOISE.search(s):
            continue
        chunks = [c.strip() for c in re.split(r"\s{2,}", s) if c.strip()]
        is_data = len(chunks) >= 2 and NUMERIC.match(chunks[-1])
        if not is_data:
            m = AG_CLASS.match(s)
            if m and len(s) < 170:
                lvl = (("Preferred " if m.group(1) else "") + m.group(2).title())
                category = lvl; pending = []; rank = 0
            elif AG_LABELS.search(s) and not AG_CLASS.match(s):
                pending = []                          # column-label row: ignore
            else:
                pending.append(s)                     # name fragment (wrapped)
            continue
        # data line — peel trailing numerics (1-2)
        nums = []
        while chunks and NUMERIC.match(chunks[-1]):
            nums.insert(0, chunks.pop())
        if not chunks or not category:
            pending = []; continue
        # leading rank?
        head = chunks[0]
        m = RANK_LEAD.match(head)
        if m:
            rk = int(m.group(1)); chunks[0] = m.group(2).strip()
        else:
            rank += 1; rk = rank
        name = " ".join(pending + [chunks[0]]).strip()
        owners = " / ".join(chunks[1:]) if len(chunks) > 1 else ""
        # assign by magnitude: avg score is the 0-100 value, YPS the small one
        score = yps = ""
        for n in nums:
            (yps := n) if float(n) <= 10 else (score := n)
        pending = []
        rows.append({"sport": "Agility", "year": year, "quarter": quarter,
                     "category": category, "rank": rk, "tie": "",
                     "dog": name, "owner": owners, "score": score, "score2": yps})
    return rows


def category_label(sport, line, division):
    """Clean a header line into a category name."""
    t = line.strip()
    if sport == "Agility":
        # Agility headers come in many shapes across the years, e.g.
        #   "Novice Springers            Owner(s)  Avg Score  YPS"
        #   "Excellent A Agility (Highest Average Score)"
        #   "Open English Springer Spaniel of the Year (Highest Average Score)"
        # Strip the boilerplate / column-label bleed and keep the class + level.
        t = re.sub(r"\(Highest Average Score\)", " ", t, flags=re.I)
        t = re.sub(r"Owner\(?s?\)?.*$", " ", t, flags=re.I)        # trailing col labels
        t = re.sub(r"English Springer Spaniel", " ", t, flags=re.I)
        t = re.sub(r"\bSpringers?\b|\bAgility\b|of the Year|"
                   r"Total\s+Score|Avg(?:erage)?\.?\s+Score|\bYPS\b", " ", t, flags=re.I)
        t = re.sub(r"\s+", " ", t).strip(" -–·")
        return t or "Overall"
    # Obedience / Rally: prefix the titling division for Obedience to disambiguate
    cat = re.sub(r"\s+", " ", t).strip().title()
    if sport == "Obedience" and division:
        div = division.title().replace(" Classes", "").replace(" Titling", "").strip()
        return f"{div}: {cat}"
    return cat


def looks_like_header(sport, stripped):
    if NOISE.search(stripped):
        return False
    if sport == "Agility":
        if "of the Year" in stripped:
            return True
        # per-class "Standings" headers (2013-2020): "Novice Springers …",
        # "Preferred Open Springers …", "Excellent A Agility …"
        return bool(re.match(r"^(Preferred\s+|Time\s*2\s*Beat|Premier\s+)?"
                             r"(Novice|Open|Excellent|Master|Veteran)\b", stripped, re.I)) \
            and len(stripped) < 80
    # Obedience/Rally: short line, mostly letters, no trailing score
    if len(stripped) > 70:
        return False
    if NUMERIC.match(re.split(r"\s{2,}", stripped)[-1]):
        return False
    # must contain a class keyword to avoid catching stray text
    return bool(re.search(r"Novice|Open|Utility|Excellent|Master|Advanced|Beginner|"
                          r"Graduate|Versatility|Preferred|Combined|Optional|Wild Card|"
                          r"Regular|Veteran|Brace|Team|Champion|Intermediate", stripped, re.I))


def parse_year_from_text(lines):
    for ln in lines[:6]:
        m = re.search(r"\b(20\d2)\b|\b(20[12]\d)\b", ln)
        if m:
            return next(g for g in m.groups() if g)
    return None


# ====================== position-based parser (pdfplumber) ==================
# The pdftotext -layout splitter drops a row whenever a long dog name leaves only
# a single space before the owner (the columns collapse). Reading word x-positions
# straight from the page recovers those rows and also captures the parenthesised
# "(n)" rank format used by some reports (e.g. 2023 Rally). Used for the common
# score-TRAILING layout; the rarer score-second PDFs (2024 Rally) keep the
# pdftotext path, which already parses them cleanly.
NUMERIC_FULL = re.compile(r"^\d+(?:\.\d+)?$")
RANK_TOK = re.compile(r"^\(?(\d+)\)?\.?$")        # 1 | 1. | (1) | (1).

# Some report fonts lack a ToUnicode map for ligatures, so pdfplumber emits
# "(cid:NNN)" where the ligature should be. Map the few that occur; strip any
# stray unmapped ones.
_CID = {"(cid:415)": "ti", "(cid:425)": "tt", "(cid:431)": "ff"}


def _fix_glyphs(s):
    for k, v in _CID.items():
        s = s.replace(k, v)
    return re.sub(r"\(cid:\d+\)", "", s)


def group_lines(words, ytol=3.0):
    """Group words into visual lines by top coordinate, each sorted left→right."""
    ws = sorted(words, key=lambda w: (round(w["top"], 1), w["x0"]))
    lines = []
    for w in ws:
        for ln in lines:
            if abs(ln["top"] - w["top"]) <= ytol:
                ln["words"].append(w)
                ln["top"] = (ln["top"] * ln["n"] + w["top"]) / (ln["n"] + 1)
                ln["n"] += 1
                break
        else:
            lines.append({"top": w["top"], "n": 1, "words": [w]})
    for ln in lines:
        ln["words"].sort(key=lambda w: w["x0"])
    lines.sort(key=lambda l: l["top"])
    return lines


def _detect_cols(lines):
    """Return (owner_x, score_x): the owner column's left edge and the score
    column's left edge, as the dominant modes over score-trailing data lines."""
    owner_x = collections.Counter()
    score_x = collections.Counter()
    for ln in lines:
        ws = ln["words"]
        if len(ws) >= 3 and NUMERIC_FULL.match(ws[-1]["text"]):
            score_x[round(ws[-1]["x0"])] += 1
            # largest gap among the non-score words ⇒ name|owner boundary
            gaps = [(ws[i]["x0"] - ws[i - 1]["x1"], round(ws[i]["x0"]))
                    for i in range(1, len(ws) - 1)]
            if gaps:
                owner_x[max(gaps)[1]] += 1
    if not owner_x or not score_x:
        return None, None
    return owner_x.most_common(1)[0][0], score_x.most_common(1)[0][0]


def _is_score_second(lines):
    """True when scores sit right after the rank (Rank Score Dog Owner), i.e. the
    rightmost token on rank-led lines is text, not a number (2024 Rally)."""
    second = trailing = 0
    for ln in lines:
        ws = ln["words"]
        if len(ws) >= 3 and RANK_TOK.match(ws[0]["text"]):
            if NUMERIC_FULL.match(ws[1]["text"]) and not NUMERIC_FULL.match(ws[-1]["text"]):
                second += 1
            elif NUMERIC_FULL.match(ws[-1]["text"]):
                trailing += 1
    return second > trailing and second >= 3


def parse_positions(path, year, sport, quarter, score_cols=1):
    """Parse a score-trailing sport PDF using word x-positions. score_cols=2 for
    Agility (Avg Score + YPS, assigned by magnitude)."""
    rows = []
    division = category = ""
    state = {"prev_rank": 0}
    tol = 6

    def name_words(ws):
        return [w for w in ws if w["x0"] < owner_x - tol]

    def has_real_name(ws):
        """A wrapped fragment is a name HEAD (vs a pure AKC-title overflow) if it
        carries a Title-case word like 'Muddy'/'Paws' rather than only CAPS titles."""
        return any(re.match(r"[A-Z][a-z]", w["text"]) for w in name_words(ws))

    def flush(anchors, orphans):
        """Build one category block: assign each orphan name-fragment to its anchor
        (name heads attach to the score line BELOW, title overflow to the line
        ABOVE), then emit a row per anchor in reading order."""
        if not category or not anchors:
            return
        anchors.sort(key=lambda a: a["ln"]["top"])
        omap = {id(a["ln"]): [] for a in anchors}
        for o in orphans:
            otop = o["top"]
            below = [a for a in anchors if a["ln"]["top"] > otop]
            above = [a for a in anchors if a["ln"]["top"] < otop]
            if has_real_name(o["words"]) and below:
                tgt = min(below, key=lambda a: a["ln"]["top"] - otop)
            elif above:
                tgt = max(above, key=lambda a: a["ln"]["top"])
            elif below:
                tgt = min(below, key=lambda a: a["ln"]["top"] - otop)
            else:
                continue
            if abs(tgt["ln"]["top"] - otop) <= 46:
                omap[id(tgt["ln"])].append(o)
        for a in anchors:
            ws, score_words = a["ln"]["words"], a["score_words"]
            # gather the whole entry (anchor + assigned orphans), top→bottom
            entry = [(a["ln"]["top"], ws)] + [(o["top"], o["words"]) for o in omap[id(a["ln"])]]
            entry.sort(key=lambda f: f[0])
            # rank: a far-left RANK_TOK on the entry's TOPMOST line (the rank digit
            # rides the name-head line when the score wraps to a lower line).
            top_ws = entry[0][1]
            first = top_ws[0]
            m = RANK_TOK.match(first["text"])
            rank_word = first if (m and first["x0"] < owner_x - 80) else None
            if rank_word:
                rank, tie = int(m.group(1)), ""
                state["prev_rank"] = rank
            elif state["prev_rank"] == 0:
                rank, tie = 1, ""            # first row of a class, rank "1" unprinted
                state["prev_rank"] = 1
            else:
                rank, tie = state["prev_rank"], "T"    # genuine tie with the dog above
            name = " ".join(w["text"] for _, fw in entry for w in name_words(fw)
                            if w is not rank_word and w not in score_words)
            owner = " ".join(w["text"] for w in ws if w not in score_words
                             and owner_x - tol <= w["x0"] < score_x - tol)
            if not owner.strip():
                for o in omap[id(a["ln"])]:
                    ow = " ".join(w["text"] for w in o["words"]
                                  if owner_x - tol <= w["x0"] < score_x - tol)
                    if ow:
                        owner = (owner + " " + ow).strip()
            nums = [w["text"] for w in score_words]
            if score_cols == 2:
                score = yps = ""
                for n in nums:
                    (yps := n) if float(n) <= 10 else (score := n)
                scores = [score, yps]
            else:
                scores = [nums[-1]] if nums else [""]
            if not name.strip():
                continue
            rows.append({"sport": sport, "year": year, "quarter": quarter,
                         "category": category, "rank": rank, "tie": tie,
                         "dog": _fix_glyphs(re.sub(r"\s+", " ", name).strip()),
                         "owner": _fix_glyphs(re.sub(r"\s+", " ", owner).strip()),
                         "score": scores[0], "score2": scores[1] if len(scores) > 1 else ""})

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
            if not words:
                continue
            lines = group_lines(words)
            owner_x, score_x = _detect_cols(lines)
            if not owner_x:
                continue
            anchors, orphans = [], []          # current category block (per page)
            for ln in lines:
                ws = ln["words"]
                text = " ".join(w["text"] for w in ws).strip()
                if not text or NOISE.search(text):
                    continue
                score_words = [w for w in ws
                               if NUMERIC_FULL.match(w["text"]) and w["x0"] >= score_x - 40]
                if score_words and len(ws) >= 2:
                    anchors.append({"ln": ln, "score_words": score_words})
                    continue
                if is_division(text):
                    flush(anchors, orphans); anchors, orphans = [], []
                    division = text; continue
                if looks_like_header(sport, text):
                    flush(anchors, orphans); anchors, orphans = [], []
                    category = category_label(sport, text, division)
                    state["prev_rank"] = 0; continue
                orphans.append({"ln": ln, "top": ln["top"], "words": ws})
            flush(anchors, orphans)
    return rows


# ---------------- dedicated Agility parser (two score columns) ---------------
# Agility reports use ~3 column orders across the years:
#   Name | Owner | Avg | YPS         (2013, 2017, 2019/2020 — scores trailing)
#   Name | Avg | YPS | Owner         (2015 — owner rightmost, owners wrap below)
# We locate the two score columns by MAGNITUDE (Avg 12-100, YPS <12) and the
# owner column by a strong left-edge mode, so column ORDER doesn't matter.
AG_CAT_RE = re.compile(r"^(Preferred\s+|Time\s*2\s*Beat\s+|Premier\s+)?"
                       r"(Novice|Open|Excellent|Master|Veteran)(\s+[AB])?\b", re.I)


def _ag_clean_cat(text):
    t = re.sub(r"\(Highest Average Score\)", " ", text, flags=re.I)
    t = re.sub(r"Owner\(?s?\)?.*$", " ", t, flags=re.I)
    t = re.sub(r"English Springer Spaniel|English Spaniel|\bES+\b|\bSpringers?\b|"
               r"\bAgility\b|of the Year|Name of Dog|2nd|\bAve?\b|Average|Score|\bYPS\b",
               " ", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip(" -–·,").title()
    if re.search(r"\bPreferred\b", t, re.I):      # normalise to "Preferred X"
        t = "Preferred " + re.sub(r"\bPreferred\b", " ", t, flags=re.I).strip()
    return re.sub(r"\s+", " ", t).strip() or "Overall"


def parse_agility(path, year, quarter):
    """Position-based Agility parser. Avg(0-100)+YPS are found by magnitude; the
    owner column by strong mode; name is the leftmost text. Handles owner on
    either side of the scores and owners/names that wrap to adjacent lines."""
    rows = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
            if not words:
                continue
            lines = group_lines(words)
            # 1. score columns by magnitude across all numeric tokens
            avg_xs, yps_xs = collections.Counter(), collections.Counter()
            for ln in lines:
                for w in ln["words"]:
                    if NUMERIC_FULL.match(w["text"]):
                        v = float(w["text"])
                        if 12 < v <= 100:
                            avg_xs[round(w["x0"])] += 1
                        elif 0 < v <= 12 and "." in w["text"]:
                            yps_xs[round(w["x0"])] += 1
            if not avg_xs or not yps_xs:
                continue
            avg_x = avg_xs.most_common(1)[0][0]
            yps_x = yps_xs.most_common(1)[0][0]
            score_l, score_r = min(avg_x, yps_x) - 6, max(avg_x, yps_x) + 40
            # 2. name_left + owner column from text-token left edges. ndata = number
            #    of data rows (avg+yps in the score band) sets the strong-mode bar.
            txt_x0 = collections.Counter()
            name_left = 9999
            ndata = 0
            for ln in lines:
                avg_here = yps_here = False
                for w in ln["words"]:
                    if not NUMERIC_FULL.match(w["text"]) and re.search(r"[A-Za-z]", w["text"]):
                        txt_x0[round(w["x0"])] += 1
                        name_left = min(name_left, w["x0"])
                    elif NUMERIC_FULL.match(w["text"]) and score_l <= w["x0"] <= score_r:
                        v = float(w["text"])
                        avg_here = avg_here or 12 < v <= 100
                        yps_here = yps_here or (0 < v <= 12 and "." in w["text"])
                if avg_here and yps_here:
                    ndata += 1
            # Owner column: prefer a strong text column to the RIGHT of the scores
            # (owner-rightmost layout, e.g. 2015 — unambiguous); else the strongest
            # text mode BETWEEN name and scores (owner-middle layout).
            after = {x: n for x, n in txt_x0.items() if x > score_r}
            before = {x: n for x, n in txt_x0.items()
                      if name_left + 45 < x < score_l}
            bar = max(3, 0.3 * ndata)
            if after and sum(after.values()) >= 0.5 * max(1, ndata):
                strong = [x for x, n in after.items() if n >= bar] or list(after)
                owner_x, owner_after = min(strong), True
            elif before:
                owner_x, owner_after = max(before, key=before.get), False
            else:
                continue

            def is_name(w):
                return name_left - 6 <= w["x0"] < (score_l if owner_after else owner_x - 6)

            def is_owner(w):
                if owner_after:
                    return w["x0"] >= owner_x - 6
                return owner_x - 6 <= w["x0"] < score_l

            # 3. anchors = lines carrying both an avg and a yps number
            blocks_cat = [None]

            def emit(category, prev_rank, anchors, orphans):
                anchors.sort(key=lambda a: a["top"])
                omap = {id(a): [] for a in anchors}
                for o in orphans:
                    cand = [a for a in anchors if abs(a["top"] - o["top"]) <= 40]
                    if cand:
                        omap[id(min(cand, key=lambda a: abs(a["top"] - o["top"])))].append(o)
                for a in anchors:
                    ws = a["ws"]
                    frag = [a] + omap[id(a)]
                    frag.sort(key=lambda f: f["top"])
                    rank_word = None
                    f0 = sorted(frag[0]["ws"], key=lambda w: w["x0"])[0] if frag[0]["ws"] else None
                    if f0:
                        m = RANK_TOK.match(f0["text"])
                        if m and f0["x0"] < name_left + 30:
                            rank_word = f0
                    name = " ".join(w["text"] for f in frag for w in sorted(f["ws"], key=lambda w: w["x0"])
                                    if is_name(w) and w is not rank_word)
                    owner = " ".join(w["text"] for f in frag for w in sorted(f["ws"], key=lambda w: w["x0"])
                                     if is_owner(w))
                    if rank_word:
                        rank, tie = int(RANK_TOK.match(rank_word["text"]).group(1)), ""
                        prev_rank[0] = rank
                    else:
                        prev_rank[0] += 1
                        rank, tie = prev_rank[0], ""
                    def fmt(v):
                        return f"{float(v):.2f}".rstrip("0").rstrip(".") if v else v
                    avg = fmt(next((w["text"] for w in a["ws"]
                                    if NUMERIC_FULL.match(w["text"]) and 12 < float(w["text"]) <= 100), ""))
                    yps = fmt(next((w["text"] for w in a["ws"]
                                    if NUMERIC_FULL.match(w["text"]) and 0 < float(w["text"]) <= 12
                                    and "." in w["text"]), ""))
                    name = _fix_glyphs(re.sub(r"\s+", " ", name).strip())
                    owner = _fix_glyphs(re.sub(r"\s+", " ", owner).strip())
                    if not name or not avg:
                        continue
                    rows.append({"sport": "Agility", "year": year, "quarter": quarter,
                                 "category": category, "rank": rank, "tie": tie,
                                 "dog": name, "owner": owner, "score": avg, "score2": yps})

            category = None
            prev_rank = [0]
            anchors, orphans = [], []
            for ln in lines:
                ws = ln["words"]
                text = " ".join(w["text"] for w in ws).strip()
                if not text or NOISE.search(text):
                    continue
                has_avg = any(NUMERIC_FULL.match(w["text"]) and 12 < float(w["text"]) <= 100
                              and score_l <= w["x0"] <= score_r for w in ws)
                has_yps = any(NUMERIC_FULL.match(w["text"]) and 0 < float(w["text"]) <= 12
                              and "." in w["text"] and score_l <= w["x0"] <= score_r for w in ws)
                if has_avg and has_yps:
                    anchors.append({"ws": ws, "top": ln["top"]})
                    continue
                m = AG_CAT_RE.match(text)
                is_hdr = (m and len(text) < 90) or "of the Year" in text
                if is_hdr and not (has_avg or has_yps):
                    if category is not None:
                        emit(category, prev_rank, anchors, orphans)
                    anchors, orphans = [], []
                    category = _ag_clean_cat(text)
                    prev_rank = [0]
                    continue
                if re.search(r"AVERAGE|Owner|Name of Dog|qualifying|based on|YPS|Score",
                             text, re.I) and not (has_avg and has_yps):
                    continue                       # column-label / footnote line
                orphans.append({"ws": ws, "top": ln["top"]})
            if category is not None:
                emit(category, prev_rank, anchors, orphans)
    return rows


def _agility_valid(r):
    """Same sanity bar the final quality filter uses — for picking the parser that
    recovers the most usable Agility rows per PDF (so we never regress a good year)."""
    try:
        s = float(r["score"])
    except (TypeError, ValueError):
        return False
    if not (0 < s <= 100) or re.match(r"^0\d", str(r["score"])):
        return False
    if not r["owner"].strip() or r["owner"][0].islower():
        return False
    if re.match(r"^[\d.]", r["dog"]):
        return False
    if r["score2"] and float(r["score2"]) > 12:
        return False
    # a real owner has a lowercase letter ("P Salzwedel"); an AKC-title string that
    # leaked across the column boundary ("CD BN RA JH") does not — reject those.
    if not re.search(r"[a-z]", r["owner"]):
        return False
    return True


def _parse_pdftotext(lines, sport, year, quarter):
    """Original line-based parser (score-second Rally, Agility 'of the Year')."""
    rows, division, category, prev_rank = [], "", "", 0
    for raw in lines:
        s = raw.strip()
        if not s:
            continue
        if is_division(raw):
            division = s
            continue
        if looks_like_header(sport, s):
            category = category_label(sport, s, division)
            prev_rank = 0
            continue
        parsed = split_row(s)
        if not parsed or not category:
            continue
        rank, tie, dog, owner, scores = parsed
        if rank is None:
            rank = prev_rank
        else:
            prev_rank = rank
        rows.append({"sport": sport, "year": year, "quarter": quarter,
                     "category": category, "rank": rank, "tie": tie,
                     "dog": dog, "owner": owner,
                     "score": scores[0], "score2": scores[1] if len(scores) > 1 else ""})
    return rows


def parse_sport_pdf(path, year, sport, quarter):
    lines = layout_lines(path)
    true_year = parse_year_from_text(lines) or year
    # Agility: no single parser handles the ~3 historical column layouts, so run
    # both the proven path and the position parser and keep whichever recovers
    # MORE valid rows for this PDF — recovers the dropped years without ever
    # regressing the good ones.
    if sport == "Agility":
        if any("of the Year" in ln for ln in lines[:4]):
            old = _parse_pdftotext(lines, sport, true_year, quarter)
        else:
            old = parse_agility_standings(lines, true_year, quarter)
        new = parse_agility(path, true_year, quarter)
        best = new if sum(map(_agility_valid, new)) > sum(map(_agility_valid, old)) else old
        return best, true_year
    # Obedience/Rally: score-second PDFs (2024 Rally) parse cleanly with pdftotext;
    # every other (score-trailing) PDF goes through the robust position parser.
    if sport in ("Obedience", "Rally"):
        pwords = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                pwords += page.extract_words(use_text_flow=False, keep_blank_chars=False)
        if not _is_score_second(group_lines(pwords)):
            return parse_positions(path, true_year, sport, quarter), true_year
    return _parse_pdftotext(lines, sport, true_year, quarter), true_year


def main():
    manifest = json.load(open(os.path.join(HERE, "sports_manifest.json")))
    allrows = []
    for m in manifest:
        path = os.path.join(PDFS, m["file"])
        rows, ty = parse_sport_pdf(path, m["year"], m["sport"], m["quarter"])
        flag = "" if ty == m["year"] else f"  [PDF says {ty}!]"
        cats = len({r["category"] for r in rows})
        print(f"{m['file']:28} -> {len(rows):3d} rows, {cats:2d} cats{flag}")
        allrows.extend(rows)
    # the 2019/2020 Agility links point to older files (true year differs) and
    # duplicate the real reports — dedupe on the full identity.
    seen, deduped = set(), []
    for r in allrows:
        k = (r["sport"], r["year"], r["quarter"], r["category"], r["dog"], r["score"])
        if k in seen:
            continue
        seen.add(k); deduped.append(r)
    if len(deduped) != len(allrows):
        print(f"deduped {len(allrows) - len(deduped)} mislabeled/duplicate rows")
    allrows = deduped

    # Quality filter: a few historical Agility reports use column orders the
    # parser can't disentangle (owner ends up empty / score non-numeric). Drop
    # those rows rather than ship garbage, and report the affected years.
    def valid(r):
        if not NUMERIC.match(str(r["score"])):
            return False
        # Obedience/Rally parse cleanly across all years (Combined classes can
        # push scores to ~400/200, so no upper cap). Agility's historical reports
        # use several incompatible column orders; keep only rows that pass strict
        # sanity so we never ship a garbled Agility row.
        if r["sport"] == "Agility":
            if not (0 < float(r["score"]) <= 100):
                return False
            if re.match(r"^0\d", str(r["score"])):          # "076" = mis-parse
                return False
            if not r["owner"].strip() or r["owner"][0].islower():  # truncated owner
                return False
            if not re.search(r"[a-z]", r["owner"]):         # AKC-title string, not an owner
                return False
            if re.match(r"^[\d.]", r["dog"]):               # YPS leaked into name
                return False
            if r["score2"] and float(r["score2"]) > 12:     # YPS out of range
                return False
        return True
    clean = [r for r in allrows if valid(r)]
    dropped = [r for r in allrows if not valid(r)]
    if dropped:
        from collections import Counter
        byyr = Counter((r["sport"], r["year"]) for r in dropped)
        print("dropped invalid rows:", dict(byyr))
    allrows = clean
    fields = ["sport", "year", "quarter", "category", "rank", "tie", "dog", "owner", "score", "score2"]
    with open(os.path.join(HERE, "sports.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(allrows)
    json.dump(allrows, open(os.path.join(HERE, "sports.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\nTOTAL {len(allrows)} sport rows -> sports.csv / .json")


if __name__ == "__main__":
    main()

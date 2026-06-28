#!/usr/bin/env python3
"""Compare calculator output (computed from raw AKC .xls) vs the official
published Q1 2026 rankings (parsed from the ESSFTA PDFs into sports.json).

Writes comparison_Q1_2026.md (human-readable, per category) + a summary.
Only Q1 2026 has raw data; this is the validation harness for every future
quarter too.
"""
import pandas as pd, json, re, os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
QUAL = {"QLFY", "1", "2", "3", "4"}

# ---- AKC title tokens to strip when matching names across raw vs PDF ----
TITLE = re.compile(r"^(GCH[A-Z]?\d?|CH|DC|NAFC|FC|AFC|OTCH\d*|MACH\d*|PACH\d*|AGCH|RACH\d*|VCCH|"
                   r"CD|CDX|UD|UDX\d*|OM\d*|OGM|GO|GN|VER|BN|PCD|PUD|RN|RA|RE|RAE\d*|RM\d*|RI|"
                   r"NA|NAJ|OA|OAJ|AX|AXJ|MX[A-Z]?\d*|MJ[A-Z]?\d*|MF[A-Z]?\d*|XF|NF|OF|T2B\d*|"
                   r"PAD|PJD|PDS|PJS|TQX|NAP|NJP|OAP|OJP|AXP|AJP|MXP\d*|MJP\d*|PAX\d*|MFP[A-Z]?|"
                   r"JH|SH|MH|TD|TDX|FDC|CGC|CGCA|CGCU|TKN|TKI|TKA|TKE|TKP|ATT|BCAT|DCAT|FCAT|"
                   r"VHMP|ACT\d?J?|FITB?|FITS?|FTN?|FTR?|SWN|SWA|SWE|SCN|SEN|SIN|SEE|SIA|SHDN|SBN|"
                   r"DS|DJ|DJA|DN|RATN|RATO|RATCH|VCD\d|SEM|SBM|BM|STR|PJDP|PADP|MFPB|MFPS|TQXP|"
                   r"T2BP\d*|MXPB\d*|MJPB\d*|MXPC|MJPC|II|III|IV|V)$", re.I)


def core(name):
    """Reduce a dog name to its distinctive words (strip titles/punct)."""
    name = str(name).replace(" ", " ").replace("’", "'")
    words = re.sub(r"[^A-Za-z' &-]", " ", name).split()
    i = 0
    while i < len(words) and TITLE.match(words[i]):
        i += 1
    j = i
    while j < len(words) and not TITLE.match(words[j]):
        j += 1
    nm = words[i:j] if j > i else words[i:]
    return re.sub(r"[^a-z]", "", "".join(nm).lower())


def load_raw(path):
    df = pd.read_excel(path, header=6)
    df.columns = [str(c).strip() for c in df.columns]
    df = df[df["Reg Number"].notna() & df["Reg Number"].astype(str).str.strip().ne("nan")].copy()
    df["Dog Name"] = df["Dog Name"].astype(str).str.replace(" ", " ", regex=False).str.strip()
    df["Primary Class"] = df["Primary Class"].astype(str).str.strip()
    df["Placement"] = df["Placement"].astype(str).str.strip()
    for c in ["Score", "Course Distance", "Dog Time"]:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def best3(df, classmap):
    out = defaultdict(list)
    for (reg, cls), g in df[df["Primary Class"].isin(classmap) & df["Placement"].isin(QUAL)].groupby(["Reg Number", "Primary Class"]):
        s = g["Score"].dropna()
        if len(s) < 3:
            continue
        avg = round(s.sort_values(ascending=False).head(3).mean(), 2)
        out[classmap[cls]].append((avg, g["Dog Name"].iloc[0]))
    return {k: sorted(v, reverse=True) for k, v in out.items()}


def yoy(df, std, jww):
    dogs = {}
    sub = df[df["Primary Class"].isin([std, jww]) & df["Placement"].isin(QUAL)]
    sub = sub.assign(d=sub["Event Date"].dt.date, yps=sub["Course Distance"] / sub["Dog Time"])
    for reg, g in sub.groupby("Reg Number"):
        dates = {}
        for dt, gg in g.groupby("d"):
            for _, r in gg.iterrows():
                slot = dates.setdefault(dt, {})
                key = "std" if r["Primary Class"] == std else "jww"
                slot.setdefault(key, r["yps"])
        qq = [(s["std"] + s["jww"]) / 2 for s in dates.values() if "std" in s and "jww" in s]
        if len(qq) >= 10:
            dogs[reg] = (round(sum(sorted(qq, reverse=True)[:10]) / 10, 2), g["Dog Name"].iloc[0])
    return sorted(dogs.values(), reverse=True)


OBED = {"BNOVA": "Beginner Novice A", "BNOVB": "Beginner Novice B", "ONOVA": "Novice A", "ONOVB": "Novice B",
        "OOPENA": "Open A", "OOPENB": "Open B", "OUTILA": "Utility A", "OUTILB": "Utility B",
        "GRADNOVR": "Graduate Novice", "GRADOPNR": "Graduate Open", "POPEN": "Preferred Open"}
RALLY = {"RNOVA": "Novice A", "RNOVB": "Novice B", "RADVA": "Advanced A", "RADVB": "Advanced B",
         "REXCA": "Excellent A", "REXCB": "Excellent B", "RINT": "Intermediate", "RMAST": "Master"}


def computed(sport):
    df = load_raw(os.path.join(HERE, f"raw_akc/ESS {sport} 1Q 2026.xls"))
    if sport == "Obedience":
        return best3(df, OBED)
    if sport == "Rally":
        return best3(df, RALLY)
    cats = {"ESS of the Year": yoy(df, "AGEXCB", "JWWEXCB"),
            "Preferred ESS of the Year": yoy(df, "AGEXCBP", "JWWEXCBP")}
    cats.update(best3(df, {"AGNOVB": "Novice", "AGOPEN": "Open", "AGEXCA": "Excellent A"}))
    return cats


def official(sport):
    """Official published Q1 2026 from sports.json, by simplified category."""
    out = defaultdict(list)
    for r in json.load(open(os.path.join(HERE, "sports.json"), encoding="utf-8")):
        if r["sport"] == sport and r["year"] == "2026":
            cat = r["category"].split(": ")[-1]
            out[cat].append((r["rank"], r["dog"], r["score"]))
    return {k: sorted(v) for k, v in out.items()}


def main():
    lines = ["# ESSFTA Q1 2026 — Calculator (from raw AKC) vs Official Published\n"]
    lines.append("Computed = our calculator on Rob Garrett's raw .xls. "
                 "Official = the published ESSFTA PDF (as parsed into the widget).\n")
    tally = defaultdict(int)
    rowlog = []
    for sport in ["Obedience", "Rally", "Agility"]:
        comp, off = computed(sport), official(sport)
        lines.append(f"\n## {sport}\n")
        cats = list(dict.fromkeys(list(off.keys()) + list(comp.keys())))
        for cat in cats:
            o = off.get(cat, [])
            c = comp.get(cat, [])
            if not o and not c:
                continue
            lines.append(f"\n### {cat}\n")
            lines.append("| # | Official (dog · score) | Computed (dog · score) | Status |")
            lines.append("|---|---|---|---|")
            n = max(len(o), len(c))
            for i in range(n):
                orow = o[i] if i < len(o) else None
                crow = c[i] if i < len(c) else None
                odog = orow[1] if orow else ""
                osc = orow[2] if orow else ""
                cdog = crow[1] if crow else ""
                csc = crow[0] if crow else ""
                COMBINED = "High Combined" in cat or "High Triple" in cat or cat == "Open B/Utility A or B"
                samescore = orow and crow and abs(float(osc) - float(csc)) < 0.05
                samedog = orow and crow and (core(odog) == core(cdog)
                                             or core(odog) in core(cdog) or core(cdog) in core(odog))
                if orow and crow:
                    if samedog and samescore:
                        status = "✅ match"
                    elif samescore:                       # same number, name noise across sources
                        status = "✅ match (name fmt)"
                    elif samedog:
                        status = f"⚠ score {osc}≠{csc}"
                    else:
                        status = f"↕ ordering ({osc} vs {csc})"
                elif orow:
                    status = "▢ combined cat (not computed yet)" if COMBINED else "△ in official, not in raw (snapshot/legs)"
                else:
                    status = "＋ computed, missing from our PDF parse"
                tally[status.split()[0]] += 1
                rowlog.append([sport, cat, i + 1, odog, osc, cdog, csc, status])
                lines.append(f"| {i+1} | {odog[:40]} · {osc} | {cdog[:40]} · {csc} | {status} |")
    # summary
    summ = ["\n## Summary\n", "| Status | Count |", "|---|---|"]
    for k, v in sorted(tally.items(), key=lambda x: -x[1]):
        summ.append(f"| {k} | {v} |")
    lines = lines[:2] + summ + lines[2:]
    open(os.path.join(HERE, "comparison_Q1_2026.md"), "w", encoding="utf-8").write("\n".join(lines))
    pd.DataFrame(rowlog, columns=["sport", "category", "rank", "official_dog", "official_score",
                                  "computed_dog", "computed_score", "status"]).to_csv(
        os.path.join(HERE, "comparison_Q1_2026.csv"), index=False)
    print("Status tally:", dict(tally))
    print("wrote comparison_Q1_2026.md and .csv")


if __name__ == "__main__":
    main()

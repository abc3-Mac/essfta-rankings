#!/usr/bin/env python3
"""Feed the rebuilt rankings_calculator.html the six per-quarter AKC files and
compare every computed category against the Q2-audit's validated outputs
(raw_akc/audit_2026Q2/computed/computed_sports.json), plus the specific
new-feature targets from comparison_Q2_2026.md."""
import json, sys
from playwright.sync_api import sync_playwright

REPO = "/Users/abc3/Documents/essfta-breed-data"
FILES = [f"{REPO}/raw_akc/ESS {s} {q} 2026.xls"
         for s in ("Obedience", "Rally", "Agility") for q in ("1Q", "2Q")]

audit = json.load(open(f"{REPO}/raw_akc/audit_2026Q2/computed/computed_sports.json"))

fails = []
def check(label, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + label + ("" if ok else f"  -- {detail}"))
    if not ok:
        fails.append(label)

with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page()
    page.goto(f"file://{REPO}/rankings_calculator.html")
    page.wait_for_function("typeof XLSX!=='undefined'")
    page.set_input_files("#ecInput", FILES)
    page.wait_for_function("Object.keys(DATA).length===3", timeout=30000)
    data = page.evaluate("DATA")
    meta = page.evaluate("META")
    b.close()

# --- new-feature targets (comparison_Q2_2026.md) ---
comb = data["Obedience"].get("Combined Open B/Utility", [])
check("Obedience Combined lists exactly Polesitter at 397.80 (>=3-trial gate)",
      len(comb) == 1 and comb[0]["score"] == "397.80" and "Polesitter" in comb[0]["dog"],
      json.dumps(comb)[:200])
pnov = data["Obedience"].get("Preferred Novice", [])
check("Preferred Novice = Hail Mary 198.33 (the card's wrong 'No Dogs Eligible')",
      len(pnov) == 1 and pnov[0]["score"] == "198.33" and "Hail Mary" in pnov[0]["dog"],
      json.dumps(pnov)[:200])
cho = data["Rally"].get("Choice", [])
check("Rally Choice = 98.00/96.00/84.00 (Ledgend/Silver Oak/Prairie Rose)",
      [r["score"] for r in cho] == ["98.00", "96.00", "84.00"]
      and "Ledgend" in cho[0]["dog"] and "Silver Oak" in cho[1]["dog"] and "Prairie Rose" in cho[2]["dog"],
      json.dumps(cho)[:300])

# --- regression: every audit category must match on (dog, score, legs) ---
for sport in ("Obedience", "Rally", "Agility"):
    for cat, want in audit["sports"][sport]["categories"].items():
        got = data[sport].get(cat, [])
        w = [(r["dog"], r["score"], r["legs"]) for r in want]
        g = [(r["dog"], r["score"], r["legs"]) for r in got]
        check(f"{sport} / {cat} ({len(w)} rows)", w == g,
              f"want {json.dumps(w[:3])} got {json.dumps(g[:3])}")

print("\nMETA:", json.dumps(meta))
sys.exit(1 if fails else 0)

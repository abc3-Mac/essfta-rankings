#!/usr/bin/env python3
"""Feed the rebuilt rankings_calculator.html the six per-quarter AKC files and
compare every computed category against the Q2-audit's validated outputs
(raw_akc/audit_2026Q2/computed/computed_sports.json), plus the specific
new-feature targets from comparison_Q2_2026.md.

Baselines follow the FINAL club rules (decided 2026-09-16): S lines — the same
run recorded a second time in a concurrent specialty's judge's book — are NEVER
counted, in rally exactly as in obedience (Polly adopted Betsy's reading); ties
are listed alphabetically by registered name and share a rank; Combined Open
B/Utility requires a minimum of five combined trials. Rally values = the
corrected Q2 card (cross-validated vs an independent Python recompute)."""
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
check("Obedience Combined lists exactly Polesitter at 397.80 (min 5 combined trials — Betsy 9/16; he has 15, Brownwell's 1 excluded)",
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

# --- spot checks under the final 9/16 rules (one run, one score) ---
def dog(cat, sub):
    return next((r for r in data["Rally"].get(cat, []) if sub in r["dog"]), None)

r = dog("Intermediate", "Thor-Adore")
check("Rally Thor-Adore NOT listed in Intermediate (2 real runs under the final rule)",
      r is None, json.dumps(r))
r = dog("Advanced B", "Crackl'N Fire")
check("Rally Crackl'n Fire NOT listed in Advanced B (his S-line copies are not scores; 2 real runs)",
      r is None, json.dumps(r))
r = dog("Novice A", "Duck Duck Goose")
check("Rally Segre's Duck Duck Goose Novice A = 89.67 (98+89+82; the S-line 98 not double-counted)",
      r is not None and r["score"] == "89.67", json.dumps(r))
r = dog("Novice B", "Cerise Valor")
check("Rally Cerise Valor Novice B = 95.67 (99+98+90 real runs)", r is not None and r["score"] == "95.67",
      json.dumps(r))
advb = data["Rally"].get("Advanced B", [])
check("Advanced B tie order = Betsy Ross / Jimmy / Polesitter, all 100.00 (alpha by registered name)",
      len(advb) >= 3 and [r["score"] for r in advb[:3]] == ["100.00"] * 3
      and "Betsy Ross" in advb[0]["dog"] and "Yellowstone" in advb[1]["dog"] and "Polesitter" in advb[2]["dog"],
      json.dumps([r["dog"][:40] for r in advb[:3]]))
r = dog("High Combined", "Ledgend")
check("Rally Balmor's Ledgend High Combined = 195.33 (card's 196.33 is a documented card-side question)",
      r is not None and r["score"] == "195.33", json.dumps(r))
r = dog("High Triple", "Polesitter")
check("Rally Polesitter High Triple = 299.67 (card's 299.33 is a documented pairing question)",
      r is not None and r["score"] == "299.67", json.dumps(r))

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

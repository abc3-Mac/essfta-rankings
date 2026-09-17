# Springer Spotlight — Ranking/Standings Coverage Survey

Surveyed 2026-09-16. Covers the 18 back issues downloaded to `pdfs/` (see `issues.csv`),
spanning **January 2022 – June 2026**. Page numbers below are **actual PDF page indices**
(1-based, as pdfplumber counts them), NOT the page numbers printed on the magazine layout
— the two differ by a few pages because of the cover/TOC. Full per-page extracted text for
every issue is cached in `extracted_text/*.txt` (not a deliverable folder called for in the
task, but left in place for the next pass) with `=== PAGE N ===` markers.

Search terms used: "Quarterly", "Rankings", "Standings", "Breed", "Group", "Obedience",
"Rally", "Agility", "Junior", "High Point", "Top Ten", plus manual verification of every
hit (many "Breed"/"Group"/"High Point" hits are prose, not tables — those are excluded
below; only issues with an actual ranking/scorecard table are listed).

## What "the archive already has" means here

`essfta_rankings.db` → view `rankings` (sport, year, quarter). Current coverage, from
`select sport, year, quarter, count(*) from rankings group by 1,2,3`:

- **Conformation**: Q4 only, every year 2013–2025, plus 2026 Q1–Q2
- **Obedience**: Q4 only, every year 2013–2025, plus 2026 Q1–Q2
- **Rally**: Q4 only, every year 2013–2025, plus 2026 Q1–Q2
- **Agility**: Q4 only 2013–2019, then a gap 2020–2022, then 2023 Q2 only, 2024 Q4, 2025 Q4, 2026 Q1–Q2
- **Juniors**: not a sport in the db at all (the `rankings` view unions only `conformation` + `sports`, and `sports` has no Juniors rows)

The DB's "quarter" label is really "as of AKC data pulled around year-end" — it does not
mean the underlying dog-show results were confined to Q4; it's just when ESSFTA compiled
the annual cumulative standings. Spotlight's own scorecards are explicitly **cumulative
year-to-date** snapshots (see date ranges below), so a direct one-to-one quarter mapping
needs care in the next parsing pass.

## Per-issue findings

| Issue | Vol/date | Obedience | Rally | Agility | Breed/Group (Conformation) | Juniors |
|---|---|---|---|---|---|---|
| `SpringerSpotlight_2022-01.pdf` | Vol 32, Jan 2022 | pp.25–27 (2021, Jan–Sep 2021 cumulative) | pp.28–32 (2021, same range) | pp.33–36 (2020/2021 label mismatch in header; body covers Jan–Dec 2021) | pp.21–24 (Breed Competition + Group Competition, dogs & bitches split) | none |
| `SpringerSpotlight_2022-06.pdf` | June 2022 | none | none | none | none | none |
| `SpringerSpotlight_2022-09.pdf` | Sep 2022 | pp.25–26 (2022 scorecard) | pp.22–24 (2022 scorecard) | none | none | none |
| `SpringerSpotlight_2022-12.pdf` | Dec 2022 | pp.19–21, 26 (Jan–Sep '22 label, body extends into Q4 data) | pp.23–25 | none | none | none |
| `SpringerSpotlight_2023-03.pdf` | Mar 2023 | pp.22–25 (2022 scorecard, year-end) | pp.26–29 (2022 scorecard) | none | none | none |
| `SpringerSpotlight_2023-06.pdf` | June 2023 | pp.23–24 (2023 YTD) | p.25 (2023 YTD) | p.22 (2022 scorecard, late) | none | none |
| `SpringerSpotlight_2023-09.pdf` | Sep 2023 | pp.32–33 (2023 YTD) | pp.34–37 (2023 YTD) | pp.30–31 (2022 scorecard, late) | none | none |
| `SpringerSpotlight_2023-12.pdf` | Vol 40, Dec 2023 | pp.43–45 (2023 YTD) | pp.40–42 (2023 YTD) | pp.36–39 (2022 & 2023 scorecards mixed) | pp.34–35 (Breed Competition + Group Competition) | none |
| `SpringerSpotlight_2024-03.pdf` | Mar 2024 | pp.38–41 (2023 year-end) | pp.34–37 (2023 year-end) | pp.29–33 (2023 year-end) | none | none |
| `SpringerSpotlight_2024-06.pdf` | June 2024 | pp.38–40 (2024 YTD) | pp.41–45 (2024 YTD) | p.37 (2024 Agility scorecard) | pp.33–36 (Breed Competition + Group Competition, dogs/bitches) | none |
| `SpringerSpotlight_2024-09.pdf` | Vol 43, Sep 2024 | **none** — no scorecards this issue at all (TOC confirms: no Obedience/Rally/Agility/Breed section listed; issue instead covers Nationals/Top-20 photos, Juniors & Pee Wees article, Bench Governor report) | | | | none (only a "Juniors and Pee Wees" feature article, not a ranking table) |
| `SpringerSpotlight_2024-12.pdf` | Dec 2024 | none | none | pp.36–38 (Jan 1–Sep 30, 2024 cumulative) | pp.39–40 (Breed Competition Report) | none |
| `SpringerSpotlight_2025-03.pdf` | Mar 2025 | pp.47–50 (Jan 1–Dec 31, 2024 full year) | pp.43–45 (same) | pp.38–42 (same) | none (only a prose mention of "Best of Breed Competition" at a specific show, not a ranking table) | none |
| `SpringerSpotlight_2025-06.pdf` | June 2025 | pp.28–30 (2025 Jan–Mar, plus a "2024 Corrected" reprint table) | pp.31–32 (Jan–Mar 2025) | none | pp.24–27 (Breed Competition, Jan 1–Mar 31 2025) | none |
| `SpringerSpotlight_2025-09.pdf` | Sep 2025 (UPDATED) | pp.103–104 (Jan–June 2025) | pp.105–107 (Jan–June 2025) | pp.108–110 (Jan–June 2025) | pp.99–102 (Breed + Group Competition, Jan–June 2025) | none |
| `SpringerSpotlight_2025-12.pdf` | Dec 2025 (final revised) | p.51 + pp.53–56ish ("2025 3rd Q Obedience Scorecard", i.e. Jan–Sep 2025 cumulative) | pp.53–56ish (Rally, same range) | pp.57–59ish (Agility, same range) | pp.47–50 (Breed/Group Competition — first issue to use the unified "ESSFTA RANKINGS" masthead) | none |
| `SpringerSpotlight_2026-03.pdf` | Vol 48, Mar 2026 | pp.38–39 ("2025 4th Q Obedience Scorecard", full year 2025) | pp.41–42 ("Rally Rankings 2026" — despite the header this table is dated Jan 1–Mar 31, i.e. really 2026 Q1; double-check when parsing) | pp.40–41 ("ESSFTA Rankings — Agility") | pp.30–33 (Breed Competition + Group Competition, "January to December 2025" — full year) | none |
| `SpringerSpotlight_2026-06.pdf` | June 2026 | p.40 ("2026 1st Q Obedience Scorecard", Jan–Mar 2026) | pp.41–42 ("Rally Rankings 2026", Jan–Mar) | pp.42–43 (Agility) | none (no Breed/Group table this issue) | none |

**Juniors: confirmed absent from every single Spotlight issue surveyed.** No issue has a
Junior Handler ranking/scorecard table; "Junior Handler" only appears in prose (event
recaps) or in the separate, non-Spotlight `2016-Juniors-Q4.pdf` file described below.

## Layout notes (for the next parser pass)

- **2022–2024 issues** ("Scorecard" era): each sport's table is broken into AKC titling
  sub-classes (Beginner Novice A/B, Novice A/B, Open A/B, Utility A/B for Obedience;
  Novice/Open/Excellent/Masters-ish tiers for Agility, etc.), each its own mini-table
  with columns `Rank | Dog's Name | Owner(s) | Score`. Bordered in some issues, borderless
  (whitespace-aligned) in others — pdfplumber's plain `extract_text()` preserves column
  order well enough to regex-split on trailing numeric score, but table-line detection
  (`extract_table()`) will likely need per-issue tuning since border style varies.
- **`SpringerSpotlight_2022-01.pdf` has a PDF-extraction quirk**: the word "SCORECARD" is
  broken by a stray space as "SCOREC ARD" in every heading on the sport-scorecard pages —
  a font/kerning artifact from that issue's original layout software, not a bug in this
  survey. Any parser matching on the literal string "SCORECARD" needs a whitespace-tolerant
  regex for this issue specifically (confirmed only in the Jan 2022 issue; not seen in
  later ones).
- **Breed/Group ("Conformation") tables**, where present, are always split into 4 sub-tables:
  Breed Competition–Dogs, Breed Competition–Bitches, Group Competition–Dogs, Group
  Competition–Bitches, with columns for BIS/BIS1/GRP1-4 placement counts and a Total
  Points column — this is a genuinely different, more detailed table shape than the
  Q4-only Conformation rows currently in `essfta_rankings.db`, so the existing parser will
  need new column-mapping logic, not just a drop-in reuse.
- **Starting with `SpringerSpotlight_2025-12.pdf` (Dec 2025)**, the magazine consolidated
  everything under one "ESSFTA RANKINGS" masthead repeated on every rankings page,
  replacing the old per-sport "20XX Scorecard" headers. This is a cleaner anchor to
  regex-search on going forward, but it also means older and newer issues need different
  header-detection patterns.
- Every issue's rankings section carries a footer credit line — `"Rankings compiled by
  Betsy Baird from AKC electronic reports"` (co-credited with Polly Mumma starting
  2023-09) — that's a reliable per-page fingerprint for "this is a rankings page" if
  header detection ever misses one.
- Scorecard date ranges are **not aligned to a single calendar quarter** — they are
  cumulative year-to-date snapshots as of the magazine's press date (e.g. "Jan 1–Sep 30",
  "Jan 1–Dec 31", "Jan 1–Mar 31"). A later parser will need to infer the actual quarter
  from the stated date range, not assume Q1–Q4 buckets.

## Summary: year × sport × quarter found in Spotlight vs. already in archive

Legend: **NEW** = date range not represented in `essfta_rankings.db` at all for that
sport/year; **overlaps** = db already has a same-year entry (usually the Q4/year-end db
row is the AKC-official final tally, while Spotlight's mid-year snapshots are NEW
*within-year* granularity even when the year itself isn't new).

| Year | Obedience in Spotlight | Rally in Spotlight | Agility in Spotlight | Breed/Group in Spotlight | vs. archive |
|---|---|---|---|---|---|
| 2021 (reported in Jan 2022 issue) | Jan–Sep 2021 YTD | Jan–Sep 2021 YTD | Jan–Dec 2021 | Breed+Group (undated range, ~2021) | db has 2021 Q4 for Obed/Rally/Conformation only — **Spotlight's mid-year 2021 snapshots and the 2021 Agility numbers are NEW** (db has no 2021 Agility row at all — this fills part of the 2020–2022 Agility gap) |
| 2022 | Jan–Sep '22, year-end '22 (3 snapshots across issues) | same | only a late "2022 scorecard" in the Jun/Sep 2023 issues (no 2022 Agility snapshot found in the 2022 issues themselves) | Breed+Group in the Jan 2022 issue only (covers ~2021) | db has 2022 Q4 Obed/Rally/Conformation; **no 2022 Agility in db at all** — Spotlight's late-published "2022 Agility Scorecard" (found in the 2023-06 and 2023-09 issues) is the only lead for filling that gap |
| 2023 | multiple YTD snapshots (Jun, Sep, Dec, and year-end reprint in Mar 2024) | same | year-end (Mar 2024 issue) and a late "2022 vs 2023" mix in Dec 2023 issue | Breed+Group in the Dec 2023 issue (year-end 2023) | db has 2023 Q4 Obed/Rally/Conformation; **db's only 2023 Agility row is Q2 (12 rows) — Spotlight's year-end 2023 Agility table (Mar 2024 issue) is a different/NEW snapshot** |
| 2024 | Jun (YTD), Sep 2024 issue has NONE, Dec (Jan–Sep YTD), Mar 2025 (full year) | same pattern | Jun, Dec (Jan–Sep YTD), Mar 2025 (full year) | Jun 2024 issue (YTD) and Dec 2024 issue (year-end) | db has 2024 Q4 for all 4 sports — **Spotlight's Jun/Sep-cumulative snapshots for all sports are NEW intra-year granularity; the Breed/Group table shape itself is new/richer than what's in the db** |
| 2025 | Mar (Q1), Jun (Q1 YTD + a "2024 corrected" reprint), Sep (H1 YTD), Dec (9-month YTD) | same | Sep (H1 YTD), Dec (9-month YTD) — no Mar/Jun Agility table found | Jun (Q1), Sep (H1), Dec/Mar-2026 (year-end 2025) | db has 2025 Q4 for all 4 sports plus scattered Agility Q4-only — **all the Q1/H1/9-month intra-2025 Spotlight snapshots are NEW**, and the Breed/Group tables are the richest lead for backfilling 2025 Conformation detail |
| 2026 | Mar (Q4-2025 reprint), Jun (Q1 2026) | Mar & Jun (both labeled "2026" but Mar's table is Jan–Mar, i.e. actually Q1) | Mar, Jun | Mar (year-end 2025) — Jun issue has none | db already has 2026 Q1–Q2 for all sports — mostly **overlap**, useful mainly as a cross-check/second source |

**Known gaps confirmed by this survey:**
- **Pre-2013**: Spotlight's earliest digitally-archived issue on the site is January 2022
  (Vol 32) — nothing pre-2022 is in the WordPress media library under any "spotlight",
  "newsletter", "quarterly", "magazine", or "bulletin" search term. The Internet Archive
  Wayback Machine was unreachable during this survey (503/429 errors) and was not
  checked further — worth a follow-up if pre-2022 issues are needed.
- **Agility 2020–2022**: partially fillable — see per-year notes above (2021 fully new,
  2022 only via a late-published table in the 2023 issues).
- **Non-Q4 quarters before 2026**: extensively fillable — nearly every 2022–2025 issue
  carries a mid-year cumulative snapshot for Obedience/Rally, and most for Agility.
- **Juniors**: Spotlight is **not** a viable source — zero Junior ranking tables found in
  any of the 18 issues. The only Juniors ranking artifact found anywhere on the site is a
  standalone (non-Spotlight) file, see below.

## Important discovery outside the Spotlight scope (flagged, not downloaded)

While enumerating the site's PDF media library (`wp-json/wp/v2/media?mime_type=application/pdf`,
379 total PDFs) to find the Spotlight issues, a **separate, much more directly
machine-parseable set of standalone quarterly ranking PDFs** turned up — e.g.
`2013-Rally-Q4.pdf`, `2016-Juniors-Q4.pdf`, `2024-Conformation-Q3.pdf`,
`2025-Agility-Q2.pdf`, `2026-Rally-Q1.pdf`, 65 files total spanning 2013–2026, including
several **non-Q4 quarters and the one 2016 Juniors file** that are gaps in the current
archive. These are plain per-sport/per-quarter PDFs (not magazine-embedded), almost
certainly the same underlying data ESSFTA already compiles for the Spotlight tables, in a
much cleaner one-table-per-file shape. This is out of scope for the current Spotlight-only
task and was **not downloaded**, but it's a strong lead for backfilling — possibly a better
first target than parsing Spotlight's magazine layout. Full list is in
`site_media_ranking_pdfs.json` in this folder (source URLs only, not fetched).

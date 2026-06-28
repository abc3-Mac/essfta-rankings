# Quarterly Rankings — how it gets updated (design notes + roadmap)

Status: **forward-looking.** Not to build now. Captured so the current design stays
compatible with a real update workflow later. (Albert raised this; see the chat.)

## The core principle (already true today — keep it true)
Data and presentation are decoupled:

    source → parser → CANONICAL DATA (fixed schema) → build_widget → HTML widget

The widget only renders the canonical data. So any future "how do we get the data"
mechanism just has to emit the **same schema** — the widget never changes.

Canonical schema (the stable contract):
- conformation: year, quarter, section, rank, tie, name, owner, + stat columns (bob_*/bos_*/grp*_*/total)
- sports: sport, year, quarter, category, rank, tie, dog, owner, score, score2
- Both already land in `essfta_rankings.db` (table per sport + a unified `rankings` view).

**The real problem to solve is the INPUT, not the parser.** Each sport's source today:
- **Conformation / Breed:** the committee runs a *database* and dumps a PDF. Best case —
  ask them to also export a **CSV/DB extract** in our schema. Then we skip PDF parsing entirely.
- **Obedience / Agility / Rally:** volunteers pull AKC results and hand-build an Excel/docx →
  PDF, historically with no uniform layout. That inconsistency is exactly what makes PDF
  parsing fragile (see the 2013/2015/2019 Agility owner-column mess).

So the highest-leverage move is **standardize what the coordinators hand us**, not to keep
teaching a parser every past layout.

## Roadmap (cheapest → most capable)

1. **Today (works, but dev-in-the-loop):** drop new PDFs in `pdfs/`, run the parsers, rebuild,
   republish. Fine for a one-time catch-up; too fragile/manual as a forever process.

2. **Standard intake template (biggest win for least effort).** Give each sport a fixed-format
   **spreadsheet template** (one row per dog: year, quarter, category, rank, dog, owner, score…).
   Coordinators already make spreadsheets — just make the columns uniform. Import the sheet
   straight into the schema; **no PDF parsing**. Could be a shared Google Sheet (one tab per
   sport) so it's collaborative and always current.

3. **Light backend / admin.** A small form or app (Google Form→Sheet, Airtable, or a minimal
   web form) where coordinators enter/upload each quarter; a scheduled job validates and
   regenerates the widget data, then redeploys. Conformation could feed in automatically from
   its database export.

4. **WordPress-native (for when it lives on the ESSFTA WP site).** Options, roughly in order:
   - **External data file:** widget fetches a `rankings.json` (or per-sport CSVs) at load time
     instead of baking data into the HTML. Updating = replace one JSON file; the widget markup
     never changes. *This is the one design hook worth adding when we go to WP.*
   - **TablePress** is already used on the ESSFTA site (field-trial quarterly rankings = table
     #12). A CSV→TablePress import per sport is a low-tech, in-house-maintainable path.
   - **Custom table + REST endpoint / small plugin:** a `wp_essfta_rankings` table the widget
     reads via the WP REST API; an admin screen (or CSV importer) writes to it. Most "real," most
     work.

## What to preserve in the current design (so the above stays easy)
- Keep the **canonical schema** stable and documented (this file + build_db.py).
- Keep `build_widget.py` a **pure function of (data + config)** — no hand-edits to the HTML.
- When porting to WP, switch the widget to **load data externally** rather than inline, so a
  quarterly update is "replace the data file," not "regenerate and repaste the whole widget."
- Per-sport quirks (categories, score columns, coverage/owner notes) already live in config in
  build_widget.py — keep new ones there, not hard-coded in markup.

## Open questions to raise with ESSFTA (later)
- Can the Breed/Conformation database export a CSV/DB extract directly (skip its PDF)?
- Will the Obedience/Agility/Rally coordinators adopt a shared standard spreadsheet template?
- Where will this live long-term — Ghost (news.collver.biz) or the ESSFTA WordPress site — and
  who maintains it each quarter?

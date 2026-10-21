# ESSFTA Quarterly Rankings — The Scoring Rules, in Plain Language

*As validated 2026-09-14 against: the published Q1 and Jan–Jun 2026 reports, the club's
annual-awards page (englishspringerspaniels.org/annual-awards), Polly Mumma's direct
explanations, and Canine Chronicle's Juniors statistics. Every rule below is encoded in
the rankings calculator; ⚠️ marks the few points still awaiting club confirmation.*

---

## The ground rules (all sports)

1. **The data comes from the AKC.** Rankings are computed from the AKC Electronic
   Reports (the raw spreadsheets the AKC sends the club each quarter). The club's own
   award rules name AKC records as the official source.
2. **Each quarterly file covers only its own quarter.** The Q2 file holds April–June
   only. Standings are cumulative for the year, so a Jan–Jun report combines the Q1 and
   Q2 files, and the year-end report needs all four. (A dog with two scores in Q1 and
   one in Q2 has its three scores.)
3. **An asterisk marks an ESSFTA member.** Membership never decides who is ranked —
   it only annotates. (Annual *awards* additionally require membership; the quarterly
   standings list everyone.)
4. **Ties (Polly Mumma, September 2026).** When two dogs end up with the same score,
   neither beat the other, so two things follow.
   - They are listed in **alphabetical order by the dog's name** — the name itself, not
     the titles in front of it. "CH OTCH4 RACH2 Polesitter Here You Come Again" files
     under P for Polesitter, not under C for Champion. That way no one can wonder why one
     dog was put ahead of another: the alphabet decided, not a person.
   - They get the **same number**, and the next dog picks up where the count actually
     stands. If three dogs tie at 100, all three are number 1 and the next dog is
     number 4, because there really are three dogs ahead of it. Numbering tied dogs
     1, 2, 3 would say one finished ahead of another, and that isn't true.

   Same score means same rank, listed by name in alphabetical order. (Titles that follow
   the name — CD, RM, RAE, CGC — never affect the order. Ties are judged on the score as
   printed, to two decimals. Agility is the exception (Linda, 21 Oct 2026): it ranks on
   the unrounded values, so a tie there means truly equal values; see Agility below.)

---

## How many scores it takes

Three qualifying scores is the rule everywhere in the obedience and rally classes: three
to be listed, ranked on the average of the best three. It changes in five places.

- **Obedience Combined Open B/Utility — five.** A dog needs five trials where it
  qualified in both Open B and Utility, and is ranked on the average of the five highest
  combined totals.
- **Rally High Combined and High Triple — three, but three *days*.** The count is of
  combined day totals, so a dog needs three days on which it qualified in every class the
  award requires. At year end, Rally Springer of the Year uses the best five.
- **Agility Springer of the Year — ten.** Ten double-Qs in Excellent B, ranked on the
  average speed of the fastest ten.
- **Agility Novice and Open — three in each half.** Three Standard and three Jumpers
  legs, the six that earn the title, averaged.
- **Agility Excellent A — three in each half again.** Three Standard and three Jumpers
  scores to be eligible; then all the dog's qualifying scores are averaged.

Two awards have no minimum at all: the year-end Preferred agility award simply totals
every Preferred qualifying run, and juniors and conformation are not score-based, so
every handler or dog with a result appears.

*(In `build_calculator.py`: the plain three-score rule at line 197, obedience Combined's
five at 217, rally's three combined days at 230, the ten double-Qs at 205, and the
three-and-three agility checks at 239.)*

---

## Obedience

- **A dog appears in a class once it has three qualifying scores** in that class for
  the year. Its ranking score is the **average of its best three**.
- Only real qualifying runs count: a placement of 1st–4th or a plain qualifying score.
  Trophy rows on the AKC report (High in Trial, High Combined, and similar) are
  duplicates of runs already counted — they are not extra scores.
- **The S-rows, explained (Betsy, 9/16 — CONFIRMED):** a breed club may run an
  all-breed obedience/rally event and a breed specialty **concurrently**. The team
  **runs once**, but the score is recorded in **two judges' books** — two placements,
  two sets of prizes, **one score**. Any AKC-report line with an `S` placement is that
  second recording and is **never used** in computing a dog's obedience ranking. (This
  matches the title-file evidence: Laurelwyn's Heartthrob's S-rows earned her no
  Beginner Novice title — she has two real runs.) As of September 16, 2026 rally
  reads these lines the same way (see the Rally section) — the two sports agree.
- **Rankings (Betsy, 9/16 — CONFIRMED):** the **three highest** qualifying scores, for
  every obedience class except Combined. HIT/HC/trophy rows are duplicates, never
  scores. (So "the three title legs" and "best three" coincide in practice: with
  S-rows excluded, a title-class dog rarely has a fourth same-year leg.)
- **Combined Open B/Utility (Betsy, 9/16):** ranked on the **five highest** combined
  totals, and a dog needs a **minimum of five** combined trials to be listed (encoded;
  Polesitter has 15, the one-trial dog stays off).
- **Title classes and prior years:** a dog is listed only in the **year its title is
  dated** with **all three legs that year** — validated 13/13 against the Q2 card.
  Lawman's CD is dated January 18, 2026, but one leg came from 2025 → excluded. Betsy
  spots old titles from AKC's previous-titles reports or her worksheet notes; the
  **monthly AKC title file** (raw_akc/New Titles 2026.xlsx, master kept by Polly) is
  the machine-readable source. Title legs from the A and B class both count (Miranda
  Rights 2026: BN A 1/30 + BN B 2/20, 2/21 → BN dated 2/21). Encoded since 2026 Q3:
  `check_title_eligibility.py`, applied by `build_quarter.py` (Shogun's How Can I Resist
  You, BN dated 6/26/2026 on only two 2026 legs → not listed). B classes are unaffected (a dog may keep entering;
  best three of all legs, e.g. Polesitter's Open B 199.17 from 17).
- **Quarterly vs annual (Betsy, 9/16):** the quarterly rankings are cumulative and can
  in rare cases differ from the year-end award computation; the quarterlies exist to
  make the year-end determination easy. (The AKC report's own "combined" rows carry no
  scores — combined totals must always be computed from the two class scores.)

## Rally

- **Same best-three rule as obedience:** three qualifying scores to appear, ranked by
  the average of the best three. **Choice** is ranked like any other class.
- **The specialty S lines are never counted (club decision, September 16, 2026):** an
  S line is the same run recorded a second time in a concurrent specialty's judge's
  book — see the obedience section for the mechanism, which is identical. Rally reads
  them exactly as obedience does: one run, one score. (The first Q2 card counted them
  as second scores; Polly adopted the obedience reading on 9/16, and the corrected
  card — outgoing/ESSFTA_Rally_2026_JanJun_CORRECTED_v2.pdf, and Polly's own revised card
  of the same evening — supersedes it.) Trophy rows
  (High Triple Qualifier, High Combined, and similar) are never scores either.
- **High Combined** (Advanced B + Excellent B) and **High Triple** (Advanced B +
  Excellent B + Master): for each day (event and date) where the dog qualified in all
  the required classes, pair the day's scores class by class, best with best; the
  **quarterly** standings use the **average of the best three** combined totals (at
  least three to list); the **annual** Rally Springer of the Year uses the **top five**.
- **Ties:** see ground rule 4 — same score, same rank, alphabetical by name. Advanced B
  in the corrected Q2 card runs 1, 1, 1, 4, 4, 4, 7, 8, 9, 10.
- **Class order on the card (Polly 9/16):** regular titling classes first, then optional —
  Novice A/B, Advanced A/B, Excellent A/B, **Master**, then **Intermediate** (an optional
  titling class), Choice, High Combined, High Triple. Obedience follows Betsy's scorecard
  order: Novice, Open, Utility, Combined, the Preferred classes, then Beginner Novice and
  Graduate.

## Agility

- **Agility Springer of the Year:** a dog needs at least **ten double-Qs** (qualifying
  in both Excellent B Standard and Excellent B Jumpers on the same day). Rank by the
  **average speed (yards per second) of the fastest ten** double-Qs.
- **Preferred Springer of the Year:** the quarterly sheet ranks by the same
  fastest-ten-double-Q speed in the Preferred classes; the **annual** award instead
  totals all Preferred qualifying runs (ties broken by speed). Both are computed.
- **Novice, Open and Excellent A awards (and their Preferred classes) (Linda, 21 Oct
  2026):** the average of the **six title legs**: the three Standard and three Jumpers
  legs that earned the dog's two titles. **All legs must be earned in the current year**:
  a dog is listed only when both titles are dated this year and every leg up to each
  title date was run this year. A dog with one leg last year and three this year finished
  the title on its second leg this year, so it is not listed. Only Excellent B and
  Preferred Excellent B are exempt. Checked against the AKC title master
  (`raw_akc/New Titles <year>.xlsx`), as for obedience; a dog with six legs but a title
  not yet on the file is kept and flagged ("AKC lag"). Ties in score break on speed.
- **Speed (yards per second) (Linda, 21 Oct 2026):** course distance ÷ dog's time. On
  **Novice and Open Standard** courses (AGNOVA, AGNOVB, AGNOVP, AGOPEN, AGOPENP) the
  course has a table, so the 5-second table count comes off the time first: distance ÷
  (time − 5). Excellent Standard no longer has a table, and Jumpers never does.
  Reproduces Linda's 2026 Open sheet run for run (12/12).
- **Precision (Linda, 21 Oct 2026):** agility ranks on the **unrounded** values, and
  every agility speed prints **three decimals** (Albert, 21 Oct: "all around").
  Two dogs can print the same figure and hold different places (Q3 2026: Mcd's Psych You
  Out 3.8417 over Cedarwood's Dream A Little Dream 3.8371, both 3.84 at two decimals).
  This overrides ground rule 4's two-decimal tie for agility.

## Conformation (Breed & Group)

*The official report comes from the club's own database; these rules reproduce it
exactly and match the wording on the club's awards page.*

- **Best of Breed points:** one point for every dog and bitch defeated at the show —
  everyone shown in the breed, classes included.
- **Best of Opposite Sex points:** one point for every same-sex dog defeated —
  **plus**, when Best of Winners went to the *same sex as the BOS winner*, one point
  for every dog shown in the classes (the Best of Winners "defeat chain").
- **Group points:** one point per dog defeated in the group; **Best in Show points:**
  one point per dog defeated at the show. On a day the dog wins BIS, its group points
  for that day fold into the BIS points (no double counting).
- Owner-handled series and puppy-competition results are separate programs and are
  not counted.
- **"Spec" columns:** a specialty is a springer club's own show or the National
  (AKC competition type S/PS), **plus designated specialties (DS)**: a breed club's
  specialty held at an all-breed show. The AKC results file lists a DS as an ordinary
  all-breed show (AB/LB), so the event numbers come from the AKC event search
  (Conformation Events → Specialties (S/PS/DS) → English Springer Spaniel → type DS →
  the host show under Associated Events). Alvin Eng compiled that list by hand/scraper;
  since 20 Oct 2026 `fetch_designated_specialties.py` does the same from the AKC event
  search API (search by EVENT date, not the default closing date) and `build_quarter.py`
  runs it whenever `raw_akc/designated_specialties_<year>.csv` does not yet reach the
  quarter's end. It reproduced Alvin's Jan–Sep 2026 list exactly (10 events). With it, every #Spec cell
  matches: Q1 and Jan–Jun 2026 published cards (0 diffs, previously 7 and 10 thought to
  be "supported entries") and Alvin's Jan–Sep 2026 tabulation (474/474 cells,
  20 Oct 2026).

## Juniors *(draft — no current published ranking; methodology validated against Canine Chronicle, the source the club's 2016 quarterly reprinted)*

- **Total Defeated** is the ranking metric. At each show, a handler gets credit for
  their single best result: Best Junior Handler defeats everyone else entered; Reserve
  defeats everyone but the winner; a class placement defeats those below it in the
  class. One credit per show — a class win and the BJH win the same day don't both count.
- Win columns follow Canine Chronicle's conventions: a Best Junior "win" requires
  actual competition (an uncontested single-entry BJH is not counted as a win, though
  it appears in the record).

---

## Questions still open with the club (updated 9/15)

**Obedience score items (9/14, unchanged):** Bluegrass Bend (182.83 vs the file's 192.83) ·
McD's According To My Heart (197.83 vs 199.17) · Calypso's Enchanted Encounter (score and
owner) · Shogun's missing score (195.33) · Preferred Novice (Hail Mary's late-June title).
None involves second-trial scores; all are believed slips or timing.

**Resolved:** rally rev 3 = 91/91 (CLOSED). Betsy's 9/16 answers + corrected scorecard
settle obedience method entirely (S-rows explained, best-3-highest, Combined min-5 —
encoded). Her corrected card adopts Bluegrass 192.83, McD's 199.17, Shogun's 195.33,
Hail Mary 198.33, and Jj's Prince Diamond Dallas 187.83.

**Still open — three cells on the corrected obedience card:**
1. Reddoor's Castine Pearl, Novice B: card 180.50 vs AKC legs 183.5+183.0+174.0 → 180.17.
2. Sapphires Where The Heart Is, Open A: card 188.33 vs AKC legs 191.5+188.5+185.5 → 188.50.
3. Calypso's Enchanted Encounter, BN B: card 194.50 / owner "A March*" vs AKC 194.0+
   191.5+188.0 → 191.17 / owner Sherry Savar ("A March" appears in no AKC owner field,
   either quarter — Betsy herself asks "who is A March?").
**S-line policy: RESOLVED 9/16** — Polly adopted the obedience reading ("I'm just
copying what you've done"): one run, one score, both sports. The corrected rally Q2
card (six dogs off, seven values changed, new firsts in Novice A and Intermediate,
alpha-tie ordering with shared ranks) is computed and with Polly to issue.

---

## Appendix — technical mapping (for the code)

| Plain term | AKC file term |
|---|---|
| qualifying run | `Placement` ∈ {QLFY, 1, 2, 3, 4} |
| specialty book line — never a score (any sport) | `Placement` ∈ {S1, S2, S3} |
| trophy row (never a score) | `Placement` ∈ {HIGHT, HIGHCM, HTQ, HTQS, HCS, HTP, HTS} |
| a trial/day | `Event Name` + `Event Date` |
| dog identity | `Reg Number` (exact; names accrete titles over the year) |
| BOB / BOS / Select / Best of Winners | `Result Code` BOB / OS / SEL / BW on `Comp Primary Class` BOB rows |
| breed points | Σ `Dogs Defeated` (BOB rows); BOS = `Same Sex Dogs Defeated` + opposite sex's `WIN`-row `Number in Class Same Sex` when BW is BOS's sex |
| group/BIS points | `Dogs Defeated` on `BISPRT`/`GRP1–4` and `(BIS, BIS)` rows |
| excluded series | `BOBOH`, `BISOH`, `BISPRTOH`/`OHG*`, `BP*` (owner-handled, puppy) |
| juniors show total | `Num Competing` on BJH/RBJH rows (class rows carry class size) |
| speed | YPS = `Course Distance` / `Dog Time`; Novice/Open Standard: / (`Dog Time` − 5) |

*Code: `build_calculator.py` (sports), `compute_conformation.py`, `juniors_standings.py`;
regression suite `test_calculator.py` pins every validated number above.*

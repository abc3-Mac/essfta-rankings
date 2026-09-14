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

---

## Obedience

- **A dog appears in a class once it has three qualifying scores** in that class for
  the year. Its ranking score is the **average of its best three**.
- Only real qualifying runs count: a placement of 1st–4th or a plain qualifying score.
  Trophy rows on the AKC report (High in Trial, High Combined, and similar) are
  duplicates of runs already counted — they are not extra scores.
- ⚠️ **Second-trial scores:** rally counts them (see below); the obedience report
  behaves as if obedience does **not**. The calculator matches the report. Awaiting
  Polly's confirmation.
- **Combined Open B / Utility:** for each trial where the dog qualified in both Open B
  and Utility (A or B), add the two scores. The ranking value is the **average of the
  five best** such combined totals; a dog needs at least three combined trials to be
  listed. (The AKC report's own "combined" rows carry no scores — the combination must
  be computed from the two class scores.)

## Rally

- **Same best-three rule as obedience:** three qualifying scores to appear, ranked by
  the average of the best three.
- **The rule that unlocked everything (Polly, 9/14):** many clusters hold **two trials
  in one day**. The AKC report shows the second trial's results as special-placement
  rows (S1, S2, S3) that repeat the score — **both scores count**. A dog that qualified
  twice on Saturday and twice on Sunday has four scores, not two. (Trophy rows —
  High Triple Qualifier, High Combined, and similar — remain non-scores, as in
  obedience; their "score" fields hold combined totals, not runs.)
- **Choice** is ranked like any other class (best three).
- **High Combined** (Advanced B + Excellent B) and **High Triple** (Advanced B +
  Excellent B + Master): a combined total exists only when the dog qualified in **all
  the required classes on the same day, in the same trial** — pairs are taken in the
  order listed on the AKC report, and a day without a full qualifying set contributes
  nothing. The **quarterly** standings use the **average of the best three** combined
  totals; the **annual** Rally Springer of the Year uses the **top five**.
  ⚠️ On a two-trial day it is not always possible to tell from the AKC file which score
  belongs to which trial; in rare cases (one dog so far, by 0.34) the compiler's pairing
  and the calculator's may differ. The compiler's number governs.

## Agility

- **Agility Springer of the Year:** a dog needs at least **ten double-Qs** (qualifying
  in both Excellent B Standard and Excellent B Jumpers on the same day). Rank by the
  **average speed (yards per second) of the fastest ten** double-Qs.
- **Preferred Springer of the Year:** the quarterly sheet ranks by the same
  fastest-ten-double-Q speed in the Preferred classes; the **annual** award instead
  totals all Preferred qualifying runs (ties broken by speed). Both are computed.
- **Novice and Open awards:** the average of the **first six** qualifying runs — the
  three Standard and three Jumpers legs that earn the title. Ties break on speed.
- **Excellent A award:** the average of the qualifying scores, with an eligibility
  requirement of **at least three Standard and three Jumpers** scores (a dog with three
  Standard 100s but only two Jumpers legs is not yet eligible).
- **Preferred class awards** (Novice/Excellent A): the average across both preferred
  classes' legs together.

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
- **"Spec" columns:** a specialty is a springer club's own show or the National —
  ⚠️ plus club-designated **supported entries** at all-breed shows, which appear only
  in the club calendar. The supported-entry list is the one input the AKC file lacks.

## Juniors *(draft — no current published ranking; methodology validated against Canine Chronicle, the source the club's 2016 quarterly reprinted)*

- **Total Defeated** is the ranking metric. At each show, a handler gets credit for
  their single best result: Best Junior Handler defeats everyone else entered; Reserve
  defeats everyone but the winner; a class placement defeats those below it in the
  class. One credit per show — a class win and the BJH win the same day don't both count.
- Win columns follow Canine Chronicle's conventions: a Best Junior "win" requires
  actual competition (an uncontested single-entry BJH is not counted as a win, though
  it appears in the record).

---

## The five obedience questions still open with the club (9/14)

Bluegrass Bend (182.83 vs the file's 192.83) · McD's According To My Heart (197.83 vs
199.17) · Calypso's Enchanted Encounter (score and owner) · Shogun's missing score
(195.33) · Preferred Novice (Hail Mary's late-June title). None involves second-trial
scores; all are believed slips or timing.

---

## Appendix — technical mapping (for the code)

| Plain term | AKC file term |
|---|---|
| qualifying run | `Placement` ∈ {QLFY, 1, 2, 3, 4} |
| second-trial score (rally only) | `Placement` ∈ {S1, S2, S3} |
| trophy row (never a score) | `Placement` ∈ {HIGHT, HIGHCM, HTQ, HTQS, HCS, HTP, HTS} |
| a trial/day | `Event Name` + `Event Date` |
| dog identity | `Reg Number` (exact; names accrete titles over the year) |
| BOB / BOS / Select / Best of Winners | `Result Code` BOB / OS / SEL / BW on `Comp Primary Class` BOB rows |
| breed points | Σ `Dogs Defeated` (BOB rows); BOS = `Same Sex Dogs Defeated` + opposite sex's `WIN`-row `Number in Class Same Sex` when BW is BOS's sex |
| group/BIS points | `Dogs Defeated` on `BISPRT`/`GRP1–4` and `(BIS, BIS)` rows |
| excluded series | `BOBOH`, `BISOH`, `BISPRTOH`/`OHG*`, `BP*` (owner-handled, puppy) |
| juniors show total | `Num Competing` on BJH/RBJH rows (class rows carry class size) |
| speed | YPS = `Course Distance` / `Dog Time` |

*Code: `build_calculator.py` (sports), `compute_conformation.py`, `juniors_standings.py`;
regression suite `test_calculator.py` pins every validated number above.*

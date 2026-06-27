#!/usr/bin/env python3
"""Build essfta_rankings.db — a SQLite database of every extracted ranking.

Two source tables keep each sport's native schema:
  conformation  — Breed/Group standings with their wide point-stat columns
  sports        — Obedience/Agility/Rally standings (category, score, score2)

A unified view `rankings` flattens both into a common shape (sport, year,
quarter, category, rank, tie, name, owner, score) for cross-sport queries.

Names/owners are cleaned + Title-Cased via dataprep (sport names untouched).
"""
import os, sqlite3
from dataprep import load_conformation, load_sports

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "essfta_rankings.db")

CONF_STAT_COLS = ["bob_shows", "bob_spec", "bob_pts", "bos_shows", "bos_spec",
                  "bos_pts", "bis_n", "bis_pts", "grp1_n", "grp1_pts", "grp2_n",
                  "grp2_pts", "grp3_n", "grp3_pts", "grp4_n", "grp4_pts", "total"]


def _int(v):
    """'' -> None, '1240' -> 1240, '8/3' (multi) -> keep as text via None guard."""
    s = str(v).strip()
    if s == "":
        return None
    try:
        return int(s)
    except ValueError:
        return s        # rare slashed value; store as-is (column is flexible)


def _num(v):
    s = str(v).strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def main():
    if os.path.exists(DB):
        os.remove(DB)
    con = sqlite3.connect(DB)
    cur = con.cursor()

    cur.execute(f"""
        CREATE TABLE conformation (
            id INTEGER PRIMARY KEY,
            year INTEGER, quarter TEXT, section TEXT,
            rank INTEGER, tie TEXT, name TEXT, owner TEXT,
            {", ".join(c + " INTEGER" for c in CONF_STAT_COLS)}
        )""")
    cur.execute("""
        CREATE TABLE sports (
            id INTEGER PRIMARY KEY,
            sport TEXT, year INTEGER, quarter TEXT, category TEXT,
            rank INTEGER, tie TEXT, dog TEXT, owner TEXT,
            score REAL, score2 REAL
        )""")

    conf = load_conformation()
    conf_cols = ["year", "quarter", "section", "rank", "tie", "name", "owner"] + CONF_STAT_COLS
    cur.executemany(
        f"INSERT INTO conformation ({', '.join(conf_cols)}) VALUES ({', '.join('?' * len(conf_cols))})",
        [[_int(r.get("year")), r.get("quarter"), r.get("section"),
          _int(r.get("rank")), r.get("tie"), r.get("name"), r.get("owner")]
         + [_int(r.get(c, "")) for c in CONF_STAT_COLS] for r in conf])

    sp = load_sports()
    cur.executemany(
        "INSERT INTO sports (sport, year, quarter, category, rank, tie, dog, owner, score, score2)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        [[r["sport"], _int(r["year"]), r["quarter"], r["category"], _int(r["rank"]),
          r["tie"], r["dog"], r["owner"], _num(r["score"]), _num(r["score2"])] for r in sp])

    # unified cross-sport view: conformation 'total' becomes the comparable score
    cur.execute("""
        CREATE VIEW rankings AS
            SELECT 'Conformation' AS sport, year, quarter, section AS category,
                   rank, tie, name, owner, CAST(total AS REAL) AS score
              FROM conformation
            UNION ALL
            SELECT sport, year, quarter, category, rank, tie, dog AS name, owner, score
              FROM sports
    """)

    for c in ("CREATE INDEX ix_conf_yr ON conformation(year, section)",
              "CREATE INDEX ix_sp_yr ON sports(sport, year, category)"):
        cur.execute(c)

    con.commit()

    # report
    print(f"wrote {DB}  ({os.path.getsize(DB)//1024} KB)")
    for tbl in ("conformation", "sports"):
        n = cur.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"  {tbl}: {n} rows")
    print("  view rankings:", cur.execute("SELECT COUNT(*) FROM rankings").fetchone()[0], "rows")
    print("  by sport:", cur.execute(
        "SELECT sport, COUNT(*) FROM rankings GROUP BY sport ORDER BY 2 DESC").fetchall())
    print("  sample:", cur.execute(
        "SELECT sport, year, name, owner, score FROM rankings WHERE year=2025 "
        "ORDER BY sport, rank LIMIT 3").fetchall())
    con.close()


if __name__ == "__main__":
    main()

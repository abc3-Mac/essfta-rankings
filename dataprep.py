#!/usr/bin/env python3
"""Single source of cleaned ranking rows for the DB builder and the widget.

- Conformation rows: Title-Case name + owner (AKC titles kept caps), and repair a
  localized 2014 Group-Bitches parse artifact where an owner asterisk-initial
  ("*B.") leaked into the name column (and the matching owner lost its initial).
- Sport rows (Obedience/Agility/Rally): names are already mixed-case in source,
  so they are passed through untouched (only whitespace tidy).
"""
import json, os, re
from titlecase import tc_name, tc_owner

HERE = os.path.dirname(os.path.abspath(__file__))

_LEAK_RE = re.compile(r"\s*(\*[A-Z]\.)\s*")     # stray owner initial inside a name


def _fix_owner_leak(name, owner):
    """If a "*X." owner-initial sits inside the name, pull it out and prepend it to
    the owner (whose leading surname is missing exactly that initial)."""
    m = _LEAK_RE.search(name)
    if not m:
        return name, owner
    initial = m.group(1)
    name = (name[:m.start()] + " " + name[m.end():]).strip()
    name = re.sub(r"\s+", " ", name)
    owner = f"{initial} {owner}".strip()
    return name, owner


def load_conformation():
    rows = json.load(open(os.path.join(HERE, "breed_group.json"), encoding="utf-8"))
    out = []
    for r in rows:
        r = dict(r)
        name, owner = _fix_owner_leak(r["name"], r["owner"])
        r["name"] = tc_name(name)
        r["owner"] = tc_owner(owner)
        out.append(r)
    return out


def load_sports():
    rows = json.load(open(os.path.join(HERE, "sports.json"), encoding="utf-8"))
    out = []
    for r in rows:
        r = dict(r)
        r["dog"] = re.sub(r"\s+", " ", (r.get("dog") or "")).strip()
        r["owner"] = re.sub(r"\s+", " ", (r.get("owner") or "")).strip()
        out.append(r)
    return out


if __name__ == "__main__":
    conf = load_conformation()
    print(f"conformation: {len(conf)} rows")
    for r in conf:
        if r["year"] == "2014" and r["section"] == "Group - Bitches" and int(r["rank"]) <= 8:
            print(f"  r{r['rank']}: {r['name']}  |  {r['owner']}")
    sp = load_sports()
    print(f"sports: {len(sp)} rows")

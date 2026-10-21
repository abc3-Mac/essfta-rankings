#!/usr/bin/env python3
"""Fetch the year's English Springer Spaniel designated specialties from the AKC event search.

    python3 fetch_designated_specialties.py 2026                 # Jan 1 through today
    python3 fetch_designated_specialties.py 2026 --through 2026-09-30

A designated specialty (AKC competition type DS) is a springer club's specialty held at
an all-breed show. The AKC conformation results export lists those results under the
host show's event number as an ordinary all-breed show (AB/LB), so compute_conformation
can count them as specialties only from this list (#Spec columns).

This automates Alvin Eng's manual steps (raw_akc/alvin_2026-10-20/Finding designated
specialties.txt):
  1. POST webapps.akc.org/event-search/api/search/events — the JSON API behind the AKC
     Event Search page — for breed 117 (English Springer Spaniel), competition
     "Specialties (S/PS/DS)", by EVENT date (dateRange.type "event"; the page's default
     filters on closing date and misses early-January shows). One query per quarter
     keeps each answer small.
  2. Keep the events whose eventType includes DS.
  3. Open each one's details page (apps.akc.org .../index_results.cfm?action=plan&
     event_number=…) and read the host show from "Associated Events" — its event number
     is in the link, its type is AB or LB.

Writes raw_akc/designated_specialties_<year>.csv in Alvin's column layout (the header
line starts with # so loaders skip it), plus a "# fetched" comment line. Requests are
spaced AKC_FETCH_DELAY seconds apart (default 2.5), as the judges directory reader does.
"""
import argparse, csv, datetime, html, http.cookiejar, json, os, re, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SEARCH = "https://webapps.akc.org/event-search/api/search/events"
DETAIL = "https://www.apps.akc.org/apps/events/search/index_results.cfm?action=plan&event_number={}"
DELAY = float(os.environ.get("AKC_FETCH_DELAY", "2.5"))
UA = {"User-Agent": "Mozilla/5.0 (Macintosh) ESSFTA quarterly rankings (designated-specialty list)"}
HEADER = ["date_event_end", "text_event_number", "cde_competition_type", "orig_name_event", "text_name_event"]

_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
_last = [0.0]


def _get(url, data=None, headers=None):
    wait = _last[0] + DELAY - time.time()
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
    try:
        with _opener.open(req, timeout=60) as r:
            return r.read().decode("utf-8", "replace")
    finally:
        _last[0] = time.time()


def search(start, end):
    body = {
        "address": {"eventSetting": {"indoor": True, "outdoor": True, "outsideCovered": True},
                    "location": {"cityState": "", "latitude": 0, "longitude": 0, "zipCode": None},
                    "radius": "any", "searchByState": False, "searchByCity": False,
                    "searchText": "All Cities & States"},
        "dateRange": {"from": f"{start}T00:00:00", "to": f"{end}T00:00:00", "type": "event"},
        "breedCode": "117 ", "breedName": "English Springer Spaniel",
        "competition": {"items": [{"label": "Specialties (S/PS/DS)", "value": {"compType": "S/PS/DS"},
                                   "selected": True}]},
        "sortBy": "date",
    }
    raw = _get(SEARCH, json.dumps(body).encode(), {"Content-Type": "application/json"})
    events = json.loads(raw).get("events")
    if events is None:
        raise SystemExit(f"AKC search answered without an event list for {start}..{end}: {raw[:200]}")
    return events


_ASSOC = re.compile(r'event_number=(\d+)[^>]*>\s*(.*?)</a>.*?<td[^>]*>\s*<font[^>]*>\s*([^<]*?)\s*</font>',
                    re.S | re.I)


def host_shows(event_number):
    """(event number, club name, event type) of the shows under Associated Events."""
    page = _get(DETAIL.format(event_number))
    i = page.find("Associated Events")
    if i < 0:
        return []
    out = []
    for num, name, typ in _ASSOC.findall(page[i:]):
        out.append((num, html.unescape(re.sub(r"\s+", " ", name)).strip(), typ.strip()))
    return out


def quarters(year, through):
    q = [(datetime.date(year, m, 1), datetime.date(year, m + 2, 30 if m + 2 in (6, 9) else 31))
         for m in (1, 4, 7, 10)]
    return [(a, min(b, through)) for a, b in q if a <= through]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("year", type=int)
    ap.add_argument("--through", type=datetime.date.fromisoformat,
                    help="last event date to include (default today, capped at Dec 31)")
    ap.add_argument("--out", help="CSV path (default raw_akc/designated_specialties_<year>.csv)")
    args = ap.parse_args()
    through = min(args.through or datetime.date.today(), datetime.date(args.year, 12, 31))
    rows, problems = [], []
    for start, end in quarters(args.year, through):
        events = search(start, end)
        ds = [e for e in events if "DS" in e["eventType"].split("/")
              and start.isoformat() <= e["startDate"] <= end.isoformat()]
        print(f"{start}..{end}: {len(events)} specialty events, {len(ds)} designated")
        for e in ds:
            hosts = [h for h in host_shows(e["eventNumber"]) if h[2].split("/")[0] in ("AB", "LB")]
            if len(hosts) != 1:
                problems.append(f"{e['eventNumber']} {e['startDate']} {e['eventName']}: host shows {hosts}")
                continue
            num, club, _ = hosts[0]
            rows.append([datetime.date.fromisoformat(e["endDate"]).strftime("%-m/%-d/%Y"), num, "DS", club,
                         e["eventName"]])
            print(f"  {e['startDate']}  {e['eventName']}  ->  {club} {num}")
    if problems:
        print("\nNOT WRITTEN — fix these by hand (AKC event search, View Complete Event Details):")
        print("\n".join("  " + p for p in problems))
        return 1
    out = args.out or os.path.join(HERE, "raw_akc", f"designated_specialties_{args.year}.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        f.write("# " + ",".join(HEADER) + "\n")
        f.write(f"# fetched {datetime.date.today()} from the AKC event search, events through {through}\n")
        csv.writer(f).writerows(rows)
    print(f"\n{len(rows)} designated specialties -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

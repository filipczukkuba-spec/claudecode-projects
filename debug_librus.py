"""Run: py debug_librus.py"""
import json, datetime, sys
sys.path.insert(0, ".")

with open("jarvis_memory.json") as f:
    mem = json.load(f)
user = (mem.get("librus_user") or "").strip()
pw   = (mem.get("librus_pass") or "").strip()
if not user or not pw:
    print("No credentials in jarvis_memory.json"); exit(1)

print(f"user={user!r}  pass={'*'*len(pw)}\n")

from jarvis import _librus_web_session, _librus_parse_terminarz, fetch_librus_events
import datetime as dt

today = dt.date.today()

print("=== Testing web login ===")
sess = _librus_web_session(user, pw)

if sess:
    print("\n=== Fetching terminarz ===")
    r = sess.post("https://synergia.librus.pl/terminarz/",
                  data={"rok": str(today.year), "miesiac": str(today.month)}, timeout=15)
    print(f"HTTP {r.status_code}  length={len(r.text)}")
    with open("terminarz_raw.html", "w", encoding="utf-8") as f:
        f.write(r.text)
    print("Saved terminarz_raw.html")

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(r.text, "lxml")
    classes = []
    for d in soup.find_all("div", class_=True):
        for c in d.get("class", []):
            if c not in classes: classes.append(c)
    print(f"\nDiv classes ({len(classes)}): {classes}")

    print("\n=== Parsing events ===")
    events = _librus_parse_terminarz(r.text, today, 14)
    print(f"Found {len(events)} events:")
    for e in events:
        print(f"  {e['start'].date()}  {e['summary']}")

print("\n=== Full fetch_librus_events ===")
all_ev = fetch_librus_events(days=7)
print(f"Total: {len(all_ev)}")
for e in all_ev:
    print(f"  {e['start'].date()}  {e['summary']}")

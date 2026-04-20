"""Run this to diagnose Librus web-form login: py debug_librus.py"""
import json, datetime, traceback, requests
from bs4 import BeautifulSoup

MEMORY_PATH = "jarvis_memory.json"
with open(MEMORY_PATH) as f:
    mem = json.load(f)

user = (mem.get("librus_user") or "").strip()
pw   = (mem.get("librus_pass") or "").strip()

if not user or not pw:
    print("ERROR: No Librus credentials in jarvis_memory.json")
    exit(1)

print(f"Credentials found: user={user!r}  pass={'*'*len(pw)}")

BASE = "https://synergia.librus.pl"
s = requests.Session()
s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

print("\nStep 1: GET login page...")
r = s.get(BASE + "/logowanie", timeout=15)
print(f"  status={r.status_code}  url={r.url}")

soup = BeautifulSoup(r.text, "lxml")
# look for any hidden fields / csrf
form = soup.find("form")
hidden = {}
if form:
    for inp in form.find_all("input", type="hidden"):
        hidden[inp.get("name")] = inp.get("value", "")
    print(f"  form action={form.get('action')!r}  hidden fields={list(hidden.keys())}")

print("\nStep 2: POST credentials...")
payload = {**hidden, "login": user, "pass": pw}
r2 = s.post(BASE + "/logowanie", data=payload, timeout=15, allow_redirects=True)
print(f"  status={r2.status_code}  final_url={r2.url}")

logged_in = "terminarz" in r2.text or "wyloguj" in r2.text.lower() or r2.url != BASE + "/logowanie"
print(f"  looks logged in: {logged_in}")

print("\nStep 3: GET terminarz...")
today = datetime.date.today()
r3 = s.post(BASE + "/terminarz/", data={"rok": str(today.year), "miesiac": str(today.month)}, timeout=15)
print(f"  status={r3.status_code}  length={len(r3.text)}")

with open("terminarz_raw.html", "w", encoding="utf-8") as fh:
    fh.write(r3.text)
print("  saved terminarz_raw.html")

soup3 = BeautifulSoup(r3.text, "lxml")
divs = soup3.find_all("div", class_=True)
classes = []
for d in divs:
    for c in d.get("class", []):
        if c not in classes:
            classes.append(c)
print(f"\nDiv classes on terminarz page ({len(classes)}):")
for c in classes:
    print(f"  {c!r}")

today = datetime.date.today()
print(f"\nFetching raw terminarz HTML for {today.month}/{today.year} ...")
try:
    resp = cli.post(cli.SCHEDULE_URL, data={"rok": str(today.year), "miesiac": str(today.month)})
    html = resp.text
    print(f"HTTP status: {resp.status_code}  length: {len(html)} chars")

    # save full HTML so we can inspect it
    with open("terminarz_raw.html", "w", encoding="utf-8") as fh:
        fh.write(html)
    print("Full HTML saved to terminarz_raw.html")

    # show first unique class names to spot the real container
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    divs = soup.find_all("div", class_=True)
    classes = []
    for d in divs:
        for c in d.get("class", []):
            if c not in classes:
                classes.append(c)
    print(f"\nAll div class names found ({len(classes)}):")
    for c in classes:
        print(f"  {c!r}")

    # check what librus-apix expects
    old_style = soup.find_all("div", attrs={"class": "kalendarz-dzien"})
    print(f"\nlibrus-apix looks for 'kalendarz-dzien' → found {len(old_style)} divs")
except Exception as e:
    print(f"Raw fetch FAILED: {e}")
    traceback.print_exc()

print(f"\nFetching homework {today} → {today + datetime.timedelta(days=7)} ...")
try:
    hw_list = get_homework(cli, today.strftime("%Y-%m-%d"),
                           (today + datetime.timedelta(days=7)).strftime("%Y-%m-%d"))
    print(f"Homework count: {len(hw_list)}")
    for hw in hw_list:
        print(f"  subject={hw.subject!r}  category={hw.category!r}  due={hw.completion_date!r}")
except Exception as e:
    print(f"get_homework FAILED: {e}")
    traceback.print_exc()

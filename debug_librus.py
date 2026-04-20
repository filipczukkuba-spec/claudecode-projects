"""Run this to diagnose why Librus events aren't showing: py debug_librus.py"""
import json, datetime, traceback

MEMORY_PATH = "jarvis_memory.json"
with open(MEMORY_PATH) as f:
    mem = json.load(f)

user = (mem.get("librus_user") or "").strip()
pw   = (mem.get("librus_pass") or "").strip()

if not user or not pw:
    print("ERROR: No Librus credentials in jarvis_memory.json")
    print("  Say 'set Librus credentials' to Jarvis first.")
    exit(1)

print(f"Credentials found: user={user!r}  pass={'*'*len(pw)}")

try:
    from librus_apix.client import new_client
    from librus_apix.schedule import get_schedule
    from librus_apix.homework import get_homework
except ImportError as e:
    print(f"ERROR: {e}")
    exit(1)

print("Logging in...")
try:
    cli = new_client()
    cli.get_token(user, pw)
    print("Login OK")
except Exception as e:
    print(f"LOGIN FAILED: {e}")
    traceback.print_exc()
    exit(1)

today = datetime.date.today()
print(f"\nFetching schedule for {today.month}/{today.year} ...")
try:
    sched = get_schedule(cli, str(today.month), str(today.year), True)
    print(f"Schedule dict has {len(sched)} day keys: {sorted(sched.keys())}")
    non_empty = {k: v for k, v in sched.items() if v}
    print(f"Non-empty days: {sorted(non_empty.keys())}")
    for day_num, events in sorted(non_empty.items()):
        d = datetime.date(today.year, today.month, day_num)
        delta = (d - today).days
        print(f"\n  {d} (in {delta} days):")
        for e in events:
            print(f"    subject={e.subject!r}  title={e.title!r}  hour={e.hour!r}  number={e.number!r}")
except Exception as e:
    print(f"get_schedule FAILED: {e}")
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

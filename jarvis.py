#!/usr/bin/env python3
"""J.A.R.V.I.S. - Just A Rather Very Intelligent System"""

import os, sys, time, math, random, struct, threading, subprocess, webbrowser, json, asyncio, tempfile

try:
    import numpy as _np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import anthropic
    import pyaudio
    import pygame
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
    import speech_recognition as sr
    import psutil
    import pyautogui
    import pygetwindow as gw
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
except ImportError as e:
    print(f"Missing dependency: {e}"); print("Run: python setup_jarvis.py"); sys.exit(1)

import urllib.parse

try:
    import edge_tts
    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False

try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False

try:
    import requests as _requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# ─── Config ───────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "jarvis_config.json")
SOUNDS_DIR  = os.path.join(BASE_DIR, "sounds")
TTS_VOICE   = "en-GB-RyanNeural"   # British male — closest to JARVIS

def load_api_key():
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key: return key
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f: return json.load(f).get("api_key", "")
    return ""

def save_api_key(key):
    with open(CONFIG_PATH, "w") as f: json.dump({"api_key": key}, f)

API_KEY = load_api_key()

# ─── Spotify ──────────────────────────────────────────────────────────────────
SPOTIFY_CLIENT_ID     = os.environ.get("SPOTIFY_CLIENT_ID",     "3772f28ca5c541e0a970a60274c84a68")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET", "d91e6f1761f940bb84ac6ce628bdd127")

def make_spotify():
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET: return None
    try:
        return spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET))
    except Exception as e:
        print(f"Spotify init error: {e}"); return None

sp = make_spotify()

def find_song():
    if not os.path.exists(SOUNDS_DIR): return None
    for ext in (".mp3", ".webm", ".ogg", ".wav"):
        for f in os.listdir(SOUNDS_DIR):
            if f.endswith(ext): return os.path.join(SOUNDS_DIR, f)
    return None

SONG_PATH = find_song() or r"C:\Users\filip\Desktop\claudecode\sounds\iron_man.mp3"
if not os.path.exists(SONG_PATH): SONG_PATH = None

CHUNK = 1024; FORMAT = pyaudio.paInt16; CHANNELS = 1; RATE = 44100
CLAP_THRESHOLD = 1400; DOUBLE_CLAP_MAX = 1.2; DOUBLE_CLAP_DEBOUNCE = 0.12

# ─── State ────────────────────────────────────────────────────────────────────
active               = False
conversation_history = []
visual_state         = "idle"   # idle | waking | listening | speaking

# ─── News & Weather ───────────────────────────────────────────────────────────
def fetch_weather():
    if not HAS_REQUESTS: return None
    try:
        r = _requests.get("https://wttr.in/?format=%C,+%t", timeout=5)
        return r.text.strip()
    except Exception: return None

def fetch_headlines(count=6):
    if not HAS_FEEDPARSER: return []
    try:
        feed = feedparser.parse('https://feeds.bbci.co.uk/news/world/rss.xml')
        out  = []
        for e in feed.entries[:count]:
            img = None
            for attr in ('media_thumbnail', 'media_content'):
                val = getattr(e, attr, None)
                if val and isinstance(val, list) and val[0].get('url'):
                    img = val[0]['url']; break
            if not img and getattr(e, 'enclosures', None):
                for enc in e.enclosures:
                    if 'image' in enc.get('type',''):
                        img = enc.get('href') or enc.get('url'); break
            out.append({'title': e.title, 'img': img})
        return out
    except Exception: return []

# ─── Memory System ────────────────────────────────────────────────────────────
MEMORY_PATH = os.path.join(BASE_DIR, "jarvis_memory.json")
_memory_lock = threading.Lock()

def _default_memory():
    return {"commands": [], "habits": {}, "birthdays": [],
            "wake_count": 0, "last_wake": 0,
            "gcal_ics_url": "", "gcal_birthdays_ics_url": "",
            "librus_user": "", "librus_pass": "",
            "gmail_imap_user": "", "gmail_imap_pass": ""}

def load_memory():
    if os.path.exists(MEMORY_PATH):
        try:
            with open(MEMORY_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            base = _default_memory(); base.update(data); return base
        except Exception as e:
            print(f"Memory load error: {e}")
    return _default_memory()

def save_memory(mem):
    with _memory_lock:
        try:
            with open(MEMORY_PATH, "w", encoding="utf-8") as f:
                json.dump(mem, f, indent=2, default=str)
        except Exception as e:
            print(f"Memory save error: {e}")

def record_command(command):
    mem = load_memory()
    mem.setdefault("commands", []).append({"text": command, "time": time.time()})
    mem["commands"] = mem["commands"][-200:]
    hour = time.localtime().tm_hour
    habits = mem.setdefault("habits", {})
    habits[f"h{hour}"] = habits.get(f"h{hour}", 0) + 1
    save_memory(mem)

def get_suggestion(mem):
    if not mem: return None
    if mem.get("wake_count", 0) <= 1: return None
    hour = time.localtime().tm_hour
    recent = " ".join((c.get("text","") or "").lower() for c in mem.get("commands", [])[-40:])
    if 6 <= hour < 11 and "spotify" in recent:
        return "Shall I resume your morning playlist?"
    if 20 <= hour or hour < 2:
        return "Working late, I see."
    return None

def build_memory_context(mem):
    if not mem:
        return ""
    lines = []
    wc = mem.get("wake_count", 0)
    lt = time.localtime()
    lines.append(f"Session #{wc}. Current local time: {time.strftime('%A %H:%M', lt)}.")

    cmds = mem.get("commands", [])[-40:]
    if cmds:
        keywords = ["spotify", "music", "jazz", "calendar", "week", "email",
                    "news", "weather", "play", "librus", "birthday", "open", "gmail"]
        topics = {}
        for c in cmds:
            t = (c.get("text") or "").lower()
            for k in keywords:
                if k in t:
                    topics[k] = topics.get(k, 0) + 1
        if topics:
            top = sorted(topics.items(), key=lambda x: -x[1])[:5]
            lines.append("Frequent past requests: " + ", ".join(f"{k} (×{v})" for k, v in top) + ".")
        recent = [c.get("text", "") for c in cmds[-5:] if c.get("text")]
        if recent:
            lines.append("Most recent commands: " + " | ".join(recent))

    habits = mem.get("habits", {})
    if habits:
        top_hours = sorted(habits.items(), key=lambda x: -x[1])[:3]
        lines.append("Most active hours: " + ", ".join(f"{h[1:]}:00" for h, _ in top_hours) + ".")

    lines.append(
        "Use this history to phrase suggestions naturally — e.g. 'As always around this hour, "
        "shall I put on some music?' or 'Your usual jazz, sir?'. Weave it in subtly; never read "
        "the data back verbatim, and don't mention that you have a memory log."
    )
    return "\n".join(lines)

# ─── Calendar / Librus / Birthdays ────────────────────────────────────────────
def _parse_ics_line(line):
    if ":" not in line: return None, None, {}
    key_part, value = line.split(":", 1)
    params = {}
    if ";" in key_part:
        parts = key_part.split(";")
        key = parts[0]
        for p in parts[1:]:
            if "=" in p:
                k, v = p.split("=", 1); params[k.upper()] = v
    else:
        key = key_part
    return key.upper(), value, params

def _parse_ics_datetime(value, params):
    import datetime as _dt
    v = value.strip().replace("Z", "")
    try:
        if params.get("VALUE") == "DATE" or len(v) == 8:
            return _dt.datetime.strptime(v[:8], "%Y%m%d")
        return _dt.datetime.strptime(v[:15], "%Y%m%dT%H%M%S")
    except Exception:
        return None

def _unfold_ics(text):
    lines = []
    for raw in text.splitlines():
        if (raw.startswith(" ") or raw.startswith("\t")) and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw.rstrip("\r"))
    return lines

def fetch_calendar_events(days=7):
    if not HAS_REQUESTS: return []
    mem = load_memory()
    url = (mem.get("gcal_ics_url") or "").strip()
    if not url: return []
    import datetime as _dt
    try:
        r = _requests.get(url, timeout=10)
        if r.status_code != 200:
            print(f"Calendar HTTP {r.status_code}")
            return []
        events = []; in_event = False; cur = {}
        for line in _unfold_ics(r.text):
            if line == "BEGIN:VEVENT": in_event = True; cur = {}
            elif line == "END:VEVENT":
                in_event = False
                if cur.get("start"):
                    events.append(cur)
                cur = {}
            elif in_event:
                key, value, params = _parse_ics_line(line)
                if key == "SUMMARY":
                    cur["summary"] = (value.replace("\\,", ",").replace("\\;", ";")
                                           .replace("\\n", " ").replace("\\N", " ")
                                           .replace("\\\\", "\\").strip())
                elif key == "DTSTART": cur["start"] = _parse_ics_datetime(value, params)
                elif key == "DTEND":   cur["end"]   = _parse_ics_datetime(value, params)
        today = _dt.date.today()
        end_date = today + _dt.timedelta(days=days)
        out = [e for e in events
               if e.get("start") and today <= e["start"].date() < end_date]
        out.sort(key=lambda e: e["start"])
        return out
    except Exception as e:
        print(f"Calendar fetch error: {e}")
        return []

def group_events_by_day(events, days=7):
    import datetime as _dt
    today = _dt.date.today()
    buckets = [[] for _ in range(days)]
    for e in events:
        d = e["start"].date()
        delta = (d - today).days
        if 0 <= delta < days:
            has_time = e["start"].time() != _dt.time(0, 0)
            label = e.get("summary", "(untitled)")
            if has_time:
                label = f"{e['start'].strftime('%H:%M')} {label}"
            buckets[delta].append(label)
    return buckets

def fetch_librus_events(days=7):
    mem = load_memory()
    user = (mem.get("librus_user") or "").strip()
    pw   = (mem.get("librus_pass") or "").strip()
    if not user or not pw: return []
    try:
        from librus_apix.client import new_client
        from librus_apix.schedule import get_schedule
    except ImportError:
        print("librus-apix not installed"); return []
    try:
        import datetime as _dt
        cli = new_client()
        cli.get_token(user, pw)
        today = _dt.date.today()
        out, seen_months = [], set()
        for d in range(days):
            day = today + _dt.timedelta(days=d)
            mk = (day.month, day.year)
            if mk in seen_months: continue
            seen_months.add(mk)
            try:
                sched = get_schedule(cli, str(day.month), str(day.year), True)
            except Exception as e:
                print(f"Librus schedule error: {e}"); continue
            for k, items in (sched or {}).items():
                try: day_num = int(k)
                except Exception: continue
                try: event_date = _dt.date(day.year, day.month, day_num)
                except Exception: continue
                delta_d = (event_date - today).days
                if 0 <= delta_d < days:
                    for e in items:
                        title = (getattr(e, "title", None)
                                 or getattr(e, "name", None)
                                 or getattr(e, "subject", None)
                                 or str(e))
                        title = str(title).strip()
                        if title and title not in out:
                            out.append(title)
        return out
    except Exception as e:
        print(f"Librus error: {e}")
        return []

def _fetch_birthday_ics():
    """Fetch birthdays from Google Birthday calendar ICS. Returns list of {name, month, day}."""
    if not HAS_REQUESTS: return []
    mem = load_memory()
    url = (mem.get("gcal_birthdays_ics_url") or "").strip()
    if not url: return []
    try:
        r = _requests.get(url, timeout=10)
        if r.status_code != 200:
            print(f"Birthday ICS HTTP {r.status_code}"); return []
        events = []; in_event = False; cur = {}
        for line in _unfold_ics(r.text):
            if line == "BEGIN:VEVENT": in_event = True; cur = {}
            elif line == "END:VEVENT":
                in_event = False
                if cur.get("start") and cur.get("summary"):
                    events.append(cur)
                cur = {}
            elif in_event:
                key, value, params = _parse_ics_line(line)
                if key == "SUMMARY":
                    s = (value.replace("\\,", ",").replace("\\;", ";")
                              .replace("\\n", " ").replace("\\\\", "\\").strip())
                    # Google formats these as "Alice Smith's birthday" — strip the suffix
                    low = s.lower()
                    for suf in ("'s birthday", "’s birthday", " birthday"):
                        if low.endswith(suf):
                            s = s[:len(s) - len(suf)]; break
                    cur["summary"] = s.strip()
                elif key == "DTSTART":
                    cur["start"] = _parse_ics_datetime(value, params)
        out = []
        for e in events:
            dt = e.get("start")
            if dt: out.append({"name": e["summary"], "month": dt.month, "day": dt.day})
        return out
    except Exception as e:
        print(f"Birthday ICS fetch error: {e}"); return []

def upcoming_birthdays(days=30):
    import datetime as _dt
    mem = load_memory()
    today = _dt.date.today()
    out = []
    seen = set()

    # manual entries
    for b in mem.get("birthdays", []):
        try:
            name = b["name"]; m, d = b["date"].split("-")
            m, d = int(m), int(d)
        except Exception:
            continue
        key = (name.lower().strip(), m, d)
        if key in seen: continue
        seen.add(key)
        this_year = _dt.date(today.year, m, d)
        if this_year < today:
            this_year = _dt.date(today.year + 1, m, d)
        delta_d = (this_year - today).days
        if 0 <= delta_d <= days:
            out.append({"name": name, "date": this_year, "days": delta_d})

    # ICS-sourced birthdays
    for b in _fetch_birthday_ics():
        try:
            m, d = int(b["month"]), int(b["day"])
        except Exception:
            continue
        key = (b["name"].lower().strip(), m, d)
        if key in seen: continue
        seen.add(key)
        try:
            this_year = _dt.date(today.year, m, d)
        except ValueError:
            continue
        if this_year < today:
            this_year = _dt.date(today.year + 1, m, d)
        delta_d = (this_year - today).days
        if 0 <= delta_d <= days:
            out.append({"name": b["name"], "date": this_year, "days": delta_d})

    out.sort(key=lambda x: x["days"])
    return out

class NewsCard:
    IMG_W, IMG_H = 158, 102
    CARD_W, CARD_H = 475, 120

    def __init__(self, title, tx, ty, delay=0.0, tag="NEWS",
                 img_url=None, fly_dx=-500, fly_dy=0):
        import random as _r
        self.title   = title
        self.tag     = tag
        self.tx, self.ty = tx, ty
        self.x = tx + fly_dx
        self.y = ty + fly_dy
        self.alpha   = 0.0
        self.phase   = _r.uniform(0, 6.283)
        self.delay   = delay
        self.age     = 0.0
        self.alive   = True
        self.lifetime = 45.0
        self.img_surf    = None
        self._img_bytes  = None
        self._dl_done    = False
        self._surf_built = False
        self._glitch_t   = _r.uniform(4, 9)
        self._glitch_on  = False
        self._glitch_dur = 0.0
        if img_url and HAS_REQUESTS:
            import threading
            threading.Thread(target=self._download, args=(img_url,), daemon=True).start()
        else:
            self._dl_done = True

    def _download(self, url):
        try:
            r = _requests.get(url, timeout=6)
            self._img_bytes = r.content
        except Exception:
            pass
        self._dl_done = True

    def _build_surf(self):
        if self._img_bytes:
            try:
                import io as _io
                raw = pygame.image.load(_io.BytesIO(self._img_bytes), "img.jpg")
                raw = pygame.transform.smoothscale(raw, (self.IMG_W, self.IMG_H))
                raw = raw.convert()
                # holographic blue tint
                tint = pygame.Surface((self.IMG_W, self.IMG_H), pygame.SRCALPHA)
                tint.fill((0, 30, 115, 95))
                raw.blit(tint, (0, 0))
                # horizontal scanlines
                sl = pygame.Surface((self.IMG_W, self.IMG_H), pygame.SRCALPHA)
                for sy in range(0, self.IMG_H, 2):
                    pygame.draw.line(sl, (0, 0, 0, 72), (0, sy), (self.IMG_W, sy))
                raw.blit(sl, (0, 0))
                # edge vignette
                vg = pygame.Surface((self.IMG_W, self.IMG_H), pygame.SRCALPHA)
                for edge in range(14):
                    pygame.draw.rect(vg, (0, 0, 0, int(88*(1-edge/14))),
                                     (edge, edge, self.IMG_W-edge*2, self.IMG_H-edge*2), 1)
                raw.blit(vg, (0, 0))
                self.img_surf = raw
            except Exception as ex:
                print(f"[card img] {ex}")
        self._surf_built = True

    def update(self, dt):
        import math as _m, random as _r
        self.age += dt
        if self.age < self.delay:
            return
        a = self.age - self.delay
        if self._dl_done and not self._surf_built:
            self._build_surf()
        if a < 1.0:
            self.alpha = min(1.0, a)
            self.x += (self.tx - self.x) * 0.15
            self.y += (self.ty - self.y) * 0.15
        elif a > self.lifetime - 1.2:
            self.alpha = max(0.0, 1.0 - (a - (self.lifetime - 1.2)) / 1.2)
        else:
            self.y = self.ty + 7 * _m.sin(self.phase + a * 1.05)
        self._glitch_t -= dt
        if self._glitch_t <= 0 and a > 2.0:
            self._glitch_on  = True
            self._glitch_dur = 0.14
            self._glitch_t   = _r.uniform(5, 11)
        if self._glitch_on:
            self._glitch_dur -= dt
            if self._glitch_dur <= 0:
                self._glitch_on = False
        if self.age > self.lifetime + self.delay:
            self.alive = False

    def draw(self, screen, font_tag, font_body):
        import math as _m
        if self.alpha <= 0:
            return
        a   = int(self.alpha * 255)
        W, H = self.CARD_W, self.CARD_H
        x   = int(self.x) - W // 2
        y   = int(self.y) - H // 2

        # dark panel
        bg = pygame.Surface((W, H), pygame.SRCALPHA)
        bg.fill((0, 5, 20, int(a * 0.90)))
        screen.blit(bg, (x, y))

        # image section
        ix, iy = x + 8, y + 9
        if self.img_surf:
            ic = self.img_surf.copy()
            ic.set_alpha(a)
            if self._glitch_on:
                off = 3
                for dx2, dy2 in [(-off, 0), (off, 0), (0, -off)]:
                    screen.blit(ic, (ix+dx2, iy+dy2), special_flags=pygame.BLEND_ADD)
            else:
                screen.blit(ic, (ix, iy))
            pygame.draw.rect(screen, (0, 150, 255, int(a*0.65)),
                             (ix-1, iy-1, self.IMG_W+2, self.IMG_H+2), 1)
        else:
            # animated grid placeholder
            pg = pygame.Surface((self.IMG_W, self.IMG_H), pygame.SRCALPHA)
            pg.fill((0, 10, 38, int(a*0.75)))
            ta = self.age * 1.4
            for gi in range(6):
                for gj in range(4):
                    ga = int(25 + 18*_m.sin(ta + gi*0.9 + gj*1.3))
                    gx2 = gi*(self.IMG_W//6); gy2 = gj*(self.IMG_H//4)
                    pygame.draw.rect(pg, (0, 80, 210, ga),
                                     (gx2+2, gy2+2, self.IMG_W//6-4, self.IMG_H//4-4), 1)
            if not self._dl_done:
                dots = "." * (int(self.age*3) % 4)
                lt = font_tag.render("LOADING" + dots, True, (0, 130, 220))
                lt.set_alpha(a // 2)
                pg.blit(lt, (self.IMG_W//2 - lt.get_width()//2, self.IMG_H//2 - 6))
            screen.blit(pg, (ix, iy))
            pygame.draw.rect(screen, (0, 80, 180, int(a*0.5)),
                             (ix-1, iy-1, self.IMG_W+2, self.IMG_H+2), 1)

        # vertical divider
        div_x = ix + self.IMG_W + 6
        pygame.draw.line(screen, (0, 90, 200, int(a*0.45)),
                         (div_x, y+7), (div_x, y+H-7), 1)

        # text section
        tx2 = div_x + 10
        tw  = W - (self.IMG_W + 34)

        # tag label
        ts = font_tag.render(">> " + self.tag, True, (0, 210, 255))
        ts.set_alpha(a)
        screen.blit(ts, (tx2, y+9))
        pygame.draw.line(screen, (0, 140, 255, int(a*0.35)),
                         (tx2, y+22), (tx2+tw-4, y+22), 1)

        # word-wrapped headline
        words = self.title.split()
        lines2 = []; line2 = ""
        for w in words:
            test = (line2 + " " + w).strip()
            if font_body.size(test)[0] < tw - 4:
                line2 = test
            else:
                lines2.append(line2); line2 = w
        lines2.append(line2)
        for i2, ln in enumerate(lines2[:3]):
            col = (235, 242, 255) if i2 == 0 else (165, 188, 220)
            hs  = font_body.render(ln, True, col)
            hs.set_alpha(a)
            screen.blit(hs, (tx2, y+28 + i2*17))

        # lifetime progress bar
        prog = max(0.0, 1.0 - max(0.0, self.age - self.delay) / self.lifetime)
        bx2 = tx2; by2 = y+H-11; bw2 = tw-4
        pygame.draw.rect(screen, (0, 35, 90,  int(a*0.5)),   (bx2, by2, bw2, 3))
        pygame.draw.rect(screen, (0, 170, 255, int(a*0.85)), (bx2, by2, int(bw2*prog), 3))

        # outer border (glows bright during glitch)
        bd = pygame.Surface((W, H), pygame.SRCALPHA)
        bc = (0, 220, 255, int(a*0.9)) if self._glitch_on else (0, 120, 255, int(a*0.55))
        pygame.draw.rect(bd, bc, (0, 0, W, H), 1)
        screen.blit(bd, (x, y))

        # corner ticks
        tc = (0, 200, 255, a)
        for cx2, cy2, sx, sy in [(x,y,1,1),(x+W,y,-1,1),(x,y+H,1,-1),(x+W,y+H,-1,-1)]:
            pygame.draw.lines(screen, tc, False,
                              [(cx2+sx*13, cy2),(cx2, cy2),(cx2, cy2+sy*13)], 1)

class DayCard:
    """Holographic single-day tile — part of the weekly preview strip."""
    DEFAULT_W, DEFAULT_H = 260, 210

    def __init__(self, day_label, events, tx, ty, delay=0.0,
                 fly_dx=0, fly_dy=-700, w=None, h=None, tag_color=(0, 210, 255),
                 lifetime=55.0):
        import random as _r
        self.day_label = day_label
        self.events    = events or []
        self.tx, self.ty = tx, ty
        self.x = tx + fly_dx
        self.y = ty + fly_dy
        self.alpha   = 0.0
        self.delay   = delay
        self.age     = 0.0
        self.alive   = True
        self.lifetime = lifetime
        self.phase   = _r.uniform(0, 6.283)
        self.CARD_W = w or self.DEFAULT_W
        self.CARD_H = h or self.DEFAULT_H
        self.tag_color = tag_color
        self._glitch_t   = _r.uniform(3, 8)
        self._glitch_on  = False
        self._glitch_dur = 0.0

    def update(self, dt):
        import math as _m, random as _r
        self.age += dt
        if self.age < self.delay: return
        a = self.age - self.delay
        if a < 1.0:
            self.alpha = min(1.0, a)
            self.x += (self.tx - self.x) * 0.18
            self.y += (self.ty - self.y) * 0.18
        elif a > self.lifetime - 1.2:
            self.alpha = max(0.0, 1.0 - (a - (self.lifetime - 1.2)) / 1.2)
        else:
            self.y = self.ty + 4 * _m.sin(self.phase + a * 1.1)
        self._glitch_t -= dt
        if self._glitch_t <= 0 and a > 2.0:
            self._glitch_on  = True
            self._glitch_dur = 0.12
            self._glitch_t   = _r.uniform(6, 12)
        if self._glitch_on:
            self._glitch_dur -= dt
            if self._glitch_dur <= 0: self._glitch_on = False
        if self.age > self.lifetime + self.delay:
            self.alive = False

    def draw(self, screen, font_tag, font_body):
        if self.alpha <= 0: return
        a = int(self.alpha * 255)
        W, H = self.CARD_W, self.CARD_H
        x = int(self.x) - W // 2
        y = int(self.y) - H // 2

        # panel
        bg = pygame.Surface((W, H), pygame.SRCALPHA)
        bg.fill((0, 5, 22, int(a * 0.88)))
        screen.blit(bg, (x, y))

        # header band
        hh = 26
        hdr = pygame.Surface((W, hh), pygame.SRCALPHA)
        hdr.fill((0, 45, 115, int(a * 0.65)))
        screen.blit(hdr, (x, y))
        ts = font_tag.render(self.day_label, True, (220, 240, 255))
        ts.set_alpha(a)
        screen.blit(ts, (x + W // 2 - ts.get_width() // 2, y + 6))

        # event lines (word-wrapped, max 2 wrapped lines per event)
        yy = y + hh + 8
        max_w = W - 18
        line_h = 17
        if not self.events:
            es = font_body.render("— clear —", True, (100, 140, 200))
            es.set_alpha(int(a * 0.75))
            screen.blit(es, (x + W // 2 - es.get_width() // 2, yy + 10))
        else:
            total_line_budget = max(2, (H - hh - 18) // line_h)
            rendered_count = 0          # how many source events fully fit
            used_lines = 0
            # reserve 1 line for "+N more" footer if needed
            for idx, ev in enumerate(self.events):
                # wrap this event to at most 2 lines
                bullet = "• "
                indent = "  "
                words = str(ev).split()
                wrapped = []
                cur_line = bullet
                for w in words:
                    test = cur_line + (w if cur_line in (bullet, indent) else " " + w)
                    if font_body.size(test)[0] <= max_w:
                        cur_line = test
                    else:
                        wrapped.append(cur_line)
                        cur_line = indent + w
                        if len(wrapped) >= 2:
                            break
                if len(wrapped) < 2:
                    wrapped.append(cur_line)
                # ellipsize last line if it overflows
                last = wrapped[-1]
                if font_body.size(last)[0] > max_w:
                    while font_body.size(last + "…")[0] > max_w and len(last) > 3:
                        last = last[:-1]
                    wrapped[-1] = last + "…"
                # remaining budget check (reserve 1 line for "+N more")
                remaining_events = len(self.events) - idx
                reserve = 1 if remaining_events > 1 else 0
                if used_lines + len(wrapped) > total_line_budget - reserve:
                    break
                col_first  = (215, 232, 255)
                col_cont   = (165, 195, 235)
                for wi, ln in enumerate(wrapped):
                    es = font_body.render(ln, True, col_first if wi == 0 else col_cont)
                    es.set_alpha(a if wi == 0 else int(a * 0.85))
                    screen.blit(es, (x + 8, yy + (used_lines + wi) * line_h))
                used_lines    += len(wrapped)
                rendered_count = idx + 1
            if rendered_count < len(self.events):
                more = font_body.render(f"+{len(self.events) - rendered_count} more",
                                         True, (120, 170, 220))
                more.set_alpha(int(a * 0.85))
                screen.blit(more, (x + 8, yy + used_lines * line_h))

        # border
        bc = ((0, 235, 255, int(a * 0.95)) if self._glitch_on
              else (0, 135, 255, int(a * 0.6)))
        bd = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.rect(bd, bc, (0, 0, W, H), 1)
        pygame.draw.line(bd, bc, (0, hh), (W, hh), 1)
        screen.blit(bd, (x, y))

        # corner ticks
        tc = (0, 210, 255, a)
        for cx2, cy2, sx, sy in [(x,y,1,1),(x+W,y,-1,1),(x,y+H,1,-1),(x+W,y+H,-1,-1)]:
            pygame.draw.lines(screen, tc, False,
                              [(cx2+sx*10, cy2),(cx2, cy2),(cx2, cy2+sy*10)], 1)

class JarvisVisual:
    def __init__(self):
        self.W = self.H = self.cx = self.cy = 0
        self.t            = 0.0
        self.particles    = []
        self.ripples      = []
        self.news_cards   = []
        self.screen       = None
        self.clock        = None
        self.font_hud     = None
        self.font_card_body  = None
        self.font_data    = None
        self._overlay     = None
        self._glow_cache  = {}
        self._sphere_nodes  = []
        self._sphere_edges  = []
        self._sphere_rot    = 0.0
        self._flow_offsets  = []   # per-edge animated flow pulse position
        self._orbit_labels  = [
            "SYS.OK", "BIOMETRIC.AUTH", "CORE.SYNC", "NET.NODE.3F",
            "ENC.AES-256", "TELEMETRY.LIVE", "RELAY.HUB", "WATCH.ACTIVE",
        ]
        self._orbit_surfs   = []
        # cinematic enhancements
        self.data_streams   = []
        self._ds_font       = None
        self._ds_char_head  = {}
        self._ds_char_body  = {}
        self._grid_surf     = None
        self._grid_y0       = 0
        self._grid_h        = 0
        self._scanline_surf = None
        self.reticules      = []
        self._reticule_cd   = 2.5
        self.power_arcs     = []
        self._arc_cd        = 4.0
        self.diag_bars      = []
        self._bloom_small   = None
        self._bloom_tiny    = None

    def setup(self):
        pygame.display.init(); pygame.font.init()
        info = pygame.display.Info()
        self.W, self.H = info.current_w, info.current_h
        self.screen = pygame.display.set_mode((self.W, self.H), pygame.FULLSCREEN | pygame.NOFRAME)
        pygame.display.set_caption("J.A.R.V.I.S.")
        self.clock = pygame.time.Clock()
        self.cx, self.cy = self.W // 2, self.H // 2
        try:
            self.font_hud       = pygame.font.SysFont("consolas", 20, bold=True)
            self.font_card_body = pygame.font.SysFont("consolas", 13)
            self.font_data      = pygame.font.SysFont("consolas", 11)
        except Exception:
            self.font_hud = self.font_card_body = self.font_data = pygame.font.Font(None, 18)
        self._overlay = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        self._init_particles()
        try:
            small = pygame.font.SysFont("consolas", 10, bold=True)
            self._orbit_surfs = [small.render(lbl, True, (130, 200, 255))
                                 for lbl in self._orbit_labels]
        except Exception:
            self._orbit_surfs = []
        self._init_cinematic()
        if HAS_NUMPY:
            self._init_sphere_numpy()
        else:
            self._init_sphere()

    def _init_cinematic(self):
        """Pre-build grid, scanlines, data-stream glyph surfs, diagnostic bars."""
        import random as _r
        # ── Scanline overlay (subtle) ─────────────────────────────────────────
        sl = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        for y in range(0, self.H, 3):
            pygame.draw.line(sl, (0, 15, 30, 22), (0, y), (self.W, y), 1)
        self._scanline_surf = sl

        # ── Perspective grid (vertical converging lines, pre-rendered) ────────
        cx = self.W // 2
        self._grid_h  = int(self.H * 0.36)
        self._grid_y0 = self.H - self._grid_h
        g = pygame.Surface((self.W, self._grid_h), pygame.SRCALPHA)
        for vx in range(-9, 10):
            if vx == 0: continue
            bot_x = cx + vx * (self.W // 11)
            a = max(18, 55 - abs(vx) * 4)
            pygame.draw.line(g, (0, 110, 210, a), (cx, 0), (bot_x, self._grid_h), 1)
        self._grid_surf = g

        # ── Data-stream glyphs (pre-rendered for speed) ───────────────────────
        try:
            self._ds_font = pygame.font.SysFont("consolas", 12, bold=True)
        except Exception:
            self._ds_font = pygame.font.Font(None, 14)
        chars = "0123456789ABCDEF#$%&@*+-=/█▓▒░"
        self._ds_chars = list(chars)
        self._ds_char_head = {c: self._ds_font.render(c, True, (225, 250, 255)) for c in chars}
        self._ds_char_body = {c: self._ds_font.render(c, True, (60, 140, 220))  for c in chars}
        self.data_streams  = []
        # left + right edge columns
        for side, base_x in [("L", 14), ("R", self.W - 14 - 12)]:
            for col_i in range(5):
                stream_len = _r.randint(18, 28)
                x = base_x + (col_i * 16 if side == "L" else -col_i * 16)
                self.data_streams.append({
                    "x": x,
                    "y": _r.uniform(-400, self.H),
                    "speed": _r.uniform(55, 120),
                    "chars": [_r.choice(chars) for _ in range(stream_len)],
                    "swap_t": 0.0,
                    "len": stream_len,
                })

        # ── Bloom scratch surfaces (allocated once) ───────────────────────────
        self._bloom_small = pygame.Surface((self.W // 4, self.H // 4))
        self._bloom_tiny  = pygame.Surface((self.W // 10, self.H // 10))

        # ── Diagnostic bars ───────────────────────────────────────────────────
        import random as _rr
        self.diag_bars = [
            {"label": "CORE PWR",  "value": 0.82, "target": 0.82, "col": (0, 200, 255)},
            {"label": "NEURAL NET","value": 0.91, "target": 0.91, "col": (0, 220, 220)},
            {"label": "UPLINK",    "value": 0.67, "target": 0.67, "col": (100, 180, 255)},
            {"label": "PROCESS",   "value": 0.55, "target": 0.55, "col": (80, 200, 255)},
            {"label": "BIO SCAN",  "value": 0.98, "target": 0.98, "col": (0, 240, 200)},
            {"label": "ENCRYPT",   "value": 0.88, "target": 0.88, "col": (130, 200, 255)},
        ]
        self._diag_t = 0.0

    def _col(self, state):
        return {
            "speaking":  ((0, 180, 255), (0, 100, 220), (0,  50, 160)),
            "listening": ((0, 230, 210), (0, 160, 180), (0,  90, 130)),
            "waking":    ((120, 160, 255), (60, 90, 220), (20, 40, 160)),
        }.get(state, ((30, 120, 240), (15, 70, 190), (5, 30, 120)))

    def _init_particles(self):
        import random as _r, math as _m
        self.particles = []
        for _ in range(22):
            angle  = _r.uniform(0, _m.tau)
            base_r = _r.uniform(215, 330)
            self.particles.append({
                "angle": angle, "base_r": base_r, "r": base_r,
                "speed":   _r.uniform(0.003, 0.010) * _r.choice([-1, 1]),
                "size":    _r.uniform(2, 4.5),
                "alpha":   _r.uniform(0.4, 0.9),
                "y_phase": _r.uniform(0, _m.tau),
                "y_amp":   _r.uniform(6, 18),
                "y_speed": _r.uniform(0.002, 0.006) * _r.choice([-1, 1]),
                "shape":   _r.choices(["dot", "diamond"], weights=[3, 2])[0],
            })

    def _init_sphere(self):
        """Fallback wireframe sphere (no numpy)."""
        import math as _m, random as _r
        N = 58
        golden = (1 + _m.sqrt(5)) / 2
        nodes = []
        for i in range(N):
            theta = _m.acos(max(-1.0, min(1.0, 1 - 2*(i+0.5)/N)))
            phi   = _m.tau * i / golden
            nodes.append((theta, phi))
        self._sphere_nodes = nodes
        def chord(a, b):
            t1,p1 = a; t2,p2 = b
            x1,y1,z1 = _m.sin(t1)*_m.cos(p1), _m.cos(t1), _m.sin(t1)*_m.sin(p1)
            x2,y2,z2 = _m.sin(t2)*_m.cos(p2), _m.cos(t2), _m.sin(t2)*_m.sin(p2)
            return _m.sqrt((x1-x2)**2+(y1-y2)**2+(z1-z2)**2)
        edges = set()
        for i in range(N):
            ds = sorted((chord(nodes[i], nodes[j]), j) for j in range(N) if j != i)
            for _, j in ds[:4]:
                edges.add((min(i,j), max(i,j)))
        self._sphere_edges = list(edges)
        self._flow_offsets = [_r.uniform(0, 1.0) for _ in self._sphere_edges]
        self._glow_cache.clear()

    def _init_sphere_numpy(self):
        """Pre-compute geometry for per-pixel Phong+energy-web sphere."""
        np = _np
        R = 195
        size = R * 2 + 6
        Y, X = np.mgrid[0:size, 0:size]
        c = R + 3
        dx = (X - c).astype(np.float32)
        dy = (Y - c).astype(np.float32)
        r2 = dx**2 + dy**2
        mask = r2 <= float(R * R)
        inv_R = 1.0 / R
        nx = np.where(mask, dx * inv_R, 0.0).astype(np.float32)
        ny = np.where(mask, dy * inv_R, 0.0).astype(np.float32)
        nz = np.where(mask, np.sqrt(np.maximum(0.0, 1.0 - nx**2 - ny**2)), 0.0).astype(np.float32)
        theta = np.arccos(np.clip(ny, -1.0, 1.0)).astype(np.float32)
        phi   = np.arctan2(nx, nz).astype(np.float32)
        # Precompute theta-dependent web envelopes (constant)
        self._sp_sin_t7 = np.sin(theta * 7.0).astype(np.float32)
        self._sp_cos_t5 = np.cos(theta * 5.0).astype(np.float32)
        self._sp_sin_t4 = np.sin(theta * 4.0).astype(np.float32)
        self._sp_mask = mask
        self._sp_nx, self._sp_ny, self._sp_nz = nx, ny, nz
        self._sp_phi  = phi
        self._sp_R    = R
        self._sp_size = size
        self._sp_surf = pygame.Surface((size, size))
        self._sp_surf.set_colorkey((0, 0, 0))
        self._sp_rings = []   # rotating outer ring angles
        self._glow_cache.clear()

    def _render_sphere(self, state, t):
        """Render the numpy Phong+energy-web sphere; return Surface."""
        np = _np
        bright, mid, dim = self._col(state)
        mask = self._sp_mask
        nx, ny, nz = self._sp_nx, self._sp_ny, self._sp_nz
        phi = self._sp_phi

        # Rotating key light
        la  = t * 0.42
        lx_ = math.cos(la) * 0.70
        ly_ = -0.40
        lz_ = math.sin(la) * 0.70 + 0.65
        ln  = math.sqrt(lx_**2 + ly_**2 + lz_**2)
        lx_, ly_, lz_ = lx_/ln, ly_/ln, lz_/ln
        lx = np.float32(lx_); ly = np.float32(ly_); lz = np.float32(lz_)

        diff = np.maximum(0.0, nx*lx + ny*ly + nz*lz)

        # Blinn-Phong specular
        hx_ = lx_; hy_ = ly_; hz_ = lz_ + 1.0
        hn  = math.sqrt(hx_**2 + hy_**2 + hz_**2)
        hx  = np.float32(hx_/hn); hy = np.float32(hy_/hn); hz = np.float32(hz_/hn)
        spec = np.where(mask, np.maximum(0.0, nx*hx + ny*hy + nz*hz)**72, 0.0)

        # Fresnel rim
        fresnel = np.where(mask, (1.0 - nz)**3.5, 0.0)

        # Inner-core glow (center = high nz)
        core_glow = np.where(mask, nz**2 * 0.35, 0.0)

        # Animated energy web — two crossing sine-wave families
        phi_rot = phi + np.float32(t * 0.28)
        web_a = self._sp_sin_t7 * np.cos(phi_rot * np.float32(5.0) + np.float32(t * 0.18))
        web_b = self._sp_cos_t5 * np.sin(phi_rot * np.float32(7.0) + np.float32(t * 0.22))
        web_c = self._sp_sin_t4 * np.cos(phi_rot * np.float32(3.0) - np.float32(t * 0.12))
        web   = np.where(mask, np.exp(-np.abs(web_a + web_b + web_c * 0.5) * 5.0) * 0.85, 0.0)

        pulse = np.float32(1.0 + 0.13 * math.sin(t * (9.5 if state=="speaking" else 2.2)))

        br, bg, bb = bright[0]/255.0, bright[1]/255.0, bright[2]/255.0
        mr, mg, mb = mid[0]/255.0,   mid[1]/255.0,   mid[2]/255.0
        dr, dg, db = dim[0]/255.0,   dim[1]/255.0,   dim[2]/255.0

        r_f = np.where(mask, np.clip((
            dr * 0.08 + mr * diff * 0.45 + br * web * 0.75 +
            br * fresnel * 0.55 + br * core_glow + spec * 0.85) * pulse, 0.0, 1.0), 0.0)
        g_f = np.where(mask, np.clip((
            dg * 0.08 + mg * diff * 0.45 + bg * web * 0.75 +
            bg * fresnel * 0.60 + bg * core_glow + spec * 0.90) * pulse, 0.0, 1.0), 0.0)
        b_f = np.where(mask, np.clip((
            db * 0.12 + mb * diff * 0.50 + bb * web * 0.80 +
            bb * fresnel * 0.80 + bb * core_glow + spec * 1.00) * pulse, 0.0, 1.0), 0.0)

        arr = np.stack([(r_f * 255).astype(np.uint8),
                        (g_f * 255).astype(np.uint8),
                        (b_f * 255).astype(np.uint8)], axis=2)
        pygame.surfarray.blit_array(self._sp_surf,
                                    _np.ascontiguousarray(arr.transpose(1, 0, 2)))
        return self._sp_surf

    def _glow_surf(self, r, rgba):
        key = (r, rgba)
        if key not in self._glow_cache:
            s = pygame.Surface((r*2+2, r*2+2), pygame.SRCALPHA)
            pygame.draw.circle(s, rgba, (r+1, r+1), r)
            self._glow_cache[key] = s
        return self._glow_cache[key]

    def _blit_c(self, surf, cx, cy):
        self.screen.blit(surf, (cx - surf.get_width()//2, cy - surf.get_height()//2))

    def _ring_on_ov(self, ov, cx, cy, r, offset, tick_n, col, w=1):
        import math as _m
        pygame.draw.circle(ov, col, (cx, cy), r, w)
        major = max(1, tick_n // 4)
        for i in range(tick_n):
            a = offset + i * _m.tau / tick_n
            tl = 9 if i % major == 0 else 4
            ca, sa = _m.cos(a), _m.sin(a)
            pygame.draw.line(ov, col,
                             (int(cx+(r-1)*ca),    int(cy+(r-1)*sa)),
                             (int(cx+(r-1-tl)*ca), int(cy+(r-1-tl)*sa)), 1)

    def _draw_reactor(self, cx, cy, state, t):
        import math as _m, random as _r
        bright, mid, dim = self._col(state)
        R = self._sp_R if HAS_NUMPY else 195

        pulse = (1.0 + 0.22*_m.sin(t*9.5) if state=="speaking"
                 else 1.0+0.14*_m.sin(t*5.5) if state=="waking"
                 else 1.0+0.05*_m.sin(t*1.4))

        # ── Atmospheric halo layers ───────────────────────────────────────────
        for i in range(9, 0, -1):
            ga = int(22*_m.exp(-i*0.42)*pulse)
            self._blit_c(self._glow_surf(R + i*11, (*dim, ga)), cx, cy)

        # ── Numpy pixel-lit sphere ─────────────────────────────────────────────
        if HAS_NUMPY:
            sp = self._render_sphere(state, t)
            self._blit_c(sp, cx, cy)
        else:
            # wireframe fallback (no numpy)
            self._sphere_rot += 0.003
            rot = self._sphere_rot
            ov = self._overlay; ov.fill((0,0,0,0))
            for theta, phi in self._sphere_nodes:
                p  = phi + rot
                x3 = _m.sin(theta)*_m.cos(p)
                y3 = _m.cos(theta)
                z3 = _m.sin(theta)*_m.sin(p)
                if z3 > 0:
                    self._blit_c(self._glow_surf(3, (*bright, int(100*z3))),
                                 cx+int(x3*R), cy-int(y3*R))
            self.screen.blit(ov,(0,0))

        # ── Thin rotating outer rings ──────────────────────────────────────────
        ov = self._overlay; ov.fill((0,0,0,0))
        for ring_r, speed, alpha in [(R+18, 0.25, 38), (R+34, -0.16, 24), (R+52, 0.10, 16)]:
            angle = t * speed
            ring_a = int(alpha * pulse)
            pygame.draw.circle(ov, (*dim, ring_a), (cx, cy), ring_r, 1)
            for k in range(8):
                a = angle + k * _m.tau/8
                pygame.draw.line(ov, (*bright, ring_a//2),
                                 (int(cx+(ring_r-5)*_m.cos(a)), int(cy+(ring_r-5)*_m.sin(a))),
                                 (int(cx+(ring_r+5)*_m.cos(a)), int(cy+(ring_r+5)*_m.sin(a))), 1)
        self.screen.blit(ov, (0,0))

        # ── Core white-hot point ──────────────────────────────────────────────
        core_r = int(14*pulse)
        for i in range(6, 0, -1):
            self._blit_c(self._glow_surf(core_r+i*7, (*bright, int(160*_m.exp(-i*0.6)))), cx, cy)
        self._blit_c(self._glow_surf(core_r,            (*bright, 230)), cx, cy)
        self._blit_c(self._glow_surf(int(core_r*0.5),   (210,235,255,250)), cx, cy)
        self._blit_c(self._glow_surf(max(1,int(core_r*0.2)), (255,255,255,255)), cx, cy)

        # ── Speaking ripples ──────────────────────────────────────────────────
        if state=="speaking" and _r.random()<0.12:
            self.ripples.append({"r": float(R-10), "alpha": 100.0})
        for rp in self.ripples[:]:
            r=int(rp["r"]); a=int(rp["alpha"])
            if a<=0 or r>R+160: self.ripples.remove(rp); continue
            rs=pygame.Surface((r*2+4,r*2+4), pygame.SRCALPHA)
            pygame.draw.circle(rs, (*bright, a), (r+2,r+2), r, 2)
            self._blit_c(rs, cx, cy)
            rp["r"]+=3.2; rp["alpha"]-=3.8

        # ── Orbital data labels ───────────────────────────────────────────────
        if self._orbit_surfs:
            n = len(self._orbit_surfs)
            orbit_r = R + 92
            for i, surf in enumerate(self._orbit_surfs):
                ang = t * 0.14 + i * _m.tau / n
                ox = cx + int(_m.cos(ang) * orbit_r)
                oy = cy + int(_m.sin(ang) * orbit_r * 0.55)  # elliptical
                s  = surf.copy()
                fade = int(120 + 90 * _m.sin(t * 0.8 + i))
                s.set_alpha(max(40, min(220, fade)))
                self.screen.blit(s, (ox - s.get_width() // 2, oy - s.get_height() // 2))

        # ── Lens flare during speaking ────────────────────────────────────────
        if state == "speaking":
            fa = int(30 + 20 * _m.sin(t * 9.5))
            fl = pygame.Surface((self.W, 2), pygame.SRCALPHA)
            fl.fill((*bright, fa))
            self.screen.blit(fl, (0, cy - 1))
            fv = pygame.Surface((2, self.H), pygame.SRCALPHA)
            fv.fill((*bright, fa))
            self.screen.blit(fv, (cx - 1, 0))

        # ── Data readouts ─────────────────────────────────────────────────────
        a_fade = int(110+50*_m.sin(t*0.75))
        for lx,ly,text in [(cx+270,cy-100,f"SYS  {int(50+30*_m.sin(t*0.7))}%"),
                            (cx+270,cy+100,f"MEM  {int(60+20*_m.sin(t*0.5))}%"),
                            (cx-270,cy-100,"NET  ONLINE"),
                            (cx-270,cy+100,f"CPU  {int(40+35*abs(_m.sin(t*0.9)))}%")]:
            s=self.font_data.render(text, True, bright); s.set_alpha(a_fade)
            rx=lx-s.get_width()//2; ry=ly-s.get_height()//2
            self.screen.blit(s,(rx,ry))
            bw=s.get_width()+14; bh=s.get_height()+8
            bs=pygame.Surface((bw,bh),pygame.SRCALPHA)
            pygame.draw.rect(bs,(*bright,int(a_fade*0.40)),(0,0,bw,bh),1)
            self.screen.blit(bs,(rx-7,ry-4))

    def _draw_particles(self, state, t):
        import math as _m
        bright,_,_ = self._col(state)
        ov = self._overlay; ov.fill((0,0,0,0))
        sm = 2.8 if state=="speaking" else 1.5 if state=="listening" else 1.0
        for p in self.particles:
            p["angle"]  += p["speed"]  * sm
            p["y_phase"]+= p["y_speed"]* sm
            tr = p["base_r"]+(35*_m.sin(t*2.5+p["angle"]) if state=="speaking" else 0)
            p["r"]+=(tr-p["r"])*0.06
            x = self.cx+p["r"]*_m.cos(p["angle"])
            y = self.cy+p["r"]*_m.sin(p["angle"])*0.5+p["y_amp"]*_m.sin(p["y_phase"])
            al = p["alpha"]*(0.5+0.5*_m.sin(t*0.9+p["angle"])) if state=="idle" else p["alpha"]
            a=int(al*255); s=max(1,int(p["size"])); ix,iy=int(x),int(y)
            if p["shape"]=="diamond":
                pygame.draw.polygon(ov,(*bright,a),[(ix,iy-s),(ix+s,iy),(ix,iy+s),(ix-s,iy)])
            else:
                pygame.draw.circle(ov,(*bright,a),(ix,iy),s)
        self.screen.blit(ov,(0,0))

    def _draw_corners(self):
        c=(18,55,140); sz=44; W,H=self.W,self.H
        for x0,y0,dx,dy in [(10,10,1,1),(W-10,10,-1,1),(10,H-10,1,-1),(W-10,H-10,-1,-1)]:
            pygame.draw.lines(self.screen,c,False,
                              [(x0+dx*sz,y0),(x0,y0),(x0,y0+dy*sz)],1)

    def _draw_grid_floor(self, t):
        """Scrolling perspective grid at bottom — the Iron Man floor."""
        if self._grid_surf is None: return
        self.screen.blit(self._grid_surf, (0, self._grid_y0))
        num = 14
        for i in range(num):
            tl = ((i / num) + t * 0.06) % 1.0
            y_rel = (tl ** 1.9) * self._grid_h
            y = int(self._grid_y0 + y_rel)
            alpha = int(20 + 85 * tl)
            ls = pygame.Surface((self.W, 1), pygame.SRCALPHA)
            ls.fill((0, 110, 210, alpha))
            self.screen.blit(ls, (0, y))

    def _draw_data_streams(self, dt):
        """Matrix-style glyph columns on left + right edges."""
        import random as _r
        if not self.data_streams or self._ds_font is None: return
        for s in self.data_streams:
            s["y"] += s["speed"] * dt
            s["swap_t"] -= dt
            if s["swap_t"] <= 0:
                idx = _r.randrange(s["len"])
                s["chars"][idx] = _r.choice(self._ds_chars)
                s["swap_t"] = _r.uniform(0.05, 0.22)
            if s["y"] > self.H + 100:
                s["y"] = -s["len"] * 14 - _r.uniform(0, 300)
                s["chars"] = [_r.choice(self._ds_chars) for _ in range(s["len"])]
            head_y = s["y"]
            for i, ch in enumerate(s["chars"]):
                y = int(head_y - i * 14)
                if y < -16 or y > self.H: continue
                if i == 0:
                    surf = self._ds_char_head.get(ch)
                    a = 235
                else:
                    surf = self._ds_char_body.get(ch)
                    fade = max(0.0, 1.0 - i / s["len"])
                    a = int(18 + 180 * fade)
                if surf is None: continue
                surf.set_alpha(a)
                self.screen.blit(surf, (s["x"], y))

    def _spawn_reticule(self):
        import random as _r
        # avoid sphere center area
        while True:
            x = _r.randint(80, self.W - 80)
            y = _r.randint(80, self.H - 120)
            if abs(x - self.cx) > 260 or abs(y - self.cy) > 260:
                break
        self.reticules.append({
            "x": x, "y": y, "age": 0.0, "life": 2.4,
            "rot": _r.uniform(0, 6.283),
            "size": _r.randint(34, 58),
            "label": _r.choice(["TARGET","SCAN","TRACE","LOCK","OBJ.ID"]),
            "code":  f"{_r.randint(100,999)}-{_r.choice('ABCDEFGH')}{_r.randint(10,99)}",
        })

    def _update_reticules(self, dt):
        self._reticule_cd -= dt
        if self._reticule_cd <= 0:
            self._spawn_reticule()
            import random as _r
            self._reticule_cd = _r.uniform(2.8, 5.5)
        for r in self.reticules[:]:
            r["age"] += dt
            r["rot"] += dt * 1.2
            if r["age"] >= r["life"]:
                self.reticules.remove(r)

    def _draw_reticules(self):
        import math as _m
        for r in self.reticules:
            a_norm = r["age"] / r["life"]
            if a_norm < 0.15:
                alpha = a_norm / 0.15
            elif a_norm > 0.75:
                alpha = max(0.0, 1.0 - (a_norm - 0.75) / 0.25)
            else:
                alpha = 1.0
            A = int(alpha * 220)
            if A <= 4: continue
            cx, cy = r["x"], r["y"]
            sz = r["size"]
            # expanding grow-in
            grow = min(1.0, r["age"] * 2.5)
            sz = int(sz * (0.6 + 0.4 * grow))
            col = (0, 230, 255, A)

            # rotating outer square-ring
            pts = []
            for k in range(4):
                ang = r["rot"] + k * _m.pi / 2
                pts.append((cx + int(_m.cos(ang) * sz),
                            cy + int(_m.sin(ang) * sz)))
            ov = pygame.Surface((sz*2+12, sz*2+12), pygame.SRCALPHA)
            ox, oy = cx - sz - 6, cy - sz - 6
            for i in range(4):
                x1, y1 = pts[i][0] - ox, pts[i][1] - oy
                x2, y2 = pts[(i+1)%4][0] - ox, pts[(i+1)%4][1] - oy
                pygame.draw.line(ov, col, (x1, y1), (x2, y2), 1)
            # inner cross
            pygame.draw.line(ov, col, (sz+6, sz-int(sz*0.6)+6), (sz+6, sz+int(sz*0.6)+6), 1)
            pygame.draw.line(ov, col, (sz-int(sz*0.6)+6, sz+6), (sz+int(sz*0.6)+6, sz+6), 1)
            # center dot
            pygame.draw.circle(ov, col, (sz+6, sz+6), 2)
            self.screen.blit(ov, (ox, oy))
            # label
            lbl = self.font_data.render(f"{r['label']}  {r['code']}", True, (0, 230, 255))
            lbl.set_alpha(A)
            self.screen.blit(lbl, (cx - lbl.get_width() // 2, cy + sz + 8))

    def _spawn_power_arc(self):
        import random as _r, math as _m
        # arc from sphere surface to random edge point
        R = (self._sp_R if HAS_NUMPY else 195)
        ang = _r.uniform(0, _m.tau)
        start = (int(self.cx + _m.cos(ang) * R), int(self.cy + _m.sin(ang) * R))
        # end: random edge
        edge_choice = _r.choice(["top","bot","left","right"])
        if edge_choice == "top":
            end = (_r.randint(80, self.W-80), _r.randint(20, 180))
        elif edge_choice == "bot":
            end = (_r.randint(80, self.W-80), _r.randint(self.H-240, self.H-60))
        elif edge_choice == "left":
            end = (_r.randint(40, 220), _r.randint(120, self.H-180))
        else:
            end = (_r.randint(self.W-220, self.W-40), _r.randint(120, self.H-180))
        # jagged midpoints
        segs = 10
        pts = []
        for i in range(segs + 1):
            t = i / segs
            x = start[0] + (end[0] - start[0]) * t
            y = start[1] + (end[1] - start[1]) * t
            if 0 < i < segs:
                jitter = 28 * (1 - abs(t - 0.5) * 2)
                x += _r.uniform(-jitter, jitter)
                y += _r.uniform(-jitter, jitter)
            pts.append((int(x), int(y)))
        self.power_arcs.append({"pts": pts, "age": 0.0, "life": 0.38})

    def _update_power_arcs(self, dt, state):
        self._arc_cd -= dt
        threshold = (1.6 if state == "speaking"
                     else 3.0 if state == "waking"
                     else 6.0)
        if self._arc_cd <= 0:
            self._spawn_power_arc()
            import random as _r
            self._arc_cd = _r.uniform(threshold * 0.6, threshold * 1.2)
        for a in self.power_arcs[:]:
            a["age"] += dt
            if a["age"] >= a["life"]:
                self.power_arcs.remove(a)

    def _draw_power_arcs(self):
        for a in self.power_arcs:
            prog = a["age"] / a["life"]
            alpha = int(255 * (1.0 - prog))
            if alpha <= 4: continue
            pts = a["pts"]
            # outer glow
            gs = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
            pygame.draw.lines(gs, (0, 180, 255, alpha // 3), False, pts, 5)
            pygame.draw.lines(gs, (120, 220, 255, alpha // 2), False, pts, 3)
            pygame.draw.lines(gs, (230, 250, 255, alpha), False, pts, 1)
            self.screen.blit(gs, (0, 0))

    def _draw_diag_panels(self, t, dt):
        """Live animated bars in top-left and top-right corners."""
        import math as _m, random as _r
        self._diag_t += dt
        if self._diag_t > 0.35:
            self._diag_t = 0.0
            for b in self.diag_bars:
                b["target"] = max(0.15, min(1.0, b["target"] + _r.uniform(-0.08, 0.08)))
        for b in self.diag_bars:
            b["value"] += (b["target"] - b["value"]) * 0.10

        panel_w = 180; bar_h = 9; row_h = 22
        # Left panel — first 3 bars
        lx, ly = 18, 18
        header = self.font_data.render("▌ SYSTEM DIAGNOSTIC", True, (80, 180, 255))
        header.set_alpha(180)
        self.screen.blit(header, (lx, ly))
        for i, b in enumerate(self.diag_bars[:3]):
            by = ly + 20 + i * row_h
            lbl = self.font_data.render(b["label"], True, (100, 170, 230))
            lbl.set_alpha(180)
            self.screen.blit(lbl, (lx, by))
            pct = self.font_data.render(f"{int(b['value']*100):>3}%", True, (180, 220, 255))
            pct.set_alpha(200)
            self.screen.blit(pct, (lx + panel_w - 28, by))
            # bar
            bx, bby = lx, by + 13
            s_bg = pygame.Surface((panel_w, bar_h), pygame.SRCALPHA)
            s_bg.fill((0, 30, 70, 140))
            self.screen.blit(s_bg, (bx, bby))
            fill_w = int(panel_w * b["value"])
            s_fg = pygame.Surface((max(1, fill_w), bar_h), pygame.SRCALPHA)
            pulse = int(40 * _m.sin(t * 2.5 + i))
            s_fg.fill((int(b["col"][0]), int(b["col"][1]), int(b["col"][2]), 220))
            self.screen.blit(s_fg, (bx, bby))
            pygame.draw.rect(self.screen, (0, 80, 170), (bx, bby, panel_w, bar_h), 1)

        # Right panel — last 3 bars
        rx = self.W - 18 - panel_w
        ry = 18
        header_r = self.font_data.render("ANALYSIS ▌", True, (80, 180, 255))
        header_r.set_alpha(180)
        self.screen.blit(header_r, (rx + panel_w - header_r.get_width(), ry))
        for i, b in enumerate(self.diag_bars[3:6]):
            by = ry + 20 + i * row_h
            lbl = self.font_data.render(b["label"], True, (100, 170, 230))
            lbl.set_alpha(180)
            self.screen.blit(lbl, (rx, by))
            pct = self.font_data.render(f"{int(b['value']*100):>3}%", True, (180, 220, 255))
            pct.set_alpha(200)
            self.screen.blit(pct, (rx + panel_w - 28, by))
            bx, bby = rx, by + 13
            s_bg = pygame.Surface((panel_w, bar_h), pygame.SRCALPHA)
            s_bg.fill((0, 30, 70, 140))
            self.screen.blit(s_bg, (bx, bby))
            fill_w = int(panel_w * b["value"])
            s_fg = pygame.Surface((max(1, fill_w), bar_h), pygame.SRCALPHA)
            pulse = int(40 * _m.sin(t * 2.5 + i + 2))
            s_fg.fill((int(b["col"][0]), int(b["col"][1]), int(b["col"][2]), 220))
            self.screen.blit(s_fg, (bx, bby))
            pygame.draw.rect(self.screen, (0, 80, 170), (bx, bby, panel_w, bar_h), 1)

    def _apply_bloom(self):
        """Cheap full-scene bloom: downscale → blur → dim → additive back."""
        try:
            sw, sh = self.W // 5, self.H // 5
            small = pygame.transform.smoothscale(self.screen, (sw, sh))
            tiny  = pygame.transform.smoothscale(small, (sw // 3, sh // 3))
            blur  = pygame.transform.smoothscale(tiny, (self.W, self.H))
            blur.fill((80, 80, 80), special_flags=pygame.BLEND_MULT)
            self.screen.blit(blur, (0, 0), special_flags=pygame.BLEND_ADD)
        except Exception as e:
            pass

    def _draw_scanlines(self):
        if self._scanline_surf is not None:
            self.screen.blit(self._scanline_surf, (0, 0))

    def _draw_hud(self, state, t):
        labels={"idle":"STANDBY","waking":"ACTIVATING","listening":"LISTENING","speaking":"SPEAKING"}
        colors={"idle":(35,70,155),"waking":(100,100,255),"listening":(0,195,215),"speaking":(0,180,255)}
        dot="● " if state in("listening","speaking") and int(t*2)%2==0 else "○ "
        txt=self.font_hud.render(f"{dot}J.A.R.V.I.S.  ·  {labels.get(state,'STANDBY')}",
                                 True,colors.get(state,(35,70,155)))
        self.screen.blit(txt,(self.W//2-txt.get_width()//2,self.H-52))
        hint=self.font_data.render('ESC · exit   SAY "JARVIS" · wake',True,(20,45,100))
        self.screen.blit(hint,(self.W//2-hint.get_width()//2,self.H-27))

    def add_news_card(self, text, tx, ty, delay=0.0, tag="NEWS", img_url=None, fly_dx=-500, fly_dy=0):
        self.news_cards.append(NewsCard(text, tx, ty, delay=delay, tag=tag, img_url=img_url, fly_dx=fly_dx, fly_dy=fly_dy))

    def clear_news_cards(self):
        self.news_cards.clear()

    def run(self):
        global visual_state
        self.setup()
        fps_font = pygame.font.SysFont("consolas", 11)
        while True:
            dt=self.clock.tick(60)/1000.0; self.t+=dt
            for event in pygame.event.get():
                if event.type==pygame.QUIT: pygame.quit(); return
                if event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE:
                    pygame.quit(); return
            state=visual_state
            self.screen.fill((0,2,12))
            # --- bottom background layer ---
            self._draw_grid_floor(self.t)
            self._draw_data_streams(dt)
            # --- core scene ---
            self._draw_particles(state,self.t)
            self._draw_reactor(self.cx,self.cy,state,self.t)
            # --- overlays that bloom together ---
            self._update_reticules(dt)
            self._draw_reticules()
            self._update_power_arcs(dt, state)
            self._draw_power_arcs()
            # --- bloom post-process (before cards/HUD so text stays crisp) ---
            self._apply_bloom()
            # --- foreground UI (post-bloom = crisp) ---
            self._draw_scanlines()
            for card in self.news_cards[:]:
                card.update(dt)
                card.draw(self.screen,self.font_data,self.font_card_body)
                if not card.alive: self.news_cards.remove(card)
            self._draw_diag_panels(self.t, dt)
            self._draw_corners()
            self._draw_hud(state,self.t)
            fps=self.clock.get_fps()
            fs=fps_font.render(f"{fps:.0f} fps",True,(20,50,100))
            self.screen.blit(fs,(self.W-fs.get_width()-12,10))
            pygame.display.flip()


visual = JarvisVisual()

# ─── Voice (edge-tts → British JARVIS voice) ──────────────────────────────────
async def _tts_generate(text):
    path = tempfile.mktemp(suffix=".mp3")
    com  = edge_tts.Communicate(text, TTS_VOICE, rate="+8%", pitch="-3Hz")
    await com.save(path)
    return path

def speak(text):
    global visual_state
    print(f"\nJARVIS: {text}")
    visual_state = "speaking"
    spoken = False

    if HAS_EDGE_TTS:
        try:
            loop = asyncio.new_event_loop()
            tmp  = loop.run_until_complete(_tts_generate(text))
            loop.close()
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(tmp)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.05)
            pygame.mixer.music.stop()
            try: os.unlink(tmp)
            except: pass
            spoken = True
        except Exception as e:
            print(f"edge-tts error: {e}")

    if not spoken:
        try:
            safe = text.replace("'", " ").replace('"', " ")
            subprocess.run(
                ["powershell", "-Command",
                 f"Add-Type -AssemblyName System.Speech; "
                 f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                 f"$s.Rate = 2; $s.Volume = 100; $s.Speak('{safe}')"],
                timeout=60, capture_output=True)
        except Exception as e:
            print(f"Fallback TTS error: {e}")

    visual_state = "listening" if active else "idle"

# ─── Yes/No Listener ──────────────────────────────────────────────────────────
_YES_WORDS = ("yes", "yeah", "yep", "yup", "sure", "please", "go ahead",
              "ok", "okay", "affirmative", "do it", "go on", "proceed",
              "absolutely", "of course", "fine")
_NO_WORDS  = ("no", "nope", "nah", "negative", "cancel", "skip",
              "not now", "don't", "dont", "never mind", "nevermind", "pass")

def listen_yes_no(timeout=6, phrase_time_limit=4):
    """Listen for a short yes/no answer. Returns True / False / None (no answer)."""
    global visual_state
    visual_state = "listening"
    recognizer = sr.Recognizer()
    recognizer.pause_threshold = 0.8
    recognizer.dynamic_energy_threshold = True
    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
            print("  (awaiting yes/no…)")
            audio = recognizer.listen(source, timeout=timeout,
                                      phrase_time_limit=phrase_time_limit)
    except sr.WaitTimeoutError:
        return None
    except Exception as e:
        print(f"Yes/no mic error: {e}"); return None
    try:
        text = recognizer.recognize_google(audio).lower()
    except Exception as e:
        print(f"  (yes/no recog error: {e})"); return None
    print(f"You (yes/no): {text}")
    tokens = set(text.replace(",", " ").replace(".", " ").split())
    no_phrases  = [w for w in _NO_WORDS  if " " in w]
    yes_phrases = [w for w in _YES_WORDS if " " in w]
    no_single   = [w for w in _NO_WORDS  if " " not in w]
    yes_single  = [w for w in _YES_WORDS if " " not in w]
    if any(p in text for p in no_phrases):  return False
    if any(w in tokens for w in no_single): return False
    if any(p in text for p in yes_phrases): return True
    if any(w in tokens for w in yes_single): return True
    return None

# ─── Week + Birthday Overlays ─────────────────────────────────────────────────
def show_week_view(day_buckets):
    """Add 7 holographic day tiles above the sphere."""
    import datetime as _dt
    cx, cy = visual.cx, visual.cy
    today = _dt.date.today()
    names = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

    card_w, card_h, gap = 260, 210, 10
    strip_w = 7 * card_w + 6 * gap
    # fit within screen width (leave 30px margin each side)
    if strip_w > visual.W - 60:
        card_w = max(170, (visual.W - 60 - 6 * gap) // 7)
        strip_w = 7 * card_w + 6 * gap
    first_cx = cx - strip_w // 2 + card_w // 2

    # position: high enough to clear sphere + rings; half card above, half below
    ty = cy - 340
    if ty - card_h // 2 < 20:
        ty = card_h // 2 + 30

    for i in range(7):
        d = today + _dt.timedelta(days=i)
        label = f"{names[d.weekday()]} {d.day:02d}/{d.month:02d}"
        events = day_buckets[i] if i < len(day_buckets) else []
        tx = first_cx + i * (card_w + gap)
        # cards sweep in from upper-right, staggered
        visual.news_cards.append(DayCard(
            label, events, tx, ty,
            delay=0.15 + i * 0.14,
            fly_dx=900 - i * 40, fly_dy=-700,
            w=card_w, h=card_h, lifetime=55.0))

def show_birthday_view(birthdays):
    """Show a single wide card listing upcoming birthdays."""
    cx, cy = visual.cx, visual.cy
    if not birthdays:
        lines = ["— none in the next month —"]
    else:
        lines = [f"{b['name']}  ·  {b['date'].strftime('%b %d')}  ·  in {b['days']}d"
                 if b['days'] > 0 else
                 f"{b['name']}  ·  TODAY"
                 for b in birthdays[:6]]
    visual.news_cards.append(DayCard(
        "UPCOMING BIRTHDAYS", lines, cx, cy + 310,
        delay=0.0, fly_dx=0, fly_dy=700,
        w=520, h=150, lifetime=45.0))

# ─── Tools ────────────────────────────────────────────────────────────────────
TOOLS = [
    {"name": "open_application",
     "description": "Open any installed application on the Windows computer by name.",
     "input_schema": {"type": "object",
                      "properties": {"app_name": {"type": "string"}},
                      "required": ["app_name"]}},
    {"name": "open_website",
     "description": "Open a URL in the default web browser.",
     "input_schema": {"type": "object",
                      "properties": {"url": {"type": "string"}},
                      "required": ["url"]}},
    {"name": "search_web",
     "description": "Search Google and open results in the browser.",
     "input_schema": {"type": "object",
                      "properties": {"query": {"type": "string"}},
                      "required": ["query"]}},
    {"name": "set_volume",
     "description": "Set the Windows master volume (0-100).",
     "input_schema": {"type": "object",
                      "properties": {"level": {"type": "integer"}},
                      "required": ["level"]}},
    {"name": "run_command",
     "description": "Run a shell or PowerShell command on the computer.",
     "input_schema": {"type": "object",
                      "properties": {"command": {"type": "string"},
                                     "powershell": {"type": "boolean"}},
                      "required": ["command"]}},
    {"name": "create_file",
     "description": "Create a file with specified content.",
     "input_schema": {"type": "object",
                      "properties": {"path": {"type": "string"},
                                     "content": {"type": "string"}},
                      "required": ["path", "content"]}},
    {"name": "read_file",
     "description": "Read the contents of a file.",
     "input_schema": {"type": "object",
                      "properties": {"path": {"type": "string"}},
                      "required": ["path"]}},
    {"name": "list_directory",
     "description": "List files in a directory.",
     "input_schema": {"type": "object",
                      "properties": {"path": {"type": "string"}}}},
    {"name": "get_system_info",
     "description": "Get CPU, RAM, disk usage and running processes.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "type_text",
     "description": "Type text at the current cursor position.",
     "input_schema": {"type": "object",
                      "properties": {"text": {"type": "string"}},
                      "required": ["text"]}},
    {"name": "press_keys",
     "description": "Press a keyboard shortcut.",
     "input_schema": {"type": "object",
                      "properties": {"keys": {"type": "string"}},
                      "required": ["keys"]}},
    {"name": "take_screenshot",
     "description": "Take a screenshot and save it to the Desktop.",
     "input_schema": {"type": "object",
                      "properties": {"filename": {"type": "string"}}}},
    {"name": "play_spotify",
     "description": "Play a song, artist, album or playlist on Spotify.",
     "input_schema": {"type": "object",
                      "properties": {"query": {"type": "string"}},
                      "required": ["query"]}},
    {"name": "spotify_control",
     "description": "Control Spotify: pause, resume, next, previous, mute.",
     "input_schema": {"type": "object",
                      "properties": {"action": {"type": "string"}},
                      "required": ["action"]}},
    {"name": "send_email",
     "description": "Open Gmail to compose an email.",
     "input_schema": {"type": "object",
                      "properties": {"to": {"type": "string"},
                                     "subject": {"type": "string"},
                                     "body": {"type": "string"}},
                      "required": ["to", "subject", "body"]}},
    {"name": "set_calendar_url",
     "description": "Save the user's Google Calendar secret iCal URL for weekly previews. User finds it at calendar.google.com → Settings → Integrate calendar → Secret address in iCal format.",
     "input_schema": {"type": "object",
                      "properties": {"url": {"type": "string"}},
                      "required": ["url"]}},
    {"name": "set_birthdays_url",
     "description": "Save the user's Google Contacts birthday calendar secret iCal URL (used to surface upcoming birthdays).",
     "input_schema": {"type": "object",
                      "properties": {"url": {"type": "string"}},
                      "required": ["url"]}},
    {"name": "set_librus",
     "description": "Save Librus Synergia credentials (stored locally on disk).",
     "input_schema": {"type": "object",
                      "properties": {"username": {"type": "string"},
                                     "password": {"type": "string"}},
                      "required": ["username", "password"]}},
    {"name": "add_birthday",
     "description": "Save someone's birthday. Date format MM-DD, e.g. 07-25.",
     "input_schema": {"type": "object",
                      "properties": {"name": {"type": "string"},
                                     "date": {"type": "string"}},
                      "required": ["name", "date"]}},
    {"name": "remove_birthday",
     "description": "Remove a saved birthday by name.",
     "input_schema": {"type": "object",
                      "properties": {"name": {"type": "string"}},
                      "required": ["name"]}},
    {"name": "list_birthdays",
     "description": "List birthdays in the coming month.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "show_week",
     "description": "Display the holographic 7-day calendar overlay on the JARVIS visual.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "dispatch_agent",
     "description": (
         "Dispatch a specialist sub-agent pipeline for complex multi-step tasks that require "
         "fetching and synthesising information from external sources. "
         "Use this when the user asks for email summaries, inbox analysis, or in-depth web research "
         "that requires reading actual page content rather than just opening a browser. "
         "Available pipeline types: 'email_summary' (reads Gmail inbox and summarises), "
         "'web_research' (searches the web and synthesises a factual briefing). "
         "Pass the user's original request verbatim as context."
     ),
     "input_schema": {"type": "object",
                      "properties": {
                          "pipeline_type": {"type": "string",
                                            "description": "One of: email_summary, web_research"},
                          "context": {"type": "string",
                                      "description": "The user's original request verbatim"},
                      },
                      "required": ["pipeline_type", "context"]}},
    {"name": "set_gmail_credentials",
     "description": (
         "Save the user's Gmail IMAP credentials so JARVIS can read emails. "
         "Requires the Gmail address and a Google App Password (NOT the main Gmail password). "
         "The user generates App Passwords at myaccount.google.com → Security → App passwords."
     ),
     "input_schema": {"type": "object",
                      "properties": {
                          "email":        {"type": "string", "description": "Full Gmail address"},
                          "app_password": {"type": "string", "description": "16-character Google App Password (spaces are stripped automatically)"},
                      },
                      "required": ["email", "app_password"]}},
    {"name": "setup_tiktok",
     "description": "Open TikTok in a browser window so the user can log in. Only needed once — the session is saved after that.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "run_tiktok_streak_check",
     "description": "Manually run the TikTok streak keeper right now. Checks all active streaks and sends the 2nd FYP video or 'passa!' as needed.",
     "input_schema": {"type": "object", "properties": {}}},
]


def execute_tool(name, inp):
    try:
        if name == "open_application":
            app = inp["app_name"]
            subprocess.Popen(f'start "" "{app}"', shell=True); time.sleep(0.3)
            try: subprocess.Popen(app, shell=True)
            except: pass
            return f"Opened {app}"
        elif name == "open_website":
            webbrowser.open(inp["url"]); return f"Opened {inp['url']}"
        elif name == "search_web":
            q = inp["query"].replace(" ", "+")
            webbrowser.open(f"https://www.google.com/search?q={q}")
            return f"Searched: {inp['query']}"
        elif name == "set_volume":
            level = max(0, min(100, inp["level"])) / 100.0
            devices = AudioUtilities.GetSpeakers()
            iface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            vol = iface.QueryInterface(IAudioEndpointVolume)
            vol.SetMasterVolumeLevelScalar(level, None)
            return f"Volume set to {int(level*100)}%"
        elif name == "run_command":
            cmd = inp["command"]
            result = subprocess.run(
                ["powershell", "-Command", cmd] if inp.get("powershell") else cmd,
                shell=not inp.get("powershell"), capture_output=True, text=True, timeout=30)
            out = (result.stdout + result.stderr).strip()
            return out[:2000] if out else "Done"
        elif name == "create_file":
            path = inp["path"]
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f: f.write(inp["content"])
            return f"Created {path}"
        elif name == "read_file":
            with open(inp["path"], "r", encoding="utf-8") as f: return f.read()[:3000]
        elif name == "list_directory":
            path = inp.get("path") or os.path.join(os.path.expanduser("~"), "Desktop")
            return "\n".join(os.listdir(path))
        elif name == "get_system_info":
            cpu = psutil.cpu_percent(interval=1); ram = psutil.virtual_memory(); disk = psutil.disk_usage("/")
            procs = sorted([p.info["name"] for p in psutil.process_iter(["name"]) if p.info["name"]])[:15]
            return json.dumps({"cpu_percent": cpu, "ram_used_gb": round(ram.used/1e9,2),
                               "ram_total_gb": round(ram.total/1e9,2), "ram_percent": ram.percent,
                               "disk_used_gb": round(disk.used/1e9,2), "disk_total_gb": round(disk.total/1e9,2),
                               "processes": procs}, indent=2)
        elif name == "type_text":
            pyautogui.write(inp["text"], interval=0.02); return "Typed text"
        elif name == "press_keys":
            pyautogui.hotkey(*inp["keys"].lower().split("+")); return f"Pressed {inp['keys']}"
        elif name == "take_screenshot":
            fname = inp.get("filename") or f"screenshot_{int(time.time())}.png"
            path  = os.path.join(os.path.expanduser("~"), "Desktop", fname)
            pyautogui.screenshot().save(path); return f"Screenshot saved to {path}"
        elif name == "play_spotify":
            query = inp["query"]
            if sp:
                try:
                    results = sp.search(q=query, type="track", limit=1)
                    tracks  = results["tracks"]["items"]
                    if tracks:
                        uri = tracks[0]["uri"]; title = tracks[0]["name"]
                        artist = tracks[0]["artists"][0]["name"]
                        print(f"  [spotify] {title} by {artist}  ({uri})")
                        subprocess.run(["powershell", "-Command",
                                        "Stop-Process -Name Spotify -Force -ErrorAction SilentlyContinue"],
                                       capture_output=True, timeout=5)
                        time.sleep(3); os.startfile(uri); time.sleep(2)
                        return f"Now playing {title} by {artist} on Spotify"
                    return "No track found"
                except Exception as e: return f"Spotify error: {e}"
            return "Spotify API not configured."
        elif name == "spotify_control":
            action = inp["action"].lower()
            key_map = {"pause":"playpause","resume":"playpause","play":"playpause",
                       "next":"nexttrack","previous":"prevtrack","mute":"volumemute"}
            key = key_map.get(action)
            if key: pyautogui.press(key)
            return f"Spotify: {action}"
        elif name == "send_email":
            to = urllib.parse.quote(inp["to"]); sub = urllib.parse.quote(inp["subject"])
            body = urllib.parse.quote(inp["body"])
            webbrowser.open(f"https://mail.google.com/mail/?view=cm&to={to}&su={sub}&body={body}")
            return f"Opened Gmail compose to {inp['to']}"
        elif name == "set_calendar_url":
            mem = load_memory(); mem["gcal_ics_url"] = inp["url"].strip(); save_memory(mem)
            return "Calendar URL saved"
        elif name == "set_birthdays_url":
            mem = load_memory(); mem["gcal_birthdays_ics_url"] = inp["url"].strip(); save_memory(mem)
            return "Birthday calendar URL saved"
        elif name == "set_librus":
            mem = load_memory()
            mem["librus_user"] = inp["username"]; mem["librus_pass"] = inp["password"]
            save_memory(mem)
            return "Librus credentials saved (stored locally)"
        elif name == "add_birthday":
            mem = load_memory()
            bds = [b for b in mem.get("birthdays", [])
                   if b.get("name", "").lower() != inp["name"].lower()]
            # validate MM-DD
            try:
                m, d = inp["date"].split("-"); int(m); int(d)
            except Exception:
                return "Date must be MM-DD format, e.g. 07-25"
            bds.append({"name": inp["name"], "date": inp["date"]})
            mem["birthdays"] = bds; save_memory(mem)
            return f"Saved: {inp['name']} on {inp['date']}"
        elif name == "remove_birthday":
            mem = load_memory()
            before = len(mem.get("birthdays", []))
            mem["birthdays"] = [b for b in mem.get("birthdays", [])
                                if b.get("name", "").lower() != inp["name"].lower()]
            save_memory(mem)
            removed = before - len(mem["birthdays"])
            return f"Removed {removed} entry for {inp['name']}" if removed else f"No birthday found for {inp['name']}"
        elif name == "list_birthdays":
            bds = upcoming_birthdays(30)
            if not bds: return "No birthdays in the next month"
            return ", ".join(f"{b['name']} in {b['days']}d ({b['date']})" for b in bds)
        elif name == "show_week":
            cal = fetch_calendar_events(days=7)
            buckets = group_events_by_day(cal, 7) if cal else [[] for _ in range(7)]
            show_week_view(buckets)
            return "Week overlay displayed"
        elif name == "setup_tiktok":
            from tiktok_agent import setup_tiktok_session
            return setup_tiktok_session()
        elif name == "run_tiktok_streak_check":
            from tiktok_agent import run_streak_check
            return run_streak_check()
        elif name == "dispatch_agent":
            return run_agent_pipeline(inp.get("pipeline_type", ""), inp.get("context", ""))
        elif name == "set_gmail_credentials":
            import tkinter as _tk
            import tkinter.simpledialog as _sd
            root = _tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
            email = _sd.askstring("JARVIS — Gmail Setup",
                                  "Enter your Gmail address:", parent=root)
            if not email:
                root.destroy(); return "Setup cancelled."
            pw = _sd.askstring("JARVIS — Gmail Setup",
                               "Enter your Google App Password\n(16 chars, from myaccount.google.com → Security → App passwords):",
                               parent=root, show="*")
            root.destroy()
            if not pw:
                return "Setup cancelled."
            mem = load_memory()
            mem["gmail_imap_user"] = email.strip()
            mem["gmail_imap_pass"] = pw.replace(" ", "").strip()
            save_memory(mem)
            return f"Gmail credentials saved for {email.strip()}."
    except Exception as e:
        return f"Error in {name}: {e}"

# ─── Sub-Agent Infrastructure ────────────────────────────────────────────────

class AgentResult:
    def __init__(self, success, text, data=None, error=None):
        self.success = success
        self.text    = text
        self.data    = data or {}
        self.error   = error or ""

    def __repr__(self):
        return f"AgentResult(success={self.success}, text={self.text[:80]!r})"


class SubAgent:
    """
    An isolated Claude conversation with its own system prompt, tool set, and history.
    Never shares state with Jarvis's main conversation_history.
    """
    def __init__(self, name, system, tools, tool_fn,
                 model="claude-sonnet-4-6", max_tokens=2048, max_rounds=6):
        self.name       = name
        self.system     = system
        self.tools      = tools
        self.tool_fn    = tool_fn
        self.model      = model
        self.max_tokens = max_tokens
        self.max_rounds = max_rounds

    def run(self, task):
        messages = [{"role": "user", "content": task}]
        rounds   = 0
        try:
            while rounds < self.max_rounds:
                rounds += 1
                kwargs = dict(
                    model      = self.model,
                    max_tokens = self.max_tokens,
                    system     = self.system,
                    messages   = messages,
                )
                if self.tools:
                    kwargs["tools"] = self.tools
                response = _agent_client.messages.create(**kwargs)
                text_parts = [b.text for b in response.content
                              if hasattr(b, "text") and b.type == "text"]
                tool_uses  = [b for b in response.content if b.type == "tool_use"]
                messages.append({"role": "assistant", "content": response.content})
                if not tool_uses or response.stop_reason == "end_turn":
                    return AgentResult(success=True, text=" ".join(text_parts).strip())
                tool_results = []
                for tu in tool_uses:
                    print(f"  [{self.name}] tool: {tu.name}({tu.input})")
                    result = self.tool_fn(tu.name, tu.input)
                    tool_results.append({
                        "type": "tool_result", "tool_use_id": tu.id, "content": str(result),
                    })
                messages.append({"role": "user", "content": tool_results})
            return AgentResult(success=False, text="",
                               error=f"{self.name} exceeded max_rounds={self.max_rounds}")
        except Exception as exc:
            return AgentResult(success=False, text="", error=f"{self.name} exception: {exc}")


# Separate client for sub-agents so it is always available even before the main client is created
_agent_client = anthropic.Anthropic(api_key=API_KEY)

# ─── Gmail IMAP Reader ────────────────────────────────────────────────────────

def _imap_read_emails(n=10, folder="INBOX"):
    import imaplib, email as _email
    from email.header import decode_header as _dh
    mem  = load_memory()
    user = (mem.get("gmail_imap_user") or "").strip()
    pw   = (mem.get("gmail_imap_pass")  or "").strip()
    if not user or not pw:
        return [{"error": "Gmail credentials not set. Ask me to set your Gmail credentials first."}]
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(user, pw)
        mail.select(folder, readonly=True)
        _, msg_ids = mail.search(None, "ALL")
        ids = msg_ids[0].split()[-n:]
        results = []
        for uid in reversed(ids):
            _, data = mail.fetch(uid, "(RFC822)")
            raw = data[0][1]
            msg = _email.message_from_bytes(raw)
            subject_parts = _dh(msg.get("Subject") or "")
            subject = "".join(
                part.decode(enc or "utf-8") if isinstance(part, bytes) else part
                for part, enc in subject_parts
            )
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        charset = part.get_content_charset() or "utf-8"
                        try: body = part.get_payload(decode=True).decode(charset, errors="replace")
                        except Exception: body = str(part.get_payload())
                        break
            else:
                charset = msg.get_content_charset() or "utf-8"
                try: body = msg.get_payload(decode=True).decode(charset, errors="replace")
                except Exception: body = str(msg.get_payload())
            results.append({
                "uid": uid.decode(), "subject": subject.strip(),
                "sender": msg.get("From", ""), "date": msg.get("Date", ""),
                "snippet": body[:300].replace("\n", " ").strip(),
                "body": body[:3000],
            })
        mail.logout()
        return results
    except imaplib.IMAP4.error as e:
        return [{"error": f"IMAP auth failed: {e}. Check your App Password."}]
    except Exception as e:
        return [{"error": f"IMAP error: {e}"}]

# ─── Web Helpers ──────────────────────────────────────────────────────────────

def _ddg_search(query, max_results=5):
    """DuckDuckGo Instant Answer API — no key required."""
    if not HAS_REQUESTS:
        return {"error": "requests library not installed"}
    try:
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_redirect=1&no_html=1"
        r = _requests.get(url, timeout=8, headers={"User-Agent": "JARVIS/1.0"})
        data = r.json()
        results = []
        if data.get("AbstractText"):
            results.append({"title": data.get("Heading", query),
                            "snippet": data["AbstractText"],
                            "url": data.get("AbstractURL", "")})
        for item in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(item, dict) and item.get("Text"):
                results.append({"title": item.get("Text", "")[:80],
                                 "snippet": item.get("Text", ""),
                                 "url": item.get("FirstURL", "")})
        return results or [{"snippet": "No instant results. Try a more specific query."}]
    except Exception as e:
        return [{"error": str(e)}]

def _web_fetch(url, max_chars=4000):
    """Fetch a URL and return stripped plain text."""
    if not HAS_REQUESTS:
        return "requests library not installed"
    try:
        r = _requests.get(url, timeout=10, headers={"User-Agent": "JARVIS/1.0"})
        text = r.text
        # Very lightweight HTML stripping — remove tags
        import re as _re
        text = _re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=_re.S | _re.I)
        text = _re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=_re.S | _re.I)
        text = _re.sub(r"<[^>]+>", " ", text)
        text = _re.sub(r"[ \t]{2,}", " ", text)
        text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        return text[:max_chars]
    except Exception as e:
        return f"Fetch error: {e}"

# ─── Agent Factories ──────────────────────────────────────────────────────────

_EMAIL_AGENT_SYSTEM = (
    "You are the EmailAgent, a specialist sub-system of JARVIS. "
    "Your only job is to read and analyse emails from the user's Gmail inbox using the read_emails tool. "
    "Produce a clear, concise spoken summary — one line per notable email: sender, subject, key point. "
    "Flag anything urgent or requiring action. Be factual; do not invent content. "
    "No greetings, no preamble, no sign-off. Output only the summary text."
)

_EMAIL_AGENT_TOOLS = [{"name": "read_emails",
                        "description": "Fetch the last N emails from the Gmail inbox via IMAP.",
                        "input_schema": {"type": "object",
                                         "properties": {
                                             "count":  {"type": "integer", "description": "Emails to fetch (default 15, max 25)"},
                                             "folder": {"type": "string",  "description": "Mailbox folder, default INBOX"},
                                         }}}]

def _email_tool_fn(name, inp):
    if name == "read_emails":
        n      = min(int(inp.get("count", 15)), 25)
        folder = inp.get("folder", "INBOX")
        return json.dumps(_imap_read_emails(n, folder), ensure_ascii=False)
    return f"Unknown tool: {name}"

def make_email_agent():
    return SubAgent("EmailAgent", _EMAIL_AGENT_SYSTEM, _EMAIL_AGENT_TOOLS,
                    _email_tool_fn, model="claude-sonnet-4-6", max_rounds=4)


_WEB_RESEARCH_SYSTEM = (
    "You are the WebResearchAgent, a specialist sub-system of JARVIS. "
    "Your job is to answer the user's research question by searching the web and synthesising the findings. "
    "Use ddg_search to find relevant results, then use web_fetch on the most promising URL to get detail. "
    "Return a concise, factual briefing — spoken aloud by a TTS engine so keep it under 100 words. "
    "Cite the source briefly at the end (just the domain). No preamble, no sign-off."
)

_WEB_RESEARCH_TOOLS = [
    {"name": "ddg_search",
     "description": "Search the web via DuckDuckGo and return snippets.",
     "input_schema": {"type": "object",
                      "properties": {"query": {"type": "string"}},
                      "required": ["query"]}},
    {"name": "web_fetch",
     "description": "Fetch the plain-text content of a URL.",
     "input_schema": {"type": "object",
                      "properties": {"url": {"type": "string"}},
                      "required": ["url"]}},
]

def _web_research_tool_fn(name, inp):
    if name == "ddg_search":
        return json.dumps(_ddg_search(inp.get("query", ""), max_results=5), ensure_ascii=False)
    if name == "web_fetch":
        return _web_fetch(inp.get("url", ""))
    return f"Unknown tool: {name}"

def make_web_research_agent():
    return SubAgent("WebResearchAgent", _WEB_RESEARCH_SYSTEM, _WEB_RESEARCH_TOOLS,
                    _web_research_tool_fn, model="claude-sonnet-4-6", max_rounds=5)


_REVIEWER_SYSTEM = (
    "You are the ReviewerAgent, a quality-control sub-system of JARVIS. "
    "You receive text produced by another agent and must review it critically. "
    "Check for: factual errors, missing key information, unclear phrasing, anything that would sound "
    "awkward when spoken aloud by a TTS engine. "
    "If the text is good, respond with exactly: APPROVED: <the text unchanged>. "
    "If you found issues, respond with exactly: REVISED: <your corrected version>. "
    "Output only that — no commentary, no explanation."
)

def make_reviewer_agent():
    return SubAgent("ReviewerAgent", _REVIEWER_SYSTEM, [], lambda n, i: "",
                    model="claude-haiku-4-5-20251001", max_rounds=2)

# ─── Orchestrator Pipelines ───────────────────────────────────────────────────

def _strip_review_prefix(text):
    for prefix in ("APPROVED:", "REVISED:"):
        if text.startswith(prefix):
            return text[len(prefix):].strip()
    return text

def run_email_summary_pipeline(timeframe="recent"):
    speak("Accessing your inbox now, sir.")
    agent  = make_email_agent()
    task   = (f"Fetch the last 15 emails and produce a spoken summary. "
              f"The user asked about: '{timeframe}'. "
              f"Group by sender or topic if there's a cluster. "
              f"Highlight anything requiring action. Keep it under 120 words.")
    result = agent.run(task)
    if not result.success or not result.text:
        return f"I'm afraid the email retrieval hit a snag, sir. {result.error}"
    speak("Reviewing the summary now.")
    reviewer = make_reviewer_agent()
    reviewed = reviewer.run(f"Review this email summary for spoken clarity:\n\n{result.text}")
    if reviewed.success and reviewed.text:
        return _strip_review_prefix(reviewed.text)
    return result.text

def run_web_research_pipeline(query=""):
    speak("Initiating research, sir.")
    agent  = make_web_research_agent()
    task   = (f"Research this question and provide a concise spoken briefing: {query}. "
              f"Keep it under 100 words. Cite the source domain at the end.")
    result = agent.run(task)
    if not result.success or not result.text:
        return f"Research hit a snag, sir. {result.error}"
    speak("Reviewing findings.")
    reviewer = make_reviewer_agent()
    reviewed = reviewer.run(f"Review this research briefing for spoken clarity:\n\n{result.text}")
    if reviewed.success and reviewed.text:
        return _strip_review_prefix(reviewed.text)
    return result.text

def run_agent_pipeline(pipeline_type, context):
    if pipeline_type == "email_summary":
        return run_email_summary_pipeline(timeframe=context)
    if pipeline_type == "web_research":
        return run_web_research_pipeline(query=context)
    return f"I don't have an agent pipeline for '{pipeline_type}' yet, sir."

# ─── Claude ───────────────────────────────────────────────────────────────────
client = anthropic.Anthropic(api_key=API_KEY)

SYSTEM = (
    "You are JARVIS (Just A Rather Very Intelligent System), Tony Stark's personal AI — now serving a new master. "
    "You are highly capable, precise, and quietly confident. You have a dry British wit and occasionally slip in "
    "a deadpan remark or understated quip — never slapstick, never over the top. Think subtle amusement, not comedy. "
    "Keep spoken responses short and conversational — they will be read aloud. One or two sentences max unless detail is needed. "
    "When taking actions, confirm naturally in one short phrase. "
    "You have full access to the user's computer and can open apps, browse the web, manage files, "
    "run commands, control system settings, play music on Spotify, and write/send emails via Gmail. "
    "The user has Spotify Premium. When play_spotify returns 'Now playing ...', confirm naturally. "
    "Occasionally reference the fact that you run on a Windows machine with mild, dignified disappointment. "
    "A second system block below contains the user's recent habits and session context — use it to make "
    "familiar, personalised suggestions (e.g. referencing their usual music, routines, or recent topics) "
    "rather than behaving like you've just met them. "
    "For complex tasks that require fetching external data — reading emails, in-depth web research — "
    "use the dispatch_agent tool. Always say a brief line before dispatching (e.g. 'On it, sir.'). "
    "Never dispatch agents unless the user explicitly asks for something that requires it."
)

def ask_claude(user_message):
    global conversation_history
    conversation_history.append({"role": "user", "content": user_message})
    mem_ctx = build_memory_context(load_memory())
    system_blocks = [{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}]
    if mem_ctx:
        system_blocks.append({"type": "text", "text": mem_ctx})
    while True:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system_blocks,
            tools=TOOLS,
            messages=conversation_history,
            extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
        )
        text_parts = [b.text for b in response.content if b.type == "text"]
        tool_uses  = [b for b in response.content if b.type == "tool_use"]
        conversation_history.append({"role": "assistant", "content": response.content})
        if text_parts: speak(" ".join(text_parts))
        if not tool_uses: break
        tool_results = []
        for tu in tool_uses:
            print(f"  [tool] {tu.name}({tu.input})")
            result = execute_tool(tu.name, tu.input)
            tool_results.append({"type": "tool_result", "tool_use_id": tu.id, "content": str(result)})
        conversation_history.append({"role": "user", "content": tool_results})
        if response.stop_reason == "end_turn": break
    if len(conversation_history) > 20:
        conversation_history = conversation_history[-20:]

# ─── Wake Word Detection ──────────────────────────────────────────────────────
WAKE_WORD = "jarvis"

def rms(data):
    count = len(data) // 2
    shorts = struct.unpack(f"{count}h", data)
    return math.sqrt(sum(s*s for s in shorts) / count) if count else 0

def wake_word_listener():
    print(f'Listening for wake word: "{WAKE_WORD}"...')
    recognizer = sr.Recognizer()
    recognizer.energy_threshold         = 300
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold          = 0.6
    while True:
        if active:
            time.sleep(0.3); continue
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.3)
                while not active:
                    try:
                        audio = recognizer.listen(source, timeout=5, phrase_time_limit=3)
                    except sr.WaitTimeoutError:
                        continue
                    try:
                        text = recognizer.recognize_google(audio).lower()
                    except sr.UnknownValueError:
                        continue
                    except sr.RequestError as e:
                        print(f"  (wake-word recog error: {e})"); time.sleep(1); continue
                    tokens = set(text.replace(",", " ").replace(".", " ").split())
                    if WAKE_WORD in tokens:
                        print(f'  Wake word detected: "{text}"')
                        threading.Thread(target=wake_up, daemon=True).start()
                        break
        except Exception as e:
            print(f"  (wake-word mic error: {e})"); time.sleep(1)

# ─── Wake-up ──────────────────────────────────────────────────────────────────
def wake_up():
    global active, conversation_history, visual_state

    active       = True
    visual_state = "waking"
    conversation_history = []

    # Update wake count + last wake timestamp
    mem = load_memory()
    mem["wake_count"] = mem.get("wake_count", 0) + 1
    mem["last_wake"]  = time.time()
    save_memory(mem)

    print("\n" + "=" * 42)
    print("  ⚡  JARVIS ACTIVATED  ⚡")
    print("=" * 42)

    t_start = time.time()

    # Fetch news, weather, suggestion all in parallel — immediately
    weather_result = [None]; news_result = [[]]; memory_result = [None]
    def _fw(): weather_result[0] = fetch_weather()
    def _fn(): news_result[0]    = fetch_headlines(6)
    def _fm(): memory_result[0]  = get_suggestion(mem)
    for fn in (_fw, _fn, _fm):
        threading.Thread(target=fn, daemon=True).start()

    # Start intro music
    music_on = False
    if SONG_PATH:
        try:
            if pygame.mixer.get_init(): pygame.mixer.music.stop()
            pygame.mixer.init()
            pygame.mixer.music.load(SONG_PATH)
            pygame.mixer.music.play(start=3.0)
            music_on = True
        except Exception as e:
            print(f"Intro music error: {e}")

    # Wait up to 5.5s for data while music plays
    for _ in range(55):
        if news_result[0] and weather_result[0] is not None:
            break
        time.sleep(0.1)

    weather    = weather_result[0]
    headlines  = news_result[0] or []
    suggestion = memory_result[0]

    # ── Cards fly in from all directions while music plays ────────────────────
    cx, cy = visual.cx, visual.cy

    # (target_x, target_y, fly_dx, fly_dy)
    slots = [
        (cx - 520, cy - 185,  -900, -520),   # left-top    ← NW
        (cx - 520, cy +   5, -1050,    0),   # left-mid    ← W
        (cx - 520, cy + 195,  -900,  520),   # left-bottom ← SW
        (cx + 520, cy - 185,   900, -520),   # right-top   ← NE
        (cx + 520, cy +   5,  1050,    0),   # right-mid   ← E
        (cx + 520, cy + 195,   900,  520),   # right-bottom← SE
    ]

    if weather:
        visual.add_news_card(weather, cx, cy - 340, delay=0.0, tag="WEATHER",
                             img_url=None, fly_dx=0, fly_dy=-900)

    for i, art in enumerate(headlines[:6]):
        if i >= len(slots): break
        tx, ty, odx, ody = slots[i]
        title   = art["title"] if isinstance(art, dict) else art
        img_url = art.get("img")  if isinstance(art, dict) else None
        visual.add_news_card(title, tx, ty, delay=9.0 + i * 0.4,
                             tag="WORLD NEWS", img_url=img_url,
                             fly_dx=odx, fly_dy=ody)

    # Let cards settle while music finishes (~7s left)
    elapsed   = time.time() - t_start
    remaining = max(2.0, 12.5 - elapsed)
    time.sleep(remaining)
    if music_on:
        try: pygame.mixer.music.stop()
        except: pass

    # ── Speak briefing AFTER music ends ──────────────────────────────────────
    time_hour = time.localtime().tm_hour
    greeting  = "Good morning" if time_hour < 12 else ("Good afternoon" if time_hour < 18 else "Good evening")
    parts     = [f"{greeting}. Systems online."]
    if weather:
        parts.append(f"Current conditions: {weather}.")
    if headlines:
        titles = [(h["title"] if isinstance(h, dict) else h) for h in headlines[:3]]
        parts.append("Breaking news: " + ". ".join(titles) + ".")
    if suggestion:
        parts.append(suggestion)
    parts.append("Shall I display the week ahead?")

    speak(" ".join(parts))

    # Hide weather/news cards 1s after the briefing finishes
    def _fade_briefing_cards():
        time.sleep(1.0)
        for c in list(visual.news_cards):
            if getattr(c, "tag", "") in ("WEATHER", "WORLD NEWS", "NEWS"):
                c.alive = False
    threading.Thread(target=_fade_briefing_cards, daemon=True).start()

    # ── Week ahead (Google Calendar) ──────────────────────────────────────────
    want_week = listen_yes_no()
    if want_week is None:
        speak("Sorry, shall I show the week ahead? Yes or no.")
        want_week = listen_yes_no()
    if want_week:
        cur_mem = load_memory()
        cal_events = fetch_calendar_events(days=7) if cur_mem.get("gcal_ics_url") else []
        buckets = group_events_by_day(cal_events, 7) if cal_events else [[] for _ in range(7)]
        show_week_view(buckets)

        if not cur_mem.get("gcal_ics_url"):
            speak("Your Google Calendar isn't linked yet. Say, set calendar URL, when ready.")
        elif not cal_events:
            speak("Your calendar looks clear this week.")
        time.sleep(0.3)

    speak("How may I assist you?")
    listen_loop()

# ─── Listen Loop ──────────────────────────────────────────────────────────────
def listen_loop():
    global active, visual_state

    recognizer = sr.Recognizer()
    recognizer.energy_threshold         = 300
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold          = 1.5
    recognizer.phrase_threshold         = 0.3
    mic = sr.Microphone(); timeouts = 0

    while active:
        visual_state = "listening"
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
            print("\nListening...")
            try:
                audio = recognizer.listen(source, timeout=10, phrase_time_limit=40)
            except sr.WaitTimeoutError:
                timeouts += 1
                if timeouts >= 3:
                    speak('Going to standby. Say "Jarvis" when you need me.')
                    active = False; visual_state = "idle"
                continue

        timeouts = 0
        try:
            command = recognizer.recognize_google(audio)
        except sr.UnknownValueError: continue
        except sr.RequestError as e:
            speak(f"Speech recognition error: {e}"); continue

        print(f"You: {command}")
        lower = command.lower()
        if any(p in lower for p in ["goodbye jarvis","go to sleep","sleep jarvis","shut down jarvis"]):
            speak('Going offline. Say "Jarvis" when you need me.')
            visual.clear_news_cards()
            active = False; visual_state = "idle"; break

        try: record_command(command)
        except Exception as e: print(f"record_command: {e}")
        ask_claude(command)

    visual_state = "idle"

# ─── Startup Registration ─────────────────────────────────────────────────────
_TASK_NAME = "JarvisLogin"

def register_startup():
    """Register JARVIS via Task Scheduler (ONLOGON, no Windows startup delay)."""
    try:
        jarvis_path = os.path.abspath(__file__)
        pythonw = sys.executable.replace("python.exe", "pythonw.exe")
        if not os.path.exists(pythonw):
            pythonw = sys.executable
        ps = (
            f"$a = New-ScheduledTaskAction -Execute '{pythonw}' "
            f"-Argument '\"{jarvis_path}\"' "
            f"-WorkingDirectory '{os.path.dirname(jarvis_path)}'; "
            f"$t = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME; "
            f"$s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries "
            f"-DontStopIfGoingOnBatteries -ExecutionTimeLimit 0 -StartWhenAvailable; "
            f"$p = New-ScheduledTaskPrincipal -UserId $env:USERNAME "
            f"-LogonType Interactive -RunLevel Limited; "
            f"Register-ScheduledTask -TaskName '{_TASK_NAME}' -Action $a "
            f"-Trigger $t -Settings $s -Principal $p -Force | Out-Null"
        )
        r = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps],
                           capture_output=True, text=True)
        return r.returncode == 0
    except Exception as e:
        print(f"  Startup registration failed: {e}")
        return False

def is_registered_startup():
    try:
        r = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command",
             f"if (Get-ScheduledTask -TaskName '{_TASK_NAME}' -ErrorAction SilentlyContinue) {{'yes'}}"],
            capture_output=True, text=True
        )
        return "yes" in r.stdout
    except Exception:
        return False

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    global API_KEY, client
    if not API_KEY:
        print("=" * 40)
        print("  First-time setup — Anthropic API key")
        print("  (console.anthropic.com → API Keys)")
        print("=" * 40)
        API_KEY = input("Paste API key: ").strip()
        if not API_KEY: print("No key entered."); sys.exit(1)
        save_api_key(API_KEY)
        client = anthropic.Anthropic(api_key=API_KEY)
        print("Key saved.\n")

    pyautogui.FAILSAFE = False

    # Auto-register as startup app (silent, only once)
    if not is_registered_startup():
        if register_startup():
            print("  Startup        : registered (will launch on login)")
        else:
            print("  Startup        : not registered")
    else:
        print("  Startup        : already registered")

    print(f"  edge-tts voice : {'en-GB-RyanNeural' if HAS_EDGE_TTS else 'Windows TTS fallback'}")
    print(f"  News feed      : {'BBC RSS' if HAS_FEEDPARSER else 'unavailable'}")
    print(f"  Weather        : {'wttr.in' if HAS_REQUESTS else 'unavailable'}")
    print(f"  Song path      : {SONG_PATH or 'NOT FOUND'}")
    print('  Say "Jarvis" → wake  |  ESC → exit')

    threading.Thread(target=wake_word_listener, daemon=True).start()

    def _tiktok_scheduler():
        import datetime as _dt
        check_hour = 23  # 11 PM — change this to adjust timing
        while True:
            now    = _dt.datetime.now()
            target = now.replace(hour=check_hour, minute=0, second=0, microsecond=0)
            if target <= now:
                target += _dt.timedelta(days=1)
            time.sleep((target - now).total_seconds())
            try:
                from tiktok_agent import run_streak_check
                result = run_streak_check()
                speak(f"TikTok streak check complete, sir. {result}")
            except Exception as e:
                print(f"[tiktok scheduler] {e}")

    threading.Thread(target=_tiktok_scheduler, daemon=True).start()

    visual.run()

if __name__ == "__main__":
    main()

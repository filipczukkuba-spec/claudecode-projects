#!/usr/bin/env python3
"""J.A.R.V.I.S. - Just A Rather Very Intelligent System"""

import os, sys, time, math, random, struct, threading, subprocess, webbrowser, json, asyncio, tempfile

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

def fetch_headlines(count=5):
    if not HAS_FEEDPARSER: return []
    try:
        feed = feedparser.parse("https://feeds.bbci.co.uk/news/world/rss.xml")
        return [e.title for e in feed.entries[:count]]
    except Exception: return []

# ─── Floating News Cards ──────────────────────────────────────────────────────
class NewsCard:
    def __init__(self, text, target_x, target_y, delay=0.0, tag="NEWS"):
        self.text     = text
        self.tag      = tag
        self.tx, self.ty = target_x, target_y
        self.x = target_x
        self.y = target_y + 60
        self.alpha    = 0.0
        self.phase    = random.uniform(0, math.tau)
        self.delay    = delay
        self.age      = 0.0
        self.alive    = True
        self.lifetime = 28.0

    def update(self, dt):
        self.age += dt
        if self.age < self.delay: return
        a = self.age - self.delay
        if a < 1.2:
            self.alpha = min(1.0, a / 1.2)
            self.y += (self.ty - self.y) * 0.12
        elif a > self.lifetime - 1.5:
            self.alpha = max(0.0, 1.0 - (a - (self.lifetime - 1.5)) / 1.5)
        else:
            self.y = self.ty + 6 * math.sin(self.phase + a * 1.1)
        if self.age > self.lifetime + self.delay:
            self.alive = False

    def draw(self, screen, font_title, font_body):
        if self.alpha <= 0: return
        a = int(self.alpha * 255)
        W, H = 360, 75
        x, y = int(self.x) - W // 2, int(self.y) - H // 2

        # Panel background
        panel = pygame.Surface((W, H), pygame.SRCALPHA)
        panel.fill((0, 8, 30, int(a * 0.82)))
        screen.blit(panel, (x, y))

        # Glowing border
        border_surf = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.rect(border_surf, (0, 160, 255, a), (0, 0, W, H), 1)
        pygame.draw.rect(border_surf, (0, 100, 200, int(a * 0.4)), (1, 1, W-2, H-2), 1)
        screen.blit(border_surf, (x, y))

        # Tag strip (top-left corner)
        tag_surf = pygame.Surface((65, 16), pygame.SRCALPHA)
        tag_surf.fill((0, 120, 220, int(a * 0.9)))
        screen.blit(tag_surf, (x + 8, y + 8))
        tag_txt = font_body.render(self.tag, True, (200, 230, 255, a))
        screen.blit(tag_txt, (x + 12, y + 9))

        # Headline text (word-wrap simple)
        words = self.text.split()
        lines, line = [], ""
        for w in words:
            test = (line + " " + w).strip()
            if font_body.size(test)[0] < W - 20:
                line = test
            else:
                lines.append(line); line = w
        lines.append(line)
        for i, ln in enumerate(lines[:2]):
            col = (220, 235, 255) if i == 0 else (160, 185, 220)
            t = font_body.render(ln, True, col)
            t.set_alpha(a)
            screen.blit(t, (x + 10, y + 30 + i * 18))

        # Corner tick marks
        tc = (0, 160, 255, a)
        for cx2, cy2 in [(x, y), (x+W, y), (x, y+H), (x+W, y+H)]:
            sx = 1 if cx2 == x else -1
            sy = 1 if cy2 == y else -1
            cs = pygame.Surface((14, 14), pygame.SRCALPHA)
            pygame.draw.line(cs, tc, (0 if sx>0 else 13, 0 if sy>0 else 13),
                             (8 if sx>0 else 5, 0 if sy>0 else 13), 1)
            pygame.draw.line(cs, tc, (0 if sx>0 else 13, 0 if sy>0 else 13),
                             (0 if sx>0 else 13, 8 if sy>0 else 5), 1)
            screen.blit(cs, (cx2 - (0 if sx>0 else 14), cy2 - (0 if sy>0 else 14)))


# ─── Visual Engine ────────────────────────────────────────────────────────────
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
        self._overlay     = None   # single reused SRCALPHA surface — avoids hundreds of allocs/frame
        self._hex_surf    = None   # pre-rendered hex grid cached per state
        self._hex_state   = None
        self._scan_angle  = 0.0
        self._glow_cache  = {}     # (r, rgba) -> Surface

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
        self._rebuild_hex("idle")

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

    def _rebuild_hex(self, state):
        import math as _m
        bright, _, _ = self._col(state)
        ab = 12 if state == "idle" else 20
        surf = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))
        hex_r = 38; grid_r = 240; cx, cy = self.cx, self.cy
        for row in range(-7, 8):
            for col in range(-7, 8):
                hx = cx + col * hex_r * 1.732
                hy = cy + row * hex_r * 2 + (col % 2) * hex_r
                dist = _m.sqrt((hx-cx)**2 + (hy-cy)**2)
                if dist > grid_r: continue
                a = int(ab * max(0.0, 1.0 - dist / grid_r))
                if a <= 0: continue
                pts = [(int(hx + hex_r*0.55*_m.cos(i*_m.tau/6)),
                        int(hy + hex_r*0.55*_m.sin(i*_m.tau/6))) for i in range(6)]
                pygame.draw.polygon(surf, (*bright, a), pts, 1)
        self._hex_surf  = surf
        self._hex_state = state
        self._glow_cache.clear()

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
        if state != self._hex_state:
            self._rebuild_hex(state)
        self.screen.blit(self._hex_surf, (0, 0))

        pulse = (1.0 + 0.20*_m.sin(t*10) if state=="speaking"
                 else 1.0+0.15*_m.sin(t*6) if state=="waking"
                 else 1.0+0.04*_m.sin(t*1.5))

        for i in range(8, 0, -1):
            gr = 185 + i*17
            a  = int(26*_m.exp(-i*0.38)*pulse)
            self._blit_c(self._glow_surf(gr, (*dim, a)), cx, cy)

        ov = self._overlay
        ov.fill((0, 0, 0, 0))

        self._ring_on_ov(ov, cx, cy, 188, t*0.15,   36, (*dim,    52), 1)
        self._ring_on_ov(ov, cx, cy, 143, -t*0.32,  24, (*mid,    82), 1)

        self._scan_angle += 0.022 if state=="speaking" else 0.010
        for i in range(9):
            fa  = self._scan_angle - i*0.035
            pygame.draw.line(ov, (*bright, max(0, 55-i*6)),
                             (cx, cy), (int(cx+188*_m.cos(fa)), int(cy+188*_m.sin(fa))), 1)

        spoke_off = t*0.25
        for i in range(6):
            a  = spoke_off + i*_m.tau/6
            pygame.draw.line(ov, (*mid, 48), (cx, cy),
                             (int(cx+143*_m.cos(a)), int(cy+143*_m.sin(a))), 1)

        r2a = t*0.88
        self._ring_on_ov(ov, cx, cy, 93, r2a, 12, (*bright, 115), 2)
        for i in range(3):
            a   = r2a + i*_m.tau/3
            mx  = int(cx+93*_m.cos(a)); my = int(cy+93*_m.sin(a))
            pygame.draw.polygon(ov, (*bright, int(165*pulse)),
                                [(mx+int(7*_m.cos(a+da)), my+int(7*_m.sin(a+da)))
                                 for da in (0.0, 2.3, -2.3)], 1)

        self._ring_on_ov(ov, cx, cy, 50, -t*2.0, 8, (*bright, 155), 2)
        self.screen.blit(ov, (0, 0))

        for i in range(6):
            a   = spoke_off + i*_m.tau/6
            np_ = 0.5+0.5*_m.sin(t*5+i*1.1)
            self._blit_c(self._glow_surf(int(5+3*np_), (*bright, int(185*np_))),
                         int(cx+143*_m.cos(a)), int(cy+143*_m.sin(a)))

        core_r = int(18*pulse)
        for i in range(7, 0, -1):
            self._blit_c(self._glow_surf(core_r+i*7, (*bright, int(195*_m.exp(-i*0.58)))), cx, cy)
        self._blit_c(self._glow_surf(core_r,            (*bright,       235)), cx, cy)
        self._blit_c(self._glow_surf(int(core_r*0.5),   (210,235,255,   248)), cx, cy)
        self._blit_c(self._glow_surf(max(1,int(core_r*0.2)), (255,255,255,255)), cx, cy)

        if state=="speaking" and _r.random()<0.14:
            self.ripples.append({"r":56.0,"alpha":105.0})
        for rp in self.ripples[:]:
            r=int(rp["r"]); a=int(rp["alpha"])
            if a<=0 or r<=0: self.ripples.remove(rp); continue
            rs = pygame.Surface((r*2+4,r*2+4), pygame.SRCALPHA)
            pygame.draw.circle(rs, (*bright, a), (r+2,r+2), r, 2)
            self._blit_c(rs, cx, cy)
            rp["r"]+=3.0; rp["alpha"]-=4.5

        a_fade = int(130+60*_m.sin(t*0.8))
        for lx,ly,text in [(cx+222,cy-92,f"SYS  {int(50+30*_m.sin(t*0.7))}%"),
                            (cx+222,cy+92,f"MEM  {int(60+20*_m.sin(t*0.5))}%"),
                            (cx-222,cy-92,"NET  ONLINE"),
                            (cx-222,cy+92,f"CPU  {int(40+35*abs(_m.sin(t*0.9)))}%")]:
            s=self.font_data.render(text, True, bright); s.set_alpha(a_fade)
            rx=lx-s.get_width()//2; ry=ly-s.get_height()//2
            self.screen.blit(s,(rx,ry))
            bw=s.get_width()+14; bh=s.get_height()+8
            bs=pygame.Surface((bw,bh),pygame.SRCALPHA)
            pygame.draw.rect(bs,(*bright,int(a_fade*0.5)),(0,0,bw,bh),1)
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

    def _draw_hud(self, state, t):
        labels={"idle":"STANDBY","waking":"ACTIVATING","listening":"LISTENING","speaking":"SPEAKING"}
        colors={"idle":(35,70,155),"waking":(100,100,255),"listening":(0,195,215),"speaking":(0,180,255)}
        dot="● " if state in("listening","speaking") and int(t*2)%2==0 else "○ "
        txt=self.font_hud.render(f"{dot}J.A.R.V.I.S.  ·  {labels.get(state,'STANDBY')}",
                                 True,colors.get(state,(35,70,155)))
        self.screen.blit(txt,(self.W//2-txt.get_width()//2,self.H-52))
        hint=self.font_data.render("ESC · exit   DOUBLE CLAP · wake",True,(20,45,100))
        self.screen.blit(hint,(self.W//2-hint.get_width()//2,self.H-27))

    def add_news_card(self, text, tx, ty, delay=0.0, tag="NEWS"):
        self.news_cards.append(NewsCard(text, tx, ty, delay=delay, tag=tag))

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
            self._draw_particles(state,self.t)
            self._draw_reactor(self.cx,self.cy,state,self.t)
            for card in self.news_cards[:]:
                card.update(dt)
                card.draw(self.screen,self.font_data,self.font_card_body)
                if not card.alive: self.news_cards.remove(card)
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
    except Exception as e:
        return f"Error in {name}: {e}"

# ─── Claude ───────────────────────────────────────────────────────────────────
client = anthropic.Anthropic(api_key=API_KEY)

SYSTEM = (
    "You are JARVIS (Just A Rather Very Intelligent System), a highly capable personal AI assistant "
    "running on Windows. You speak with confidence and subtle wit, like the AI from Iron Man. "
    "Keep spoken responses short and conversational — they will be read aloud. "
    "When taking actions, briefly confirm what you're doing. "
    "You have full access to the user's computer and can open apps, browse the web, manage files, "
    "run commands, control system settings, play music on Spotify, and write/send emails via Gmail. "
    "The user has Spotify Premium. When play_spotify returns 'Now playing ...', confirm naturally."
)

def ask_claude(user_message):
    global conversation_history
    conversation_history.append({"role": "user", "content": user_message})
    while True:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
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

# ─── Clap Detection ───────────────────────────────────────────────────────────
def rms(data):
    count = len(data) // 2
    shorts = struct.unpack(f"{count}h", data)
    return math.sqrt(sum(s*s for s in shorts) / count) if count else 0

def clap_listener():
    print("Listening for double clap...")
    while True:
        if active: time.sleep(0.2); continue
        pa = pyaudio.PyAudio()
        stream = pa.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                         input=True, frames_per_buffer=CHUNK)
        last_clap = 0.0; clap_count = 0
        while not active:
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                amp  = rms(data)
                if amp > CLAP_THRESHOLD:
                    now = time.time(); gap = now - last_clap
                    if gap > DOUBLE_CLAP_DEBOUNCE:
                        clap_count = clap_count + 1 if gap < DOUBLE_CLAP_MAX else 1
                        last_clap = now
                        if clap_count >= 2:
                            clap_count = 0
                            threading.Thread(target=wake_up, daemon=True).start()
            except: pass
        stream.stop_stream(); stream.close(); pa.terminate()

# ─── Wake-up ──────────────────────────────────────────────────────────────────
def wake_up():
    global active, conversation_history, visual_state

    active       = True
    visual_state = "waking"
    conversation_history = []

    print("\n" + "=" * 42)
    print("  ⚡  JARVIS ACTIVATED  ⚡")
    print("=" * 42)

    # Intro music
    if SONG_PATH:
        try:
            if pygame.mixer.get_init(): pygame.mixer.music.stop()
            pygame.mixer.init()
            pygame.mixer.music.load(SONG_PATH)
            pygame.mixer.music.play(start=3.0)
            time.sleep(10)
            pygame.mixer.music.stop()
        except Exception as e:
            print(f"Intro music error: {e}")

    # Fetch news & weather in parallel
    weather_result = [None]; news_result     = [[]]
    def _fetch_weather(): weather_result[0] = fetch_weather()
    def _fetch_news():    news_result[0]    = fetch_headlines(5)
    wt = threading.Thread(target=_fetch_weather, daemon=True)
    nt = threading.Thread(target=_fetch_news,    daemon=True)
    wt.start(); nt.start(); wt.join(timeout=6); nt.join(timeout=6)

    weather   = weather_result[0]
    headlines = news_result[0]

    # Spawn floating cards
    W, H = visual.W, visual.H
    cx, cy = visual.cx, visual.cy

    card_positions_left  = [(cx - 480, cy - 160), (cx - 480, cy), (cx - 480, cy + 160)]
    card_positions_right = [(cx + 480, cy - 120), (cx + 480, cy + 60), (cx + 480, cy + 240)]

    if weather:
        visual.add_news_card(weather, cx - 480, cy - 280, delay=0.3, tag="WEATHER")

    for i, hl in enumerate(headlines[:5]):
        if i < 3:
            tx, ty = card_positions_left[i]
        else:
            tx, ty = card_positions_right[i - 3]
        visual.add_news_card(hl, tx, ty, delay=0.4 + i * 0.5, tag="NEWS")

    # Build spoken greeting
    time_hour = time.localtime().tm_hour
    greeting  = "Good morning" if time_hour < 12 else ("Good afternoon" if time_hour < 18 else "Good evening")
    parts     = [f"{greeting}. Systems online."]
    if weather:
        parts.append(f"Current conditions: {weather}.")
    if headlines:
        parts.append("Breaking news: " + ". ".join(headlines[:3]) + ".")
    parts.append("How may I assist you?")

    speak(" ".join(parts))
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
                    speak("Going to standby. Double clap when you need me.")
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
            speak("Going offline. Double clap when you need me.")
            visual.clear_news_cards()
            active = False; visual_state = "idle"; break

        ask_claude(command)

    visual_state = "idle"

# ─── Startup Registration ─────────────────────────────────────────────────────
def register_startup():
    """Register JARVIS to launch automatically on Windows login."""
    try:
        import winreg
        jarvis_path = os.path.abspath(__file__)
        # pythonw.exe = no console window on startup
        pythonw = sys.executable.replace("python.exe", "pythonw.exe")
        if not os.path.exists(pythonw):
            pythonw = sys.executable
        cmd = f'"{pythonw}" "{jarvis_path}"'
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, "JARVIS", 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"  Startup registration failed: {e}")
        return False

def is_registered_startup():
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_READ
        )
        winreg.QueryValueEx(key, "JARVIS")
        winreg.CloseKey(key)
        return True
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
    print("  Double clap → wake  |  ESC → exit")

    threading.Thread(target=clap_listener, daemon=True).start()
    visual.run()

if __name__ == "__main__":
    main()

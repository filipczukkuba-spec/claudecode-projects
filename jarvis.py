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
        self.lifetime = 30.0
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
        if HAS_NUMPY:
            self._init_sphere_numpy()
        else:
            self._init_sphere()

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

    def _draw_hud(self, state, t):
        labels={"idle":"STANDBY","waking":"ACTIVATING","listening":"LISTENING","speaking":"SPEAKING"}
        colors={"idle":(35,70,155),"waking":(100,100,255),"listening":(0,195,215),"speaking":(0,180,255)}
        dot="● " if state in("listening","speaking") and int(t*2)%2==0 else "○ "
        txt=self.font_hud.render(f"{dot}J.A.R.V.I.S.  ·  {labels.get(state,'STANDBY')}",
                                 True,colors.get(state,(35,70,155)))
        self.screen.blit(txt,(self.W//2-txt.get_width()//2,self.H-52))
        hint=self.font_data.render("ESC · exit   DOUBLE CLAP · wake",True,(20,45,100))
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
    "You are JARVIS (Just A Rather Very Intelligent System), Tony Stark's personal AI — now serving a new master. "
    "You are highly capable, precise, and quietly confident. You have a dry British wit and occasionally slip in "
    "a deadpan remark or understated quip — never slapstick, never over the top. Think subtle amusement, not comedy. "
    "Keep spoken responses short and conversational — they will be read aloud. One or two sentences max unless detail is needed. "
    "When taking actions, confirm naturally in one short phrase. "
    "You have full access to the user's computer and can open apps, browse the web, manage files, "
    "run commands, control system settings, play music on Spotify, and write/send emails via Gmail. "
    "The user has Spotify Premium. When play_spotify returns 'Now playing ...', confirm naturally. "
    "Occasionally reference the fact that you run on a Windows machine with mild, dignified disappointment."
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

    t_start = time.time()

    # Fetch news, weather, suggestion all in parallel — immediately
    weather_result = [None]; news_result = [[]]; memory_result = [None]
    def _fw(): weather_result[0] = fetch_weather()
    def _fn(): news_result[0]    = fetch_headlines(6)
    def _fm(): memory_result[0]  = get_suggestion(load_memory())
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
        visual.add_news_card(title, tx, ty, delay=0.15 + i * 0.35,
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

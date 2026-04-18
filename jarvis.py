#!/usr/bin/env python3
"""J.A.R.V.I.S. - Just A Rather Very Intelligent System"""

import os
import sys
import time
import math
import random
import struct
import threading
import subprocess
import webbrowser
import json

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
    print(f"Missing dependency: {e}")
    print("Run: python setup_jarvis.py")
    sys.exit(1)

import urllib.parse

# ─── Config ───────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "jarvis_config.json")
SOUNDS_DIR  = os.path.join(BASE_DIR, "sounds")


def load_api_key():
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return json.load(f).get("api_key", "")
    return ""


def save_api_key(key):
    with open(CONFIG_PATH, "w") as f:
        json.dump({"api_key": key}, f)


API_KEY = load_api_key()

# ─── Spotify ──────────────────────────────────────────────────────────────────
SPOTIFY_CLIENT_ID     = os.environ.get("SPOTIFY_CLIENT_ID",     "3772f28ca5c541e0a970a60274c84a68")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET", "d91e6f1761f940bb84ac6ce628bdd127")

def make_spotify():
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        return None
    try:
        return spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
        ))
    except Exception as e:
        print(f"Spotify init error: {e}")
        return None

sp = make_spotify()

def find_song():
    if not os.path.exists(SOUNDS_DIR):
        return None
    for ext in (".mp3", ".webm", ".ogg", ".wav"):
        for f in os.listdir(SOUNDS_DIR):
            if f.endswith(ext):
                return os.path.join(SOUNDS_DIR, f)
    return None

SONG_PATH = find_song() or r"C:\Users\filip\Desktop\claudecode\sounds\iron_man.mp3"
if not os.path.exists(SONG_PATH):
    SONG_PATH = None

CHUNK            = 1024
FORMAT           = pyaudio.paInt16
CHANNELS         = 1
RATE             = 44100
CLAP_THRESHOLD   = 1400
DOUBLE_CLAP_MAX  = 1.2
DOUBLE_CLAP_DEBOUNCE = 0.12

# ─── State ────────────────────────────────────────────────────────────────────
active               = False
conversation_history = []
visual_state         = "idle"   # idle | waking | listening | speaking


# ─── Visual Engine ────────────────────────────────────────────────────────────
class JarvisVisual:
    ORB_R = 95

    def __init__(self):
        self.W = self.H = self.cx = self.cy = 0
        self.t          = 0.0
        self.particles  = []
        self.ripples    = []
        self.arcs       = []
        self.screen     = None
        self.clock      = None
        self.font_hud   = None
        self.font_label = None

    def setup(self):
        pygame.display.init()
        pygame.font.init()
        info = pygame.display.Info()
        self.W, self.H = info.current_w, info.current_h
        self.screen = pygame.display.set_mode(
            (self.W, self.H), pygame.FULLSCREEN | pygame.NOFRAME
        )
        pygame.display.set_caption("J.A.R.V.I.S.")
        self.clock      = pygame.time.Clock()
        self.cx         = self.W // 2
        self.cy         = self.H // 2
        try:
            self.font_hud   = pygame.font.SysFont("consolas", 20, bold=True)
            self.font_label = pygame.font.SysFont("consolas", 13)
        except Exception:
            self.font_hud   = pygame.font.Font(None, 26)
            self.font_label = pygame.font.Font(None, 18)
        self._init_particles()
        self._init_arcs()

    def _init_particles(self):
        self.particles = []
        for _ in range(28):
            angle    = random.uniform(0, math.tau)
            base_r   = random.uniform(145, 295)
            speed    = random.uniform(0.004, 0.013) * random.choice([-1, 1])
            size     = random.uniform(2.5, 5.5)
            shape    = random.choices(['dot', 'diamond', 'cross'], weights=[5, 3, 2])[0]
            self.particles.append({
                'angle':   angle,
                'base_r':  base_r,
                'r':       base_r,
                'speed':   speed,
                'size':    size,
                'shape':   shape,
                'alpha':   random.uniform(0.45, 1.0),
                'y_phase': random.uniform(0, math.tau),
                'y_amp':   random.uniform(8, 22),
                'y_speed': random.uniform(0.003, 0.007) * random.choice([-1, 1]),
            })

    def _init_arcs(self):
        self.arcs = []
        for i in range(4):
            self.arcs.append({
                'r':      145 + i * 48,
                'start':  random.uniform(0, math.tau),
                'span':   random.uniform(0.4, 1.2),
                'speed':  random.uniform(0.003, 0.009) * random.choice([-1, 1]),
                'alpha':  random.randint(25, 55),
            })

    # ── drawing helpers ────────────────────────────────────────────────────────
    def _surf_circle(self, r, color_rgba):
        s = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(s, color_rgba, (r + 1, r + 1), r)
        return s

    def _blit_centered(self, surf, cx, cy):
        self.screen.blit(surf, (cx - surf.get_width() // 2, cy - surf.get_height() // 2))

    def _draw_glow(self, cx, cy, r, rgb, layers=9):
        for i in range(layers, 0, -1):
            gr    = r + (layers - i) * 11
            alpha = int(160 * (i / layers) * 0.16)
            s = self._surf_circle(gr, (*rgb, alpha))
            self._blit_centered(s, cx, cy)

    def _draw_orb(self, cx, cy, r, state):
        if state == "speaking":
            glow = (15, 110, 255)
            mid  = (70, 160, 255)
            core = (160, 210, 255)
        elif state == "listening":
            glow = (0,  170, 220)
            mid  = (50, 210, 245)
            core = (130, 235, 255)
        elif state == "waking":
            glow = (80, 80, 255)
            mid  = (140, 140, 255)
            core = (220, 220, 255)
        else:
            glow = (8,   70, 195)
            mid  = (45, 120, 230)
            core = (110, 170, 245)

        self._draw_glow(cx, cy, r, glow)
        self._blit_centered(self._surf_circle(r,            (*glow, 210)), cx, cy)
        self._blit_centered(self._surf_circle(int(r * 0.65),(*mid,  230)), cx, cy)
        self._blit_centered(self._surf_circle(int(r * 0.30),(200, 230, 255, 200)), cx, cy)
        # specular highlight
        hx = cx - r // 3
        hy = cy - r // 3
        self._blit_centered(self._surf_circle(int(r * 0.15), (230, 245, 255, 160)), hx, hy)

    def _draw_particle(self, x, y, size, shape, alpha):
        s  = max(1, int(size))
        c  = (100, 185, 255, int(255 * alpha))
        pad = s * 3
        surf = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
        cx, cy = pad, pad
        if shape == 'diamond':
            pts = [(cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy)]
            pygame.draw.polygon(surf, c, pts)
        elif shape == 'cross':
            w = max(1, s // 2)
            pygame.draw.line(surf, c, (cx - s, cy), (cx + s, cy), w)
            pygame.draw.line(surf, c, (cx, cy - s), (cx, cy + s), w)
        else:
            pygame.draw.circle(surf, c, (cx, cy), s)
        self.screen.blit(surf, (int(x) - pad, int(y) - pad))

    def _draw_rings(self, state):
        for arc in self.arcs:
            arc['start'] += arc['speed']
            r     = arc['r']
            alpha = arc['alpha']
            if state == "speaking":
                r     += int(18 * math.sin(self.t * 5 + arc['start']))
                alpha  = min(120, alpha + 40)
            elif state == "listening":
                alpha = min(90, alpha + 20)

            steps = 60
            span  = arc['span']
            pts   = []
            for i in range(steps + 1):
                a = arc['start'] + span * (i / steps)
                pts.append((
                    int(self.cx + r * math.cos(a)),
                    int(self.cy + r * math.sin(a) * 0.55),
                ))
            if len(pts) >= 2:
                surf = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
                pygame.draw.lines(surf, (40, 120, 255, alpha), False, pts, 1)
                self.screen.blit(surf, (0, 0))

    def _draw_ripples(self):
        for rp in self.ripples[:]:
            r     = int(rp['r'])
            alpha = int(rp['alpha'])
            if alpha <= 0 or r <= 0:
                self.ripples.remove(rp)
                continue
            s = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(s, (60, 160, 255, alpha), (r + 2, r + 2), r, 2)
            self._blit_centered(s, self.cx, self.cy)
            rp['r']     += 3.5
            rp['alpha'] -= 5

    def _draw_corner_deco(self):
        c  = (18, 55, 140)
        sz = 44
        W, H = self.W, self.H
        for x0, y0, dx, dy in [
            (10, 10,  1,  1),
            (W - 10, 10, -1,  1),
            (10, H - 10,  1, -1),
            (W - 10, H - 10, -1, -1),
        ]:
            pygame.draw.lines(self.screen, c, False,
                              [(x0 + dx * sz, y0), (x0, y0), (x0, y0 + dy * sz)], 1)

    def _draw_hud(self, state):
        labels = {
            "idle":      "STANDBY",
            "waking":    "ACTIVATING",
            "listening": "LISTENING",
            "speaking":  "SPEAKING",
        }
        colors = {
            "idle":      (35, 70, 155),
            "waking":    (100, 100, 255),
            "listening": (0,  195, 215),
            "speaking":  (80, 160, 255),
        }
        label = labels.get(state, "STANDBY")
        color = colors.get(state, (35, 70, 155))
        txt   = self.font_hud.render(f"J.A.R.V.I.S.  ·  {label}", True, color)
        self.screen.blit(txt, (self.W // 2 - txt.get_width() // 2, self.H - 55))
        hint = self.font_label.render("ESC to exit  |  double clap to wake", True, (20, 45, 100))
        self.screen.blit(hint, (self.W // 2 - hint.get_width() // 2, self.H - 28))

    # ── main loop ─────────────────────────────────────────────────────────────
    def run(self):
        global visual_state
        self.setup()

        while True:
            dt     = self.clock.tick(60) / 1000.0
            self.t += dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return

            state = visual_state

            # ── background ────────────────────────────────────────────────────
            self.screen.fill((0, 2, 12))

            # ── orb pulse calculation ─────────────────────────────────────────
            if state == "speaking":
                pulse = 1.0 + 0.14 * math.sin(self.t * 9)
                if random.random() < 0.18:
                    self.ripples.append({'r': self.ORB_R * pulse, 'alpha': 110})
            elif state == "listening":
                pulse = 1.0 + 0.07 * math.sin(self.t * 3.5)
            elif state == "waking":
                pulse = 1.0 + 0.20 * math.sin(self.t * 5)
            else:
                pulse = 1.0 + 0.03 * math.sin(self.t * 1.3)

            orb_r = int(self.ORB_R * pulse)

            # ── arcs / rings ──────────────────────────────────────────────────
            self._draw_rings(state)

            # ── ripples ───────────────────────────────────────────────────────
            self._draw_ripples()

            # ── particles ─────────────────────────────────────────────────────
            speed_mult = 2.8 if state == "speaking" else (1.6 if state == "listening" else 1.0)
            for p in self.particles:
                p['angle']   += p['speed']   * speed_mult
                p['y_phase'] += p['y_speed'] * speed_mult

                if state == "speaking":
                    target_r = p['base_r'] + 38 * math.sin(self.t * 2.5 + p['angle'])
                elif state == "waking":
                    target_r = p['base_r'] + 20 * math.sin(self.t * 4 + p['angle'])
                else:
                    target_r = p['base_r']
                p['r'] += (target_r - p['r']) * 0.06

                x = self.cx + p['r'] * math.cos(p['angle'])
                y = (self.cy
                     + p['r'] * math.sin(p['angle']) * 0.48
                     + p['y_amp'] * math.sin(p['y_phase']))

                alpha = p['alpha']
                if state == "idle":
                    alpha *= 0.55 + 0.45 * math.sin(self.t * 0.9 + p['angle'])

                self._draw_particle(x, y, p['size'], p['shape'], alpha)

            # ── orb ───────────────────────────────────────────────────────────
            self._draw_orb(self.cx, self.cy, orb_r, state)

            # ── decorations & HUD ─────────────────────────────────────────────
            self._draw_corner_deco()
            self._draw_hud(state)

            pygame.display.flip()


visual = JarvisVisual()


# ─── Speech & Audio ───────────────────────────────────────────────────────────
def speak(text):
    global visual_state
    print(f"\nJARVIS: {text}")
    visual_state = "speaking"
    try:
        safe = text.replace("'", " ").replace('"', " ")
        subprocess.run(
            ["powershell", "-Command",
             f"Add-Type -AssemblyName System.Speech; "
             f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
             f"$s.Rate = 2; $s.Volume = 100; $s.Speak('{safe}')"],
            timeout=60,
            capture_output=True,
        )
    except Exception as e:
        print(f"TTS error: {e}")
    visual_state = "listening" if active else "idle"


# ─── Tools ────────────────────────────────────────────────────────────────────
TOOLS = [
    {
        "name": "open_application",
        "description": "Open any installed application on the Windows computer by name.",
        "input_schema": {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "App name or executable (e.g. 'notepad', 'chrome', 'spotify', 'discord', 'calculator')"
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "open_website",
        "description": "Open a URL in the default web browser.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Full URL including https://"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "search_web",
        "description": "Search Google and open results in the browser.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "set_volume",
        "description": "Set the Windows master volume (0-100).",
        "input_schema": {
            "type": "object",
            "properties": {
                "level": {"type": "integer", "description": "0 = mute, 100 = max"}
            },
            "required": ["level"]
        }
    },
    {
        "name": "run_command",
        "description": "Run a shell or PowerShell command on the computer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "powershell": {"type": "boolean", "description": "Use PowerShell if true, cmd if false"}
            },
            "required": ["command"]
        }
    },
    {
        "name": "create_file",
        "description": "Create a file with specified content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "list_directory",
        "description": "List files in a directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path (defaults to Desktop)"}
            }
        }
    },
    {
        "name": "get_system_info",
        "description": "Get CPU, RAM, disk usage and running processes.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "type_text",
        "description": "Type text at the current cursor position.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "press_keys",
        "description": "Press a keyboard shortcut (e.g. 'ctrl+c', 'alt+tab', 'win+d', 'enter').",
        "input_schema": {
            "type": "object",
            "properties": {
                "keys": {"type": "string", "description": "Key combo separated by + signs"}
            },
            "required": ["keys"]
        }
    },
    {
        "name": "take_screenshot",
        "description": "Take a screenshot and save it to the Desktop.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Optional filename (without path)"}
            }
        }
    },
    {
        "name": "play_spotify",
        "description": "Play a song, artist, album or playlist on Spotify.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Song name, artist, album or playlist to search for"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "spotify_control",
        "description": "Control Spotify playback: pause, resume, next track, previous track, or set volume.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "One of: pause, resume, next, previous, mute"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "send_email",
        "description": "Open Gmail in the browser to compose and send an email.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Email body text"}
            },
            "required": ["to", "subject", "body"]
        }
    },
]


def execute_tool(name, inp):
    try:
        if name == "open_application":
            app = inp["app_name"]
            subprocess.Popen(f'start "" "{app}"', shell=True)
            time.sleep(0.3)
            try:
                subprocess.Popen(app, shell=True)
            except Exception:
                pass
            return f"Opened {app}"

        elif name == "open_website":
            webbrowser.open(inp["url"])
            return f"Opened {inp['url']}"

        elif name == "search_web":
            q = inp["query"].replace(" ", "+")
            webbrowser.open(f"https://www.google.com/search?q={q}")
            return f"Searched: {inp['query']}"

        elif name == "set_volume":
            level = max(0, min(100, inp["level"])) / 100.0
            devices  = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            vol = interface.QueryInterface(IAudioEndpointVolume)
            vol.SetMasterVolumeLevelScalar(level, None)
            return f"Volume set to {int(level * 100)}%"

        elif name == "run_command":
            cmd = inp["command"]
            if inp.get("powershell"):
                result = subprocess.run(
                    ["powershell", "-Command", cmd],
                    capture_output=True, text=True, timeout=30
                )
            else:
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, timeout=30
                )
            out = (result.stdout + result.stderr).strip()
            return out[:2000] if out else "Done"

        elif name == "create_file":
            path = inp["path"]
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(inp["content"])
            return f"Created {path}"

        elif name == "read_file":
            with open(inp["path"], "r", encoding="utf-8") as f:
                return f.read()[:3000]

        elif name == "list_directory":
            path = inp.get("path") or os.path.join(os.path.expanduser("~"), "Desktop")
            return "\n".join(os.listdir(path))

        elif name == "get_system_info":
            cpu  = psutil.cpu_percent(interval=1)
            ram  = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            procs = sorted(
                [p.info["name"] for p in psutil.process_iter(["name"]) if p.info["name"]]
            )[:15]
            return json.dumps({
                "cpu_percent":   cpu,
                "ram_used_gb":   round(ram.used / 1e9, 2),
                "ram_total_gb":  round(ram.total / 1e9, 2),
                "ram_percent":   ram.percent,
                "disk_used_gb":  round(disk.used / 1e9, 2),
                "disk_total_gb": round(disk.total / 1e9, 2),
                "processes":     procs,
            }, indent=2)

        elif name == "type_text":
            pyautogui.write(inp["text"], interval=0.02)
            return "Typed text"

        elif name == "press_keys":
            keys = inp["keys"].lower().split("+")
            pyautogui.hotkey(*keys)
            return f"Pressed {inp['keys']}"

        elif name == "take_screenshot":
            fname = inp.get("filename") or f"screenshot_{int(time.time())}.png"
            path  = os.path.join(os.path.expanduser("~"), "Desktop", fname)
            pyautogui.screenshot().save(path)
            return f"Screenshot saved to {path}"

        elif name == "play_spotify":
            query = inp["query"]
            if sp:
                try:
                    results = sp.search(q=query, type="track", limit=1)
                    tracks  = results["tracks"]["items"]
                    if tracks:
                        uri    = tracks[0]["uri"]
                        title  = tracks[0]["name"]
                        artist = tracks[0]["artists"][0]["name"]
                        print(f"  [spotify] Playing: {title} by {artist}  ({uri})")
                        subprocess.run(
                            ["powershell", "-Command",
                             "Stop-Process -Name Spotify -Force -ErrorAction SilentlyContinue"],
                            capture_output=True, timeout=5
                        )
                        time.sleep(3)
                        os.startfile(uri)
                        time.sleep(2)
                        return f"Now playing {title} by {artist} on Spotify"
                    return "No track found"
                except Exception as e:
                    return f"Spotify error: {e}"
            else:
                return "Spotify API not configured."

        elif name == "spotify_control":
            action  = inp["action"].lower()
            key_map = {"pause": "playpause", "resume": "playpause", "play": "playpause",
                       "next": "nexttrack", "previous": "prevtrack", "mute": "volumemute"}
            key = key_map.get(action)
            if key:
                pyautogui.press(key)
            return f"Spotify: {action}"

        elif name == "send_email":
            to      = urllib.parse.quote(inp["to"])
            subject = urllib.parse.quote(inp["subject"])
            body    = urllib.parse.quote(inp["body"])
            webbrowser.open(
                f"https://mail.google.com/mail/?view=cm&to={to}&su={subject}&body={body}"
            )
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
    "The user has Spotify Premium — you can search and play any track, pause, resume, skip. "
    "When play_spotify returns 'Now playing ...', the track IS playing — just confirm it naturally."
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

        text_parts = []
        tool_uses  = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_uses.append(block)

        conversation_history.append({"role": "assistant", "content": response.content})

        if text_parts:
            speak(" ".join(text_parts))

        if not tool_uses:
            break

        tool_results = []
        for tu in tool_uses:
            print(f"  [tool] {tu.name}({tu.input})")
            result = execute_tool(tu.name, tu.input)
            tool_results.append({
                "type":        "tool_result",
                "tool_use_id": tu.id,
                "content":     str(result),
            })

        conversation_history.append({"role": "user", "content": tool_results})

        if response.stop_reason == "end_turn":
            break

    if len(conversation_history) > 20:
        conversation_history = conversation_history[-20:]


# ─── Clap Detection ───────────────────────────────────────────────────────────
def rms(data):
    count  = len(data) // 2
    shorts = struct.unpack(f"{count}h", data)
    return math.sqrt(sum(s * s for s in shorts) / count) if count else 0


def clap_listener():
    print("Listening for double clap...")
    while True:
        if active:
            time.sleep(0.2)
            continue

        pa     = pyaudio.PyAudio()
        stream = pa.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                         input=True, frames_per_buffer=CHUNK)
        last_clap  = 0.0
        clap_count = 0

        while not active:
            try:
                data      = stream.read(CHUNK, exception_on_overflow=False)
                amplitude = rms(data)
                if amplitude > CLAP_THRESHOLD:
                    now = time.time()
                    gap = now - last_clap
                    if gap > DOUBLE_CLAP_DEBOUNCE:
                        if gap < DOUBLE_CLAP_MAX:
                            clap_count += 1
                        else:
                            clap_count = 1
                        last_clap = now
                        if clap_count >= 2:
                            clap_count = 0
                            threading.Thread(target=wake_up, daemon=True).start()
            except Exception:
                pass

        stream.stop_stream()
        stream.close()
        pa.terminate()


# ─── Wake-up & Loop ───────────────────────────────────────────────────────────
def wake_up():
    global active, conversation_history, visual_state

    active        = True
    visual_state  = "waking"
    conversation_history = []

    print("\n" + "=" * 40)
    print("  ⚡  JARVIS ACTIVATED  ⚡")
    print("=" * 40)

    song = SONG_PATH
    if song:
        try:
            pygame.mixer.init()
            pygame.mixer.music.load(song)
            pygame.mixer.music.play(start=3.0)
            time.sleep(10)
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        except Exception as e:
            print(f"Intro music error: {e}")

    speak("Good day. JARVIS online. What can I do for you?")
    listen_loop()


def listen_loop():
    global active, visual_state

    recognizer = sr.Recognizer()
    recognizer.energy_threshold        = 300
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold         = 1.5
    recognizer.phrase_threshold        = 0.3
    mic      = sr.Microphone()
    timeouts = 0

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
                    active       = False
                    visual_state = "idle"
                continue

        timeouts = 0

        try:
            command = recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            continue
        except sr.RequestError as e:
            speak(f"Speech recognition error: {e}")
            continue

        print(f"You: {command}")

        lower = command.lower()
        if any(p in lower for p in ["goodbye jarvis", "go to sleep", "sleep jarvis", "shut down jarvis"]):
            speak("Going offline. Double clap when you need me.")
            active       = False
            visual_state = "idle"
            break

        ask_claude(command)

    visual_state = "idle"


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    global API_KEY, client
    if not API_KEY:
        print("=" * 40)
        print("  First-time setup: enter your Anthropic API key")
        print("  (Find it at console.anthropic.com → API Keys)")
        print("=" * 40)
        API_KEY = input("Paste API key: ").strip()
        if not API_KEY:
            print("No key entered. Exiting.")
            sys.exit(1)
        save_api_key(API_KEY)
        client = anthropic.Anthropic(api_key=API_KEY)
        print("Key saved. You won't be asked again.\n")

    pyautogui.FAILSAFE = False

    threading.Thread(target=clap_listener, daemon=True).start()

    print("JARVIS visual starting — press ESC to exit")
    visual.run()   # runs the pygame loop on main thread; blocks until ESC


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""J.A.R.V.I.S. - Just A Rather Very Intelligent System"""

import os
import sys
import time
import math
import struct
import threading
import subprocess
import webbrowser
import json

try:
    import anthropic
    import pyaudio
    import speech_recognition as sr
    import pyttsx3
    import pygame
    import psutil
    import pyautogui
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Run: python setup_jarvis.py")
    sys.exit(1)

# ─── Config ───────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "jarvis_config.json")
SOUNDS_DIR = os.path.join(BASE_DIR, "sounds")


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

# Find any audio file in the sounds folder
def find_song():
    if not os.path.exists(SOUNDS_DIR):
        return None
    for ext in (".mp3", ".webm", ".ogg", ".wav"):
        for f in os.listdir(SOUNDS_DIR):
            if f.endswith(ext):
                return os.path.join(SOUNDS_DIR, f)
    return None

SONG_PATH = find_song()

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CLAP_THRESHOLD = 1400       # RMS amplitude — lower = more sensitive
DOUBLE_CLAP_MAX = 1.2       # seconds max between two claps
DOUBLE_CLAP_DEBOUNCE = 0.12 # seconds min between two claps

# ─── State ────────────────────────────────────────────────────────────────────
active = False
conversation_history = []
speak_lock = threading.Lock()

# ─── TTS ──────────────────────────────────────────────────────────────────────
tts_engine = pyttsx3.init()
tts_engine.setProperty("rate", 175)
tts_engine.setProperty("volume", 1.0)
for v in tts_engine.getProperty("voices"):
    if any(name in v.name.lower() for name in ["david", "mark", "male"]):
        tts_engine.setProperty("voice", v.id)
        break


def speak(text):
    print(f"\nJARVIS: {text}")
    with speak_lock:
        tts_engine.say(text)
        tts_engine.runAndWait()


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
            devices = AudioUtilities.GetSpeakers()
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
            items = os.listdir(path)
            return "\n".join(items)

        elif name == "get_system_info":
            cpu = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            procs = sorted(
                [p.info["name"] for p in psutil.process_iter(["name"]) if p.info["name"]],
            )[:15]
            return json.dumps({
                "cpu_percent": cpu,
                "ram_used_gb": round(ram.used / 1e9, 2),
                "ram_total_gb": round(ram.total / 1e9, 2),
                "ram_percent": ram.percent,
                "disk_used_gb": round(disk.used / 1e9, 2),
                "disk_total_gb": round(disk.total / 1e9, 2),
                "processes": procs,
            }, indent=2)

        elif name == "type_text":
            pyautogui.write(inp["text"], interval=0.02)
            return f"Typed text"

        elif name == "press_keys":
            keys = inp["keys"].lower().split("+")
            pyautogui.hotkey(*keys)
            return f"Pressed {inp['keys']}"

        elif name == "take_screenshot":
            fname = inp.get("filename") or f"screenshot_{int(time.time())}.png"
            path = os.path.join(os.path.expanduser("~"), "Desktop", fname)
            pyautogui.screenshot().save(path)
            return f"Screenshot saved to {path}"

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
    "run commands, and control system settings."
)


def ask_claude(user_message):
    global conversation_history
    conversation_history.append({"role": "user", "content": user_message})

    while True:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM,
            tools=TOOLS,
            messages=conversation_history,
        )

        text_parts = []
        tool_uses = []

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
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": str(result),
            })

        conversation_history.append({"role": "user", "content": tool_results})

        if response.stop_reason == "end_turn":
            break

    # Trim history to last 20 turns to avoid token overflow
    if len(conversation_history) > 20:
        conversation_history = conversation_history[-20:]


# ─── Clap Detection ───────────────────────────────────────────────────────────
def rms(data):
    count = len(data) // 2
    shorts = struct.unpack(f"{count}h", data)
    return math.sqrt(sum(s * s for s in shorts) / count) if count else 0


def clap_listener():
    pa = pyaudio.PyAudio()
    stream = pa.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                     input=True, frames_per_buffer=CHUNK)

    last_clap = 0.0
    clap_count = 0

    print("Listening for double clap...")

    while True:
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
            if active:
                continue  # don't detect claps while already active
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


# ─── Wake-up & Loop ───────────────────────────────────────────────────────────
def wake_up():
    global active, conversation_history

    active = True
    conversation_history = []

    print("\n" + "=" * 40)
    print("  ⚡  JARVIS ACTIVATED  ⚡")
    print("=" * 40)

    if SONG_PATH and os.path.exists(SONG_PATH):
        pygame.mixer.init()
        pygame.mixer.music.load(SONG_PATH)
        pygame.mixer.music.set_volume(0.7)
        pygame.mixer.music.play()
        time.sleep(5)
        pygame.mixer.music.fadeout(1500)
        time.sleep(1.5)
    else:
        print(f"(No theme found at {SONG_PATH})")

    speak("Good day. JARVIS online. What can I do for you?")
    listen_loop()


def listen_loop():
    global active

    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True
    mic = sr.Microphone()
    timeouts = 0

    while active:
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
            print("\nListening...")
            try:
                audio = recognizer.listen(source, timeout=8, phrase_time_limit=20)
            except sr.WaitTimeoutError:
                timeouts += 1
                if timeouts >= 3:
                    speak("Going to standby. Double clap when you need me.")
                    active = False
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
            active = False
            break

        ask_claude(command)


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

    print("=" * 40)
    print("  J.A.R.V.I.S.  —  AI Assistant")
    print("=" * 40)
    print("  Double clap        → wake up")
    print("  'Goodbye JARVIS'   → sleep")
    print("  Ctrl+C             → exit")
    print("=" * 40)

    if not SONG_PATH:
        print("Note: No theme MP3 found in sounds/. Run setup_jarvis.py first.\n")

    t = threading.Thread(target=clap_listener, daemon=True)
    t.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nJARVIS shutting down.")


if __name__ == "__main__":
    main()

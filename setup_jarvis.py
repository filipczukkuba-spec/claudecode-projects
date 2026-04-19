#!/usr/bin/env python3
"""JARVIS Setup - installs dependencies and downloads the Iron Man theme"""

import subprocess
import sys
import os

PACKAGES = [
    "anthropic",
    "pyaudio",
    "SpeechRecognition",
    "pyttsx3",
    "pygame",
    "psutil",
    "pyautogui",
    "pycaw",
    "comtypes",
    "yt-dlp",
    "playwright",
]

SOUNDS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds")
SONG_PATH = os.path.join(SOUNDS_DIR, "iron_man.mp3")


def install_packages():
    print("Installing packages...")
    for pkg in PACKAGES:
        print(f"  Installing {pkg}...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", pkg, "--quiet"],
            stdout=subprocess.DEVNULL,
        )
    print("All packages installed.\n")


def download_song():
    if os.path.exists(SONG_PATH):
        print(f"Iron Man theme already exists at {SONG_PATH}")
        return

    os.makedirs(SOUNDS_DIR, exist_ok=True)
    print("Downloading Iron Man theme (AC/DC - Back in Black from Iron Man 2)...")

    result = subprocess.run(
        [
            sys.executable, "-m", "yt_dlp",
            "ytsearch1:AC/DC Back in Black Iron Man 2 official",
            "-x",
            "--audio-format", "mp3",
            "--audio-quality", "5",
            "-o", os.path.join(SOUNDS_DIR, "iron_man.%(ext)s"),
            "--no-playlist",
            "--quiet",
            "--no-warnings",
        ]
    )

    if result.returncode == 0 and os.path.exists(SONG_PATH):
        print(f"Downloaded to {SONG_PATH}\n")
    else:
        print("Download failed. You can manually place an MP3 at:")
        print(f"  {SONG_PATH}\n")


if __name__ == "__main__":
    install_packages()
    download_song()
    print("=" * 50)
    print("Setup complete! Run jarvis.py to start.")
    print("Make sure ANTHROPIC_API_KEY is set:")
    print('  set ANTHROPIC_API_KEY=your-key-here')
    print("=" * 50)

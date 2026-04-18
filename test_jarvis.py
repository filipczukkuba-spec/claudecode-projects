#!/usr/bin/env python3
"""JARVIS Diagnostic - run this to find what's broken"""

import os, sys, time, math, struct

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOUNDS_DIR = os.path.join(BASE_DIR, "sounds")

print("=" * 50)
print("  JARVIS Diagnostic")
print("=" * 50)

# 1. Check sounds folder
print("\n[1] Checking sounds folder...")
if os.path.exists(SOUNDS_DIR):
    files = os.listdir(SOUNDS_DIR)
    if files:
        for f in files:
            print(f"    FOUND: {f}")
    else:
        print("    EMPTY - no files in sounds/")
else:
    print("    MISSING - sounds/ folder doesn't exist")

# 2. Test pygame music
print("\n[2] Testing music playback...")
try:
    import pygame
    pygame.mixer.init()
    mp3 = None
    if os.path.exists(SOUNDS_DIR):
        for f in os.listdir(SOUNDS_DIR):
            if f.endswith(".mp3"):
                mp3 = os.path.join(SOUNDS_DIR, f)
    if mp3:
        pygame.mixer.music.load(mp3)
        pygame.mixer.music.play()
        print(f"    Playing {mp3} for 4 seconds...")
        time.sleep(4)
        pygame.mixer.music.stop()
        print("    Music OK")
    else:
        print("    SKIP - no mp3 found")
except Exception as e:
    print(f"    ERROR: {e}")

# 3. Test microphone + clap detection
print("\n[3] Testing microphone (clap or speak now — 5 seconds)...")
try:
    import pyaudio
    CHUNK = 1024
    pa = pyaudio.PyAudio()
    stream = pa.open(format=pyaudio.paInt16, channels=1, rate=44100,
                     input=True, frames_per_buffer=CHUNK)
    peak = 0
    for _ in range(int(44100 / CHUNK * 5)):
        data = stream.read(CHUNK, exception_on_overflow=False)
        count = len(data) // 2
        shorts = struct.unpack(f"{count}h", data)
        rms = math.sqrt(sum(s*s for s in shorts) / count)
        if rms > peak:
            peak = rms
        if rms > 500:
            print(f"    Sound detected: RMS={int(rms)}")
    stream.stop_stream()
    stream.close()
    pa.terminate()
    print(f"    Peak RMS = {int(peak)}  (clap threshold in jarvis.py = 2500)")
    if peak < 1000:
        print("    WARNING: mic seems very quiet — check mic permissions/volume")
    elif peak < 2500:
        print("    >>> Lower CLAP_THRESHOLD in jarvis.py to", int(peak * 0.7))
    else:
        print("    Microphone OK")
except Exception as e:
    print(f"    ERROR: {e}")

# 4. Test speech recognition
print("\n[4] Testing speech recognition (say something — 5 seconds)...")
try:
    import speech_recognition as sr
    r = sr.Recognizer()
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source, duration=1)
        print("    Listening...")
        try:
            audio = r.listen(source, timeout=5, phrase_time_limit=5)
            text = r.recognize_google(audio)
            print(f"    Heard: '{text}'  — Speech recognition OK")
        except sr.WaitTimeoutError:
            print("    Timeout - nothing heard")
        except sr.UnknownValueError:
            print("    Could not understand audio")
        except Exception as e:
            print(f"    ERROR: {e}")
except Exception as e:
    print(f"    ERROR: {e}")

print("\n" + "=" * 50)
input("Press Enter to exit...")

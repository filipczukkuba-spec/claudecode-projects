---
type: context
project: jarvis
---

# Jarvis

**File:** `jarvis.py` | **Memory:** `jarvis_memory.json` | **Config:** `jarvis_config.json`

## What it is
Voice-controlled AI assistant (JARVIS from Iron Man). British male TTS via `edge_tts` (en-GB-RyanNeural). Uses Claude (Anthropic) as brain.

## Stack
- Speech: `speech_recognition` + `pyaudio`
- TTS: `edge_tts`
- AI: `anthropic` SDK
- Spotify: `spotipy`
- Audio control: `pycaw`
- UI automation: `pyautogui`, `pygetwindow`
- Sounds: `./sounds/` folder

## Capabilities (from memory log)
- Google Calendar display
- Spotify playback
- Gmail open
- Week-ahead view
- Volume control

## Setup
Run `setup_jarvis.py` to install deps. API key stored in `jarvis_config.json` or `ANTHROPIC_API_KEY` env var.

## Launcher
`launch_jarvis (2).bat`

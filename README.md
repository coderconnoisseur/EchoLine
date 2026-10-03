# EchoLine - Real-Time Speech-to-Text Overlay
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![Moonshine](https://img.shields.io/badge/Speech-Moonshine-orange)
![PySide6](https://img.shields.io/badge/GUI-PySide6%20%2B%20QML-green?logo=qt&logoColor=white)
![Accessibility](https://img.shields.io/badge/Accessibility-Live_Captions-brightgreen)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)

EchoLine shows live captions for anything playing on your PC: videos, calls,
games, podcasts. Speech recognition runs entirely on your machine, so it works
offline and nothing you hear leaves your computer.

## Features
- Real-time captions of any audio playing on your PC, no Stereo Mix needed
- Follows your output device: switch to headphones or Bluetooth and captions keep going
- Fully offline after a one-time model download
- Always-on-top, translucent overlay with smoothly rolling caption lines, or film-style subtitle blocks
- Four caption themes (Classic CC, Netflix, Minimal, High contrast) and full control over font, size, colors, outline, background, width and line count
- Remembers where you put it; snap to the top, center or bottom of the screen
- Tray icon, hover bar and global hotkeys: **Ctrl+Alt+C** show/hide, **Ctrl+Alt+P** pause, **Ctrl+Alt+T** click-through
- Microphone captioning for in-person conversations and lectures
- Click-through (clicks reach the window below), auto-hide after silence, start with Windows
- Drag the overlay anywhere, or drag its edges to resize

## Requirements
- Windows 10 or 11
- Python 3.10 or higher

## Installation & Setup

1. **Clone this repository:**
   ```bash
   git clone https://github.com/coderconnoisseur/EchoLine.git
   cd EchoLine
   ```
2. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Run EchoLine:**
   ```bash
   python -m echoline
   ```
   The speech model downloads automatically on first run (tens of MB for the
   default model). Play anything with speech and captions appear at the
   bottom of your screen.

### Options
- `--model tiny|small|medium`: larger models are more accurate but need a faster CPU (default: `tiny`)
- `--show-latency`: show how long captions take to appear (p50 / p95)

## Controls

- **Tray icon:** left-click hides or shows the captions. Right-click for pause,
  click-through, audio source (system audio or microphone), settings and quit.
- **Hover bar:** move the pointer over the captions for pause, source,
  settings and hide buttons.
- **Hotkeys** (work while other apps have focus; change them in Settings → Hotkeys):
  - `Ctrl+Alt+C` show or hide captions
  - `Ctrl+Alt+P` pause or resume
  - `Ctrl+Alt+T` click-through on or off
- **Click-through:** the captions ignore the mouse so you can click the video
  under them. Turn it off with `Ctrl+Alt+T` or from the tray icon.

Hiding the captions keeps EchoLine running in the tray; quit from the tray
menu or the captions' right-click menu.

## Customizing

Right-click the captions (or press **Ctrl + ,** while they are focused) to open
settings. Changes preview live. Settings are stored in
`%APPDATA%\EchoLine\settings.json`; if that file is damaged, EchoLine backs it
up as `settings.json.bak` and starts with defaults.

## Running the tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

The tests use fake speech engines, fake audio devices and Qt's offscreen
platform, so they need neither a speech model nor an audio device. Tests that
run real models are marked and run with `python -m pytest -m model`.

## Benchmarking

Compare speech engines on reference clips (accuracy and speed):

```bash
python -m scripts.fetch_bench_clips
python -m echoline.bench --engines moonshine-tiny moonshine-small
```

Results for the reference machine are in [docs/benchmarks](docs/benchmarks/).
The transcription metrics package is documented in [metrics/README.md](metrics/README.md).

## Troubleshooting

**No captions appear**
- Check that sound is playing through your default output device and is not muted.
- If the overlay shows "No audio device", connect or enable an output device; EchoLine picks it up automatically.

**Captions lag behind ("Catching up…")**
- Your CPU cannot keep up with the selected model. Use `--model tiny`.

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
- Tray icon, hover bar and global hotkeys: **Ctrl+Alt+Shift+C** show/hide, **Ctrl+Alt+Shift+P** pause, **Ctrl+Alt+Shift+T** click-through
- Microphone captioning for in-person conversations and lectures
- Click-through (clicks reach the window below), auto-hide after silence, start with Windows
- Drag the overlay anywhere, or drag its edges to resize

## Install

1. Download **EchoLine-Setup.exe** from the
   [latest release](https://github.com/coderconnoisseur/EchoLine/releases/latest)
   (Windows 10 or 11, 64-bit). No admin rights needed.
2. Run it. The installer is not code-signed yet, so Windows may show
   "Windows protected your PC": click **More info → Run anyway**.
3. EchoLine starts with a short setup: it downloads the speech model
   (45 MB, once), checks your PC, plays a sound test and lets you pick a look.

Prefer no installer? Download the portable `.zip`, extract it anywhere and run
`EchoLine.exe`. If something goes wrong, `%LOCALAPPDATA%\EchoLine\echoline.log`
says why; please attach it to an issue.

## Run from source

Requires Windows 10 or 11 and Python 3.10 or higher.

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
   The first launch opens a short setup: it downloads the speech model (45 MB,
   or 190 MB if your PC is fast enough for the more accurate Small model),
   runs a sound test and lets you pick a look. Models are stored in
   `%LOCALAPPDATA%\EchoLine\models`. Launching EchoLine again while it runs
   brings the running copy forward.

### Options
- `--model tiny|small|medium`: use this model for one run instead of the one chosen at setup (switch for good under Settings → Behavior → Speech model)
- `--show-latency`: show how long captions take to appear (p50 / p95)

## Controls

- **Tray icon:** left-click hides or shows the captions. Right-click for pause,
  click-through, audio source (system audio or microphone), settings and quit.
- **Hover bar:** move the pointer over the captions for pause, source,
  settings and hide buttons.
- **Hotkeys** (work while other apps have focus; change them in Settings → Hotkeys):
  - `Ctrl+Alt+Shift+C` show or hide captions
  - `Ctrl+Alt+Shift+P` pause or resume
  - `Ctrl+Alt+Shift+T` click-through on or off
- **Click-through:** the captions ignore the mouse so you can click the video
  under them. Turn it off with `Ctrl+Alt+Shift+T` or from the tray icon.

Hiding the captions keeps EchoLine running in the tray; quit from the tray
menu or the captions' right-click menu.

## Customizing

Right-click the captions, or use the tray icon, to open Settings. Pages on the
left cover Appearance, Position, Behavior, Speech, Shortcuts and About; a live
preview at the top shows every change, and the window follows Windows' light or
dark theme and accent colour. Changes apply immediately. Settings are stored in
`%APPDATA%\EchoLine\settings.json`; if that file is damaged, EchoLine backs it
up as `settings.json.bak` and starts with defaults.

Captions arrive word by word: new words fade in, words the engine is still
unsure about are dimmed and brighten once they settle, and corrections
cross-fade in place. If "Show animations in Windows" is turned off
(Settings → Accessibility → Visual effects), captions update without motion.

## Building the installer

```bash
pip install pyinstaller==6.16.0
python -m PyInstaller packaging/echoline.spec --noconfirm --distpath build/dist --workpath build/work
iscc /DAppVersion=0.3.0 packaging\installer.iss
```

Releases are built by GitHub Actions: pushing a tag such as `v0.3.0` (or
`v0.3.0-beta.1` for a pre-release) tests, builds and publishes the installer,
a portable zip and `SHA256SUMS.txt`.

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
- Your CPU cannot keep up with the selected model. Choose Tiny under Settings → Behavior → Speech model.

## License

EchoLine is released under the [MIT License](LICENSE). It uses
[Moonshine](https://github.com/moonshine-ai/moonshine) English speech models
(MIT) and [Qt for Python](https://www.qt.io/qt-for-python) (LGPL-3.0).

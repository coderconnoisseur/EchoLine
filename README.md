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
- Always-on-top, translucent overlay with smoothly rolling caption lines
- Drag the overlay anywhere; quit with **Ctrl + Q** or **Esc**

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

# EchoLine v1 — Product Design

Date: 2026-10-03
Status: Approved design, pending spec review

## Goal

Turn EchoLine from a personal project into a product strangers can download,
set up in under two minutes, and keep using: live, offline, private captions for
anything playing on a Windows PC.

Every target audience (deaf / hard-of-hearing users, meeting attendees, language
learners, streamers) needs the same foundation, so v1 builds only that:

1. **Low latency** — words appear while they are being spoken.
2. **Modern, smooth UI** — animated, GPU-rendered captions that do not look dated.
3. **Customizable captions** — how text looks and how it flows.
4. **Easy setup** — no Python, no Stereo Mix, no manual model download.

Translation, transcripts, more languages and other features are deferred to
[ROADMAP.md](../../ROADMAP.md).

### Success criteria

- A first-time user goes from the download page to live captions in < 2 minutes
  with no manual configuration beyond clicking through first-run setup.
- Typical (p50) sound-to-screen caption latency < 300 ms on a mid-range laptop
  CPU; p95 < 600 ms.
- Captions stay smooth (no visible stutter or full-text redraws) during
  continuous speech for at least one hour, with flat memory use.
- Works fully offline after the one-time model download.

## Decisions

| Topic | Decision | Why |
|---|---|---|
| UI stack | PySide6 + QML (Qt Quick) | GPU-rendered, animations built in, single process (lowest latency), single-exe packaging |
| Speech engine | Moonshine v2 streaming (`moonshine-voice`), Vosk kept as fallback engine | Built for live captions; reported ~50 ms (Tiny) / ~150 ms (Small) latency with near-Whisper accuracy; MIT code and English models |
| Default model | Auto-pick by hardware on first run (Small if the CPU keeps up, else Tiny) | Best accuracy each machine can afford; user can override |
| Audio capture | WASAPI loopback via PyAudioWPatch, behind an `AudioSource` interface | Captures whatever plays on the default output device (incl. Bluetooth) without Stereo Mix; interface leaves room for mic and per-app capture |
| Languages | English only in v1 | Smallest scope, best demo quality |
| Distribution | Inno Setup installer + portable zip, on GitHub Releases | Installer for most users, zip for people who avoid installers |
| Code signing | None in v1 | No budget yet; explain the SmartScreen prompt on the site and publish checksums |

## Architecture

One process, four isolated units connected by queues and Qt signals:

```
AudioSource ──► SpeechEngine ──► CaptionModel ──► QML overlay
(capture thread)  (engine thread)   (GUI thread)     (scene graph)
```

### `AudioSource` (package `echoline/audio`)

Interface:

```python
class AudioSource(Protocol):
    name: str
    def start(self, on_audio: Callable[[np.ndarray], None]) -> None: ...
    def stop(self) -> None: ...
```

- `on_audio` receives float32 mono samples at 16 kHz in blocks of 20–50 ms.
  Each source owns downmixing and resampling from the device format.
- `LoopbackSource` — WASAPI loopback on the current default output device.
  Watches for default-device changes (headphones plugged in, Bluetooth
  connected) and reopens the stream on the new device.
- `MicrophoneSource` — default or chosen input device.
- Source choice persists in settings. Per-app capture is a future
  `ProcessLoopbackSource` with the same interface.

### `SpeechEngine` (package `echoline/engine`)

Interface:

```python
@dataclass(frozen=True)
class Partial:
    utterance_id: int
    text: str

@dataclass(frozen=True)
class Final:
    utterance_id: int
    text: str

class SpeechEngine(Protocol):
    def feed(self, samples: np.ndarray) -> list[Partial | Final]: ...
    def flush(self) -> list[Final]: ...
```

- Runs on a dedicated worker thread fed by a bounded queue from the audio
  source.
- `MoonshineEngine` (default) wraps `moonshine-voice` streaming
  transcription. `VoskEngine` adapts the existing `SpeechRecognizer`.
- **Backlog protection:** if more than ~3 s of audio is waiting, the oldest
  audio is dropped and a `lagging` status is raised so the UI can suggest a
  smaller model. Captions must never drift behind real time.

### `CaptionModel` (package `echoline/captions`)

- Grows out of the existing `CaptionBuffer`. Holds recent utterances, each with
  a stable `utterance_id`, `text` and `final` flag; partials update their
  utterance in place.
- Exposed to QML as a `QAbstractListModel`, so QML animates per-utterance
  changes instead of re-rendering the whole text.
- Keeps a bounded history (enough for the visible lines plus the fade-out
  animation).

### QML UI (package `echoline/ui`)

- `Overlay.qml` — frameless, transparent, always-on-top window.
  - **Rolling mode (default):** the live line updates in place; finished lines
    slide up and fade out. 1–3 visible lines.
  - **Subtitle mode:** one block per phrase, cross-fading to the next.
  - Status pill for "Listening", "No audio device", "Paused", "Lagging".
- `HoverBar.qml` — slim bar on hover: pause, source switch, settings, close.
- `Settings.qml` — pages: Appearance, Position & Behavior, Audio, Engine,
  Hotkeys, About. Changes preview live on the overlay.
- `Onboarding.qml` — first-run flow in three steps: getting ready (model
  download with progress + hardware check) → sound test ("play something") →
  theme pick. See [First-run setup (M4)](#first-run-setup-m4).
- System tray icon (`QSystemTrayIcon`): show/hide, pause, click-through toggle,
  settings, quit. Needed because click-through overlays cannot be hovered.

### Supporting services

- `Settings` — dataclass persisted as JSON in `%APPDATA%\EchoLine\settings.json`
  and exposed to QML as properties. Unknown or invalid values fall back to
  defaults.
- Themes — named presets over the appearance settings: **Classic CC**,
  **Netflix**, **Minimal**, **High-contrast**.
- `ModelManager` — downloads models to `%LOCALAPPDATA%\EchoLine\models` with
  progress, checksum verification and resume. Runs the hardware check: time Tiny
  on a short bundled clip and choose Small only if Tiny is fast enough that Small
  keeps up, otherwise Tiny (details in [First-run setup (M4)](#first-run-setup-m4)).
- Global hotkeys via Win32 `RegisterHotKey`: show/hide captions, pause/resume,
  toggle click-through. Defaults are configurable and must not clash with common
  shortcuts: **Ctrl+Alt+Shift+C / P / T** (plain Ctrl+Alt is AltGr on many
  European layouts, e.g. Polish Programmer AltGr+C = ć).
- Single-instance guard: launching again focuses the running instance.

## First-run setup (M4)

### Model files

moonshine-voice 0.1.5 already downloads with progress, resume (`.partial` files
and HTTP Range), size and CRC32C verification and atomic rename. `ModelManager`
(`echoline/models.py`) is a thin wrapper over it, not a second downloader:

- Models live under `%LOCALAPPDATA%\EchoLine\models` (passed as `cache_root`);
  `MoonshineEngine.load` reads from the same root, so the engine never
  downloads on its own.
- `is_downloaded(name)` — every file in the model's manifest exists with its
  expected size. Offline; the manifest comes from the native library.
- `download(name, on_progress)` — blocking, called on a worker thread; reports a
  0–1 fraction. Errors propagate to the caller.
- Model names: `tiny`, `small` (offered in the UI) and `medium` (`--model` only).

### Hardware check

Stream the first 15 s of the bundled `two_cities.wav` through Tiny with the
live streaming settings, in 50 ms chunks as fast as possible, and measure the
real-time factor (processing time / audio time). Choose **Small** when Tiny's
RTF ≤ **0.25**, otherwise **Tiny**. Small costs ~1.9× Tiny in the M0 benchmark
(0.88 vs 0.47), so this keeps Small under the benchmark's 0.5 bound. The
threshold is one named constant, tuned from real-world reports after release.
Small is downloaded only when chosen, so slow PCs download 45 MB, not 190 MB.

### Settings

- `model`: `""` (not chosen yet) | `tiny` | `small` | `medium`.
- `onboarded`: `false` until the user finishes onboarding.
- `--model` overrides the model for one run without saving.
- Behavior page: **Speech model** combo (Tiny — faster / Small — more
  accurate). Choosing a model that is not downloaded shows a progress bar under
  the combo, then the engine reloads (`EchoLineApp.reload_engine()`). If the
  download fails, the setting reverts and a notice explains why.

### Onboarding window

`Onboarding.qml`, backed by a `Setup` QObject (`echoline/ui/onboarding.py`),
is shown at startup when `onboarded` is false. The overlay stays hidden until
step 2.

1. **Getting ready** — welcome text; the download starts at once: Tiny
   progress → "Checking your PC…" → Small progress if chosen → model saved.
   Failure: "Couldn't download — check your internet connection" + **Retry**
   (resumes the partial file).
2. **Sound test** — the engine starts and the real overlay appears: "Play a
   video or music — captions appear at the bottom of your screen." The latest
   caption is echoed in the window too.
3. **Theme** — one card per preset; clicking applies it to the live overlay.
   **Finish** (with a one-line tip about the hotkeys and tray icon) saves
   `onboarded` and closes the window.

Closing the window before the model is ready quits the app; after that,
closing counts as Finish. When `onboarded` is true but the chosen model is
missing or damaged, the window opens in **repair mode**: only Getting ready
(download, no hardware check), then it closes and captions start.

### Single instance

`echoline/instance.py`: a `QLocalServer` named per Windows user. At startup
the app first tries to connect; if a server answers it sends `show` and exits
with code 0. The running instance shows the overlay and raises the onboarding
window if it is open. A stale server name left by a crash is cleared with
`QLocalServer.removeServer` before listening.

## Customization (all four groups ship in v1)

| Group | Settings |
|---|---|
| Text style | Font family, size, weight, color, outline / shadow, visible line count (1–3) |
| Background & shape | Background color and opacity, corner radius, width, optional blur-behind |
| Position & behavior | Drag and resize, snap presets (top / center / bottom), click-through, auto-hide when silent, always-on-top |
| Theme presets | Classic CC, Netflix, Minimal, High-contrast |

## Latency budget

| Stage | Target |
|---|---|
| Audio capture block | 20–50 ms |
| Engine (Moonshine Small / Tiny) | ~150 ms / ~50 ms |
| Signal + QML render | < 16 ms |
| **End to end (p50)** | **< 300 ms** |

Latency is measured, not assumed: the existing `PerformanceMonitor` is wired
into the live pipeline (audio block received → engine event → frame shown), and
a debug overlay shows p50/p95.

## Error handling

| Situation | Behavior |
|---|---|
| No output/input device, or device removed | Status pill; retry and reattach automatically when a device appears |
| Default output device changes | Loopback source reopens on the new device |
| Model missing or checksum mismatch | Open onboarding in repair mode (getting-ready step only) and re-download |
| Engine thread crashes | Log it, restart the engine, show a brief status |
| Engine falls behind real time | Drop the oldest audio, show "Lagging", suggest the Tiny model |
| Second launch | Focus the existing instance and exit |
| Corrupt settings file | Back it up, load defaults, notify once |

## Testing

- **Unit (pytest):** `CaptionModel`, settings load/save/validation, theme
  application, `ModelManager` (progress, downloaded check, hardware-check
  choice) against a faked moonshine downloader, engine adapters with fake recognizers, backlog dropping, audio
  resampling and downmixing.
- **Pipeline:** fake `AudioSource` → real engine adapter with a fake model →
  `CaptionModel` events, asserting order and bounded memory.
- **QML smoke:** load every QML file on the offscreen platform and fail on QML
  warnings or errors.
- **Benchmark command:** `python -m echoline.bench` reports WER and latency per
  engine and model on reference clips, using the `metrics` package.
- **Manual checklist** per release: fresh Windows install, Bluetooth headset
  switch, click-through, hotkeys, one-hour soak.

## Milestones

Each milestone gets its own implementation plan and PR.

| | Milestone | Done when |
|---|---|---|
| M0 | Engine verification | `echoline.bench` compares Moonshine Tiny / Small and Vosk on this machine; the Moonshine choice and Small/Tiny threshold are confirmed with data |
| M1 | Core pipeline | Code moves from the top-level `audio/`, `transcription/`, `ui/`, `utils/` folders into the `echoline/` package; loopback → Moonshine → `CaptionModel` → rolling-mode QML overlay replaces the Widgets UI; latency is measured live |
| M2 | Customization | Settings persistence, settings window, all four groups, subtitle mode |
| M3 | Controls | Tray icon, hover bar, global hotkeys, click-through, auto-hide |
| M4 | First-run setup | `ModelManager`, hardware check, onboarding flow, sound test |
| M5 | Packaging | PyInstaller build, Inno Setup installer, portable zip, GitHub Actions release workflow |

After v1: the single-page download website, as its own sub-project with its own spec.

## Out of scope for v1

See [ROADMAP.md](../../ROADMAP.md).

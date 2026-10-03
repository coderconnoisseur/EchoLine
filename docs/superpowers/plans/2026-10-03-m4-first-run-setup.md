# M4 First-Run Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A fresh install goes from first launch to live captions by clicking through a three-step onboarding window that downloads the right model for the PC; second launches focus the running app; users can switch Tiny/Small in Settings.

**Architecture:** `echoline/models.py` wraps moonshine-voice's own resumable, checksummed downloader (models under `%LOCALAPPDATA%\EchoLine\models`) and holds the hardware check. A `Setup` QObject (`echoline/ui/onboarding.py`) runs downloads on a worker thread and drives both `Onboarding.qml` and the Settings model combo. `echoline/instance.py` is a per-user `QLocalServer` guard. `__main__` decides run / setup / repair at startup.

**Tech Stack:** Python 3.11, PySide6 6.11 (QML, QtNetwork), moonshine-voice 0.1.5, pytest (offscreen Qt).

**Spec:** `docs/superpowers/specs/2026-10-03-echoline-v1-design.md` — section "First-run setup (M4)".

## Global Constraints

- Run everything with `D:/EchoLine/.venv/Scripts/python` (tests: `-m pytest -q`).
- Default hotkeys: **Ctrl+Alt+Shift+C / P / T**.
- Models dir: `%LOCALAPPDATA%\EchoLine\models`; model names `tiny`, `small`, `medium` (`medium` via `--model` only).
- Hardware check: first 15 s of bundled `two_cities.wav`, 50 ms chunks, Small iff Tiny RTF ≤ 0.25.
- Copy: error text "Couldn't download — check your internet connection".
- Never import PySide6 before `preload_native_library()` in entry points.
- New files must be `git add`ed before the full suite (`tests/test_repository.py`).
- Commits: small, "why" in body, no mention of Claude/AI, no Co-Authored-By.

## Review Focus

1. Offline on first run → error + Retry, no crash, Retry restarts the download (Task 5 test `test_failed_download_shows_error_and_retry_restarts`).
2. Closing onboarding before the model is ready → app quits; after ready → counts as Finish (Task 5 tests).
3. Model files deleted after onboarding → startup goes to repair, not a broken engine (Task 8 `test_startup_mode`).
4. Two model switches / reloads in quick succession → exactly one worker, old engine closed (Task 6 `test_overlapping_reloads_keep_one_worker`).
5. Second launch while onboarding is open → raises onboarding instead of showing an empty overlay (Task 6 `test_bring_to_front_prefers_onboarding`).

---

### Task 1: Ctrl+Alt+Shift hotkey defaults

**Files:**
- Modify: `echoline/settings/model.py:34-36`
- Modify: `tests/test_settings_model.py:88,97`, `tests/test_settings_window.py:145-146`, `tests/test_echoline_app.py:368`
- Modify: `README.md:19,58-62`

- [ ] **Step 1: Update the expectations in tests first**

`tests/test_settings_model.py:88` →
```python
    assert (s.hotkey_show_hide, s.hotkey_pause, s.hotkey_click_through) == (
        "Ctrl+Alt+Shift+C", "Ctrl+Alt+Shift+P", "Ctrl+Alt+Shift+T")
```
`:97` → `assert s.hotkey_pause == "Ctrl+Alt+Shift+P"`.
`tests/test_settings_window.py:145-146` → `"Ctrl+Alt+Shift+P"` / `"Ctrl+Alt+Shift+C"`.
`tests/test_echoline_app.py:368` → `assert "Ctrl+Alt+Shift+T" in ...`.

- [ ] **Step 2: Run, expect 4 failures**

Run: `.venv/Scripts/python -m pytest -q tests/test_settings_model.py tests/test_settings_window.py tests/test_echoline_app.py`

- [ ] **Step 3: Change defaults**

```python
    hotkey_show_hide: str = "Ctrl+Alt+Shift+C"
    hotkey_pause: str = "Ctrl+Alt+Shift+P"
    hotkey_click_through: str = "Ctrl+Alt+Shift+T"
```
README: replace `Ctrl+Alt+C/P/T` with `Ctrl+Alt+Shift+C/P/T` (lines 19, 58–62).

- [ ] **Step 4: Run the same tests, expect pass. Commit** — "Default hotkeys to Ctrl+Alt+Shift" (body: AltGr = Ctrl+Alt on many layouts; Polish Programmer AltGr+C types ć; saved settings keep their keys).

---

### Task 2: `model` and `onboarded` settings

**Files:** Modify `echoline/settings/model.py`; Test `tests/test_settings_model.py`

**Produces:** `Settings.model: str = ""` (choices `"", "tiny", "small", "medium"`), `Settings.onboarded: bool = False`.

- [ ] **Step 1: Failing test**

```python
def test_model_and_onboarding_fields_validate():
    assert Settings().model == "" and Settings().onboarded is False
    s = validate({"model": "small", "onboarded": True})
    assert (s.model, s.onboarded) == ("small", True)
    s = validate({"model": "huge", "onboarded": "yes"})
    assert (s.model, s.onboarded) == ("", False)
```

- [ ] **Step 2: Run → FAIL (no field `model`).**
- [ ] **Step 3: Implement** — add fields after `hotkey_click_through`:
```python
    model: str = ""            # "" until first-run setup picks one
    onboarded: bool = False
```
and `"model": ("", "tiny", "small", "medium")` to `CHOICES`.
- [ ] **Step 4: Run → PASS. Commit** — "Remember the chosen model and finished onboarding".

---

### Task 3: Model files (`echoline/models.py`)

**Files:** Create `echoline/models.py`; Modify `echoline/engine/moonshine_engine.py:29-38`; Test `tests/test_models.py`

**Produces:**
- `models_dir() -> Path`
- `arch(name: str) -> ModelArch`
- `is_downloaded(name: str, root: Path | None = None) -> bool`
- `download(name: str, on_progress=None, root: Path | None = None) -> str` (blocking; raises on failure)
- `MoonshineEngine.load(model_arch, update_interval=0.1, options=None, cache_root=None)`

- [ ] **Step 1: Failing tests**

```python
import moonshine_voice

from echoline import models


def test_models_live_under_local_appdata(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert models.models_dir() == tmp_path / "EchoLine" / "models"


def test_is_downloaded_needs_every_file_at_full_size(tmp_path):
    files = models._files("tiny", tmp_path)
    assert files and not models.is_downloaded("tiny", tmp_path)
    for path, size in files:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.truncate(size)            # sparse: instant even for 40 MB
    assert models.is_downloaded("tiny", tmp_path)

    path, size = files[0]
    with open(path, "wb") as f:
        f.truncate(size - 1)            # a cut-off download
    assert not models.is_downloaded("tiny", tmp_path)


def test_download_uses_our_folder_and_reports_progress(monkeypatch, tmp_path):
    calls = []

    def fake(language, model_arch, cache_root=None, on_progress=None):
        calls.append((language, model_arch, cache_root))
        on_progress(0.5, "encoder.ort")
        return "model-path", model_arch

    monkeypatch.setattr(moonshine_voice, "get_model_for_language", fake)
    seen = []
    assert models.download("small", seen.append, root=tmp_path) == "model-path"
    assert calls == [("en", models.arch("small"), tmp_path)]
    assert seen == [0.5]
```

- [ ] **Step 2: Run** `pytest -q tests/test_models.py` → FAIL (no module).

- [ ] **Step 3: Implement `echoline/models.py`**

```python
"""Speech model files: where they live, whether they are complete, fetching them.

moonshine-voice already downloads with resume, size + CRC32C checks and atomic
rename; this module only points it at EchoLine's folder and adapts progress.
"""
import os
from pathlib import Path


def models_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "EchoLine" / "models"


def arch(name):
    from moonshine_voice import ModelArch

    return {"tiny": ModelArch.TINY_STREAMING, "small": ModelArch.SMALL_STREAMING,
            "medium": ModelArch.MEDIUM_STREAMING}[name]


def _files(name, root):
    """(path, expected size) for each file of the model, from the native manifest (offline)."""
    from moonshine_voice.download import _primary_stt_group, find_model_info

    group = _primary_stt_group(find_model_info("en", arch(name)))
    base = Path(root) / group["base_url"].replace("https://", "")
    return [(base / f["name"], f.get("size")) for f in group["files"]]


def is_downloaded(name, root=None) -> bool:
    return all(path.is_file() and (size is None or path.stat().st_size == size)
               for path, size in _files(name, root or models_dir()))


def download(name, on_progress=None, root=None) -> str:
    """Fetch (or resume) the model; blocks, so call it off the GUI thread."""
    import moonshine_voice

    progress = (lambda fraction, _file: on_progress(fraction)) if on_progress else None
    path, _ = moonshine_voice.get_model_for_language(
        "en", arch(name), cache_root=root or models_dir(), on_progress=progress)
    return path
```

`MoonshineEngine.load`: add `cache_root=None` and pass it:
```python
    def load(cls, model_arch, update_interval=0.1, options=None, cache_root=None):
        from moonshine_voice import Transcriber, get_model_for_language

        path, arch = get_model_for_language("en", model_arch, cache_root=cache_root)
```

- [ ] **Step 4: Run → PASS; also `pytest -q tests/test_engine_moonshine.py`. Commit** (git add new files) — "Keep speech models in EchoLine's own folder" (body: reuse moonshine's resumable checksummed downloader rather than a second one; manifest check works offline).

---

### Task 4: Hardware check

**Files:** Modify `echoline/models.py`; Test `tests/test_models.py`

**Produces:** `SMALL_IF_TINY_RTF_AT_MOST = 0.25`, `check_clip(seconds=15) -> np.ndarray` (16 kHz float32), `measure_rtf(engine, samples) -> float`, `choose_model(tiny_rtf) -> str`, `check_hardware(load=None) -> str`.

- [ ] **Step 1: Failing tests**

```python
import time

import numpy as np

from echoline.engine.base import SAMPLE_RATE


def test_choose_model_takes_small_only_when_tiny_has_lots_of_headroom():
    assert models.choose_model(0.20) == "small"
    assert models.choose_model(0.25) == "small"
    assert models.choose_model(0.26) == "tiny"
    assert models.choose_model(0.77) == "tiny"     # this Ryzen 5 3550H


class SlowEngine:
    def __init__(self, per_chunk_s):
        self.per_chunk_s, self.fed, self.flushed, self.closed = per_chunk_s, 0, False, False

    def feed(self, samples):
        self.fed += len(samples)
        time.sleep(self.per_chunk_s)
        return []

    def flush(self):
        self.flushed = True
        return []

    def close(self):
        self.closed = True


def test_measure_rtf_feeds_everything_and_times_it():
    engine = SlowEngine(0.01)                      # 10 ms per 50 ms chunk ≈ 0.2
    samples = np.zeros(SAMPLE_RATE, np.float32)    # 1 s → 20 chunks
    rtf = models.measure_rtf(engine, samples)
    assert engine.fed == SAMPLE_RATE and engine.flushed
    assert 0.18 <= rtf < 0.5


def test_check_clip_is_15_seconds_of_16khz_audio():
    clip = models.check_clip()
    assert clip.dtype == np.float32 and len(clip) == 15 * SAMPLE_RATE


def test_check_hardware_closes_the_engine(monkeypatch):
    engine = SlowEngine(0)
    monkeypatch.setattr(models, "check_clip", lambda seconds=15: np.zeros(1600, np.float32))
    assert models.check_hardware(load=lambda: engine) == "small"
    assert engine.closed
```

- [ ] **Step 2: Run → FAIL (no attribute).**

- [ ] **Step 3: Implement (append to `models.py`, add `import time`, `import numpy as np`)**

```python
# Small costs ~1.9x Tiny (M0 bench: RTF 0.88 vs 0.47), so Tiny at <= 0.25 keeps Small under 0.5.
# ponytail: calibrated on one Ryzen 5 3550H; retune from real-world reports.
SMALL_IF_TINY_RTF_AT_MOST = 0.25


def choose_model(tiny_rtf) -> str:
    return "small" if tiny_rtf <= SMALL_IF_TINY_RTF_AT_MOST else "tiny"


def check_clip(seconds=15):
    """The first `seconds` of moonshine's bundled speech clip, as 16 kHz mono float32."""
    from moonshine_voice import get_assets_path, load_wav_file

    from .audio.convert import StreamConverter

    audio, rate = load_wav_file(os.path.join(get_assets_path(), "two_cities.wav"))
    samples = np.asarray(audio[: seconds * rate], dtype=np.float32)
    converter = StreamConverter(rate, 1)
    return np.concatenate([converter.process(samples), converter.process(np.zeros(rate, np.float32))])[
        : seconds * 16000]


def measure_rtf(engine, samples) -> float:
    """Processing time / audio time, feeding 50 ms chunks as fast as the engine takes them."""
    from .engine.base import SAMPLE_RATE

    chunk = SAMPLE_RATE // 20
    start = time.perf_counter()
    for i in range(0, len(samples), chunk):
        engine.feed(samples[i:i + chunk])
    engine.flush()
    return (time.perf_counter() - start) / (len(samples) / SAMPLE_RATE)


def check_hardware(load=None) -> str:
    """Time Tiny on the bundled clip and pick the model this PC can keep up with."""
    if load is None:
        from .engine.moonshine_engine import MoonshineEngine

        load = lambda: MoonshineEngine.load(arch("tiny"), cache_root=models_dir())  # noqa: E731
    engine = load()
    try:
        return choose_model(measure_rtf(engine, check_clip()))
    finally:
        engine.close()
```

(The zero-padding flush pushes soxr's tail out so the clip is exactly 15 s.)

- [ ] **Step 4: Run → PASS. Optional real check:** `.venv/Scripts/python -c "from echoline.engine.moonshine_engine import preload_native_library as p; p(); from echoline import models; print(models.measure_rtf(__import__('echoline.engine.moonshine_engine', fromlist=['x']).MoonshineEngine.load(models.arch('tiny')), models.check_clip()))"` — record the value in the ledger. **Commit** — "Pick Tiny or Small from a timed Tiny run".

---

### Task 5: `Setup` controller

**Files:** Create `echoline/ui/onboarding.py`; Test `tests/test_onboarding.py`

**Consumes:** `models.download/check_hardware/is_downloaded` (Tasks 3–4). From the app object: `settings_store`, `status`, `start()`, `set_visible(bool)`, `reload_engine()`, `close_onboarding()`, `quit()` (Task 6 adds the missing ones to `EchoLineApp`; tests use a fake).

**Produces:** `Setup(app, download=None, check_hardware=None, is_downloaded=None)` with QML properties `step:int` (0 getting ready, 1 sound test, 2 theme), `phase:str` (`idle|downloading|checking|ready|error`), `progress:float`, `repair:bool`, one notify signal `changed`; methods `begin(repair_model=None)`; slots `retry()`, `nextStep()`, `finish()`, `windowClosed()`, `chooseModel(str)`.

- [ ] **Step 1: Failing tests** (`tests/test_onboarding.py`)

```python
import threading
import time

import pytest
from PySide6.QtGui import QGuiApplication

from echoline.settings.model import Settings
from echoline.settings.store import SettingsStore
from echoline.ui.onboarding import Setup

app = QGuiApplication.instance()


def wait_until(condition, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    return False


class FakeStatus:
    notice = ""

    def set_notice(self, text, ms=6000):
        self.notice = text


class FakeApp:
    def __init__(self, tmp_path, **settings):
        self.settings_store = SettingsStore(Settings(**settings), tmp_path / "settings.json")
        self.status = FakeStatus()
        self.calls = []

    def __getattr__(self, name):          # start, set_visible, reload_engine, close_onboarding, quit
        return lambda *args: self.calls.append((name, *args))


class Downloads:
    def __init__(self, fail=False):
        self.fail, self.names = fail, []

    def __call__(self, name, on_progress):
        self.names.append(name)
        on_progress(0.5)
        if self.fail:
            raise OSError("offline")
        return "path"


def make(tmp_path, downloads=None, choice="tiny", downloaded=False, **settings):
    fake = FakeApp(tmp_path, **settings)
    setup = Setup(fake, download=downloads or Downloads(), check_hardware=lambda: choice,
                  is_downloaded=lambda name: downloaded)
    return fake, setup


def test_first_run_downloads_tiny_checks_and_starts(tmp_path):
    fake, setup = make(tmp_path)
    setup.begin()
    assert wait_until(lambda: setup.property("phase") == "ready")
    assert fake.settings_store.settings.model == "tiny"
    assert ("start",) in fake.calls
    assert setup.property("progress") == 0.5


def test_fast_pc_also_downloads_small(tmp_path):
    downloads = Downloads()
    fake, setup = make(tmp_path, downloads, choice="small")
    setup.begin()
    assert wait_until(lambda: setup.property("phase") == "ready")
    assert downloads.names == ["tiny", "small"]
    assert fake.settings_store.settings.model == "small"


def test_failed_download_shows_error_and_retry_restarts(tmp_path):
    downloads = Downloads(fail=True)
    fake, setup = make(tmp_path, downloads)
    setup.begin()
    assert wait_until(lambda: setup.property("phase") == "error")
    downloads.fail = False
    setup.retry()
    assert wait_until(lambda: setup.property("phase") == "ready")
    assert downloads.names == ["tiny", "tiny"]


def test_steps_advance_only_once_ready_and_show_captions(tmp_path):
    fake, setup = make(tmp_path)
    setup.begin()
    setup.nextStep()
    assert setup.property("step") == 0          # still downloading
    assert wait_until(lambda: setup.property("phase") == "ready")
    setup.nextStep()
    assert setup.property("step") == 1 and ("set_visible", True) in fake.calls
    setup.nextStep()
    assert setup.property("step") == 2


def test_finish_saves_onboarded_and_closes(tmp_path):
    fake, setup = make(tmp_path)
    setup.finish()
    assert fake.settings_store.settings.onboarded is True
    assert (tmp_path / "settings.json").exists()
    assert ("close_onboarding",) in fake.calls
    setup.windowClosed()                         # the close that finish() caused
    assert ("quit",) not in fake.calls


def test_closing_before_ready_quits(tmp_path):
    fake, setup = make(tmp_path, Downloads(fail=True))
    setup.begin()
    assert wait_until(lambda: setup.property("phase") == "error")
    setup.windowClosed()
    assert ("quit",) in fake.calls


def test_closing_after_ready_counts_as_finish(tmp_path):
    fake, setup = make(tmp_path)
    setup.begin()
    assert wait_until(lambda: setup.property("phase") == "ready")
    setup.windowClosed()
    assert fake.settings_store.settings.onboarded is True and ("quit",) not in fake.calls


def test_repair_downloads_the_named_model_then_closes_and_starts(tmp_path):
    downloads = Downloads()
    fake, setup = make(tmp_path, downloads, onboarded=True, model="small")
    setup.begin(repair_model="small")
    assert setup.property("repair") is True
    assert wait_until(lambda: ("start",) in fake.calls)
    assert downloads.names == ["small"]
    assert ("close_onboarding",) in fake.calls and ("set_visible", True) in fake.calls


def test_choose_downloaded_model_switches_at_once(tmp_path):
    fake, setup = make(tmp_path, downloaded=True, onboarded=True, model="tiny")
    setup.chooseModel("small")
    assert fake.settings_store.settings.model == "small"
    assert ("reload_engine",) in fake.calls


def test_choose_missing_model_downloads_first(tmp_path):
    downloads = Downloads()
    fake, setup = make(tmp_path, downloads, onboarded=True, model="tiny")
    setup.chooseModel("small")
    assert fake.settings_store.settings.model == "tiny"       # not until the files are here
    assert wait_until(lambda: ("reload_engine",) in fake.calls)
    assert fake.settings_store.settings.model == "small" and setup.property("phase") == "idle"


def test_failed_switch_keeps_the_old_model_and_says_why(tmp_path):
    fake, setup = make(tmp_path, Downloads(fail=True), onboarded=True, model="tiny")
    setup.chooseModel("small")
    assert wait_until(lambda: setup.property("phase") == "idle" and fake.status.notice)
    assert fake.settings_store.settings.model == "tiny"
    assert ("reload_engine",) not in fake.calls
```

- [ ] **Step 2: Run** `pytest -q tests/test_onboarding.py` → FAIL (no module).

- [ ] **Step 3: Implement `echoline/ui/onboarding.py`**

```python
import threading
import traceback

from PySide6.QtCore import Property, QObject, Qt, Signal, Slot

from .. import models

GETTING_READY, SOUND_TEST, THEME = range(3)
DOWNLOAD_FAILED = "Couldn't download — check your internet connection"


class Setup(QObject):
    """First-run setup and model switching: fetch a model with progress, then start captions."""

    changed = Signal()
    _phase_from_worker = Signal(str)
    _progress_from_worker = Signal(float)
    _succeeded = Signal(str)
    _failed = Signal()

    def __init__(self, app, download=None, check_hardware=None, is_downloaded=None):
        super().__init__()
        self._app = app
        self._download = download or models.download
        self._check_hardware = check_hardware or models.check_hardware
        self._is_downloaded = is_downloaded or models.is_downloaded
        self._step, self._phase, self._progress = GETTING_READY, "idle", 0.0
        self._mode = None            # "setup" | "repair" | "switch"
        self._finished = False
        self._repair_model = None
        self._phase_from_worker.connect(self._set_phase, Qt.QueuedConnection)
        self._progress_from_worker.connect(self._set_progress, Qt.QueuedConnection)
        self._succeeded.connect(self._on_ready, Qt.QueuedConnection)
        self._failed.connect(self._on_failed, Qt.QueuedConnection)

    step = Property(int, lambda self: self._step, notify=changed)
    phase = Property(str, lambda self: self._phase, notify=changed)
    progress = Property(float, lambda self: self._progress, notify=changed)
    repair = Property(bool, lambda self: self._mode == "repair", notify=changed)

    @Slot(str)
    def _set_phase(self, phase):
        self._phase = phase
        self.changed.emit()

    @Slot(float)
    def _set_progress(self, fraction):
        self._progress = fraction
        self.changed.emit()

    def _run(self, job):
        self._progress = 0.0
        self._set_phase("downloading")

        def work():
            try:
                self._succeeded.emit(job())
            except Exception:
                traceback.print_exc()
                self._failed.emit()

        threading.Thread(target=work, name="model-setup", daemon=True).start()

    def _fetch(self, name):
        self._download(name, self._progress_from_worker.emit)
        return name

    def _first_run(self):
        self._fetch("tiny")
        self._phase_from_worker.emit("checking")
        model = self._check_hardware()
        if model != "tiny":
            self._progress_from_worker.emit(0.0)
            self._phase_from_worker.emit("downloading")
            self._fetch(model)
        return model

    def begin(self, repair_model=None):
        """Start first-run setup, or (repair_model) re-fetch a missing model."""
        self._mode = "repair" if repair_model else "setup"
        self._repair_model = repair_model
        self._run(lambda: self._fetch(repair_model) if repair_model else self._first_run())

    @Slot(str)
    def _on_ready(self, model):
        self._app.settings_store.setValue("model", model)
        if self._mode == "switch":
            self._set_phase("idle")
            self._app.reload_engine()
            return
        self._set_phase("ready")
        if self._mode == "repair":
            self._finished = True
            self._app.close_onboarding()
            self._app.set_visible(True)
        self._app.start()

    @Slot()
    def _on_failed(self):
        if self._mode == "switch":
            self._set_phase("idle")
            self._app.status.set_notice(DOWNLOAD_FAILED)
        else:
            self._set_phase("error")

    @Slot()
    def retry(self):
        if self._phase == "error":
            self.begin(self._repair_model)

    @Slot()
    def nextStep(self):
        if self._step == GETTING_READY and self._phase != "ready":
            return
        if self._step == GETTING_READY:
            self._app.set_visible(True)          # the sound test uses the real overlay
        self._step = min(self._step + 1, THEME)
        self.changed.emit()

    @Slot()
    def finish(self):
        if self._finished:
            return
        self._finished = True
        self._app.settings_store.setValue("onboarded", True)
        self._app.settings_store.save_now()
        self._app.close_onboarding()

    @Slot()
    def windowClosed(self):
        if self._finished:
            return
        if self._mode == "setup" and self._phase == "ready":
            self.finish()
        else:
            self._app.quit()                     # nothing to caption with yet

    @Slot(str)
    def chooseModel(self, name):
        busy = self._phase in ("downloading", "checking")
        onboarding = self._mode in ("setup", "repair") and not self._finished
        if busy or onboarding or name == self._app.settings_store.settings.model:
            return
        if self._is_downloaded(name):
            self._app.settings_store.setValue("model", name)
            self._app.reload_engine()
            return
        self._mode = "switch"
        self._run(lambda: self._fetch(name))
```

- [ ] **Step 4: Run → PASS. Commit** (git add) — "Drive first-run setup and model switches from one controller" (body: one place owns download threads and phases so onboarding and Settings never race; worker results hop to the GUI thread through queued signals).

---

### Task 6: App support — engine reload, onboarding window, bring to front

**Files:** Modify `echoline/app.py`; Create `echoline/ui/qml/Onboarding.qml`; Test `tests/test_echoline_app.py`, `tests/test_onboarding_window.py`

**Consumes:** `Setup` (Task 5).
**Produces on `EchoLineApp`:** `__init__(..., model_ops=None)` (dict of `download`/`check_hardware`/`is_downloaded` forwarded to `Setup`), `self.setup` (also QML context property `setup`), `reload_engine()`, `run_setup(repair_model=None)`, `open_onboarding()`, `close_onboarding()`, `bring_to_front()`, `onboarding_window`.

- [ ] **Step 1: Failing app tests** (append to `tests/test_echoline_app.py`)

```python
class ClosingEngine(EchoEngine):
    closed = 0

    def close(self):
        ClosingEngine.closed += 1


def test_reload_engine_swaps_in_a_fresh_engine(tmp_path):
    engines = []

    def factory():
        engines.append(ClosingEngine())
        return engines[-1]

    source = FakeSource()
    echoline = EchoLineApp(lambda kind: source, factory, SettingsStore(Settings(), tmp_path / "s.json"))
    echoline.start()
    assert wait_until(lambda: echoline.worker is not None)
    ClosingEngine.closed = 0
    echoline.reload_engine()
    assert wait_until(lambda: len(engines) == 2 and echoline.worker is not None)
    assert echoline.worker._engine is engines[1] and ClosingEngine.closed == 1
    echoline.shutdown()


def test_overlapping_reloads_keep_one_worker(tmp_path):
    engines = []

    def factory():
        time.sleep(0.05)
        engines.append(ClosingEngine())
        return engines[-1]

    echoline = EchoLineApp(lambda kind: FakeSource(), factory, SettingsStore(Settings(), tmp_path / "s.json"))
    ClosingEngine.closed = 0
    echoline.start()
    echoline.reload_engine()
    assert wait_until(lambda: len(engines) == 2)
    wait_until(lambda: False, timeout=0.2)
    assert echoline.worker._engine is engines[-1] and ClosingEngine.closed == 1
    echoline.shutdown()


def test_reload_while_paused_stays_paused(running):
    echoline, source = running
    echoline.set_paused(True)
    source.on_audio = None
    echoline.reload_engine()
    assert wait_until(lambda: echoline.worker is not None)
    wait_until(lambda: False, timeout=0.1)
    assert echoline.paused and echoline.status.property("state") == "paused"
    assert source.on_audio is None               # the source was not restarted


def test_bring_to_front_prefers_onboarding(tmp_path):
    echoline = EchoLineApp(lambda kind: FakeSource(), EchoEngine, SettingsStore(Settings(), tmp_path / "s.json"),
                           model_ops={"download": lambda name, cb: threading.Event().wait(),
                                      "check_hardware": lambda: "tiny", "is_downloaded": lambda name: False})
    echoline.run_setup()
    assert not echoline.visible and echoline.onboarding_window.isVisible()
    echoline.bring_to_front()
    assert not echoline.visible                  # nothing to caption yet; raise the setup window
    echoline.close_onboarding()
    echoline.bring_to_front()
    assert echoline.visible
    echoline.shutdown()
```
(add `import threading` at top of the test file.)

`tests/test_onboarding_window.py`:
```python
import time

from PySide6.QtCore import QObject
from PySide6.QtGui import QGuiApplication

from echoline.app import EchoLineApp
from echoline.engine.base import Partial
from echoline.settings.model import Settings
from echoline.settings.store import SettingsStore

app = QGuiApplication.instance()


class FakeSource:
    name = "System audio"

    def start(self, on_audio, on_status):
        on_status("listening")

    def stop(self):
        pass


class EchoEngine:
    def feed(self, samples):
        return [Partial(0, "hi")]

    def flush(self):
        return []


def wait_until(condition, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    return False


def test_onboarding_walks_through_all_steps_without_warnings(tmp_path):
    store = SettingsStore(Settings(), tmp_path / "settings.json")
    echoline = EchoLineApp(lambda kind: FakeSource(), EchoEngine, store,
                           model_ops={"download": lambda name, cb: cb(1.0), "check_hardware": lambda: "tiny",
                                      "is_downloaded": lambda name: True})
    warnings = []
    echoline.qml.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))
    window = echoline.run_setup()
    find = lambda name: window.findChild(QObject, name)  # noqa: E731

    assert window.objectName() == "onboardingWindow"
    assert wait_until(lambda: find("nextButton").property("enabled"))
    find("nextButton").clicked.emit()
    assert echoline.visible and find("echoLabel") is not None
    find("soundNextButton").clicked.emit()
    find("theme High contrast").clicked.emit()
    assert store.settings.theme == "High contrast"
    find("finishButton").clicked.emit()
    assert store.settings.onboarded and not window.isVisible()
    assert warnings == []
    echoline.shutdown()
```

- [ ] **Step 2: Run** both files → FAIL (`model_ops` unexpected, no `reload_engine`).

- [ ] **Step 3: Implement in `echoline/app.py`**

Imports: `from .ui.onboarding import Setup`.

`__init__` signature: `def __init__(self, source_factory, engine_factory, settings_store, show_latency=False, settings_reset=False, model_ops=None):`; add `self._engine = None`, `self.onboarding_window = None` near `self.settings_window = None`; right after `self.window = load_overlay(...)`:
```python
        self.setup = Setup(self, **(model_ops or {}))
        self.qml.rootContext().setContextProperty("setup", self.setup)
```

Replace `_on_engine_ready` and add helpers:
```python
    def _on_engine_ready(self, engine):
        if self._closed:
            self._close_engine(engine)       # finished loading after quit
            return
        self._stop_engine()                  # a reload overtook an earlier load
        self._engine = engine
        self.worker = EngineWorker(
            engine,
            on_events=lambda events, captured_at: self.bridge.events.emit(events, captured_at),
            on_lagging=lambda lagging: self.bridge.status.emit("lagging" if lagging else "caught-up"))
        self.worker.start()
        if self.paused:
            self.status.set_state("paused")
        else:
            self._start_source()

    @staticmethod
    def _close_engine(engine):
        close = getattr(engine, "close", None)
        if close is not None:
            close()

    def _stop_engine(self):
        if self.worker is None:
            return
        self.source.stop()
        self.worker.stop()
        self.worker = None
        self._close_engine(self._engine)
        self._engine = None

    def reload_engine(self):
        """Load the engine again, e.g. after the model setting changed."""
        self._stop_engine()
        if not self.paused:
            self.status.set_state("loading")
        threading.Thread(target=self._load_engine, name="engine-load", daemon=True).start()
```

`set_paused`: it returns early when `self.worker is None` — keep as is.

Window helpers (refactor `open_settings`):
```python
    def _load_window(self, file_name):
        before = len(self.qml.rootObjects())
        self.qml.load(QUrl.fromLocalFile(str(QML_DIR / file_name)))
        root = self.qml.rootObjects()[before]
        return shiboken6.wrapInstance(shiboken6.getCppPointer(root)[0], QQuickWindow)

    @staticmethod
    def _present(window):
        window.show()
        window.raise_()
        window.requestActivate()
        return window

    def open_settings(self):
        if self.settings_window is None:
            self.settings_window = self._load_window("Settings.qml")
        return self._present(self.settings_window)

    def open_onboarding(self):
        if self.onboarding_window is None:
            self.onboarding_window = self._load_window("Onboarding.qml")
        return self._present(self.onboarding_window)

    def close_onboarding(self):
        if self.onboarding_window is not None:
            self.onboarding_window.close()

    def run_setup(self, repair_model=None):
        """First run (or a missing model): hide captions and show the setup window."""
        self.set_visible(False)
        self.setup.begin(repair_model)
        return self.open_onboarding()

    def bring_to_front(self):
        """Another launch asked for us: raise setup if it is running, else show captions."""
        if self.onboarding_window is not None and self.onboarding_window.isVisible():
            self._present(self.onboarding_window)
        else:
            self.set_visible(True)
```

`shutdown`: keep `self.source.stop()`, replace the `if self.worker is not None: ...` block with `self._stop_engine()`, and close the onboarding window next to the settings window:
```python
        if self.onboarding_window is not None:
            self.onboarding_window.close()
```
Careful: closing onboarding during shutdown triggers `setup.windowClosed()` → `quit()`; harmless (`QCoreApplication.quit` while exiting). To keep it silent set `self.setup._finished = True` before closing.

- [ ] **Step 4: Create `echoline/ui/qml/Onboarding.qml`**

```qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: win
    objectName: "onboardingWindow"
    title: "Welcome to EchoLine"
    width: 480
    height: 400
    visible: false
    readonly property var s: settingsStore.values
    onClosing: setup.windowClosed()

    StackLayout {
        anchors.fill: parent
        anchors.margins: 24
        currentIndex: setup.step

        ColumnLayout {          // 0: getting ready
            spacing: 14
            Label { text: setup.repair ? "Fixing the speech model" : "Welcome to EchoLine"; font.pixelSize: 24; font.weight: Font.DemiBold }
            Label {
                text: "Live captions for anything playing on your PC. Everything runs on this computer — nothing you hear leaves it."
                wrapMode: Text.Wrap; Layout.fillWidth: true
            }
            Item { Layout.fillHeight: true }
            Label {
                objectName: "phaseLabel"
                Layout.fillWidth: true; wrapMode: Text.Wrap
                text: ({ downloading: "Downloading the speech model… " + Math.round(setup.progress * 100) + "%",
                         checking: "Checking how fast your PC is…",
                         error: "Couldn't download — check your internet connection",
                         ready: "All set." })[setup.phase] || ""
            }
            ProgressBar {
                Layout.fillWidth: true
                visible: setup.phase === "downloading" || setup.phase === "checking"
                indeterminate: setup.phase === "checking"
                value: setup.progress
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                Button { objectName: "retryButton"; text: "Retry"; visible: setup.phase === "error"; onClicked: setup.retry() }
                Button {
                    objectName: "nextButton"; text: "Next"; highlighted: true
                    visible: !setup.repair; enabled: setup.phase === "ready"
                    onClicked: setup.nextStep()
                }
            }
        }

        ColumnLayout {          // 1: sound test
            spacing: 14
            Label { text: "Sound test"; font.pixelSize: 24; font.weight: Font.DemiBold }
            Label {
                text: "Play a video or music — captions appear at the bottom of your screen."
                wrapMode: Text.Wrap; Layout.fillWidth: true
            }
            Label {
                objectName: "echoLabel"
                Layout.fillWidth: true; wrapMode: Text.Wrap; font.italic: !captions.latestText
                text: captions.latestText || "Waiting for sound…"
            }
            Item { Layout.fillHeight: true }
            Button {
                objectName: "soundNextButton"; text: "Next"; highlighted: true
                Layout.alignment: Qt.AlignRight
                onClicked: setup.nextStep()
            }
        }

        ColumnLayout {          // 2: theme
            spacing: 14
            Label { text: "Pick a look"; font.pixelSize: 24; font.weight: Font.DemiBold }
            GridLayout {
                columns: 2; columnSpacing: 10; rowSpacing: 10; Layout.fillWidth: true
                Repeater {
                    model: settingsStore.themeNames
                    delegate: Button {
                        required property string modelData
                        Layout.fillWidth: true; Layout.preferredHeight: 56
                        objectName: "theme " + modelData
                        text: modelData
                        highlighted: win.s.theme === modelData
                        onClicked: settingsStore.applyTheme(modelData)
                    }
                }
            }
            Label {
                Layout.fillWidth: true; wrapMode: Text.Wrap
                text: (win.s.hotkey_show_hide ? win.s.hotkey_show_hide + " shows or hides captions. " : "")
                      + "Everything else is in the tray icon and Settings."
            }
            Item { Layout.fillHeight: true }
            Button {
                objectName: "finishButton"; text: "Finish"; highlighted: true
                Layout.alignment: Qt.AlignRight
                onClicked: setup.finish()
            }
        }
    }
}
```

- [ ] **Step 5: Run** `pytest -q tests/test_echoline_app.py tests/test_onboarding_window.py tests/test_settings_window.py` → PASS (fix QML warnings if any). **Commit** (git add) — "Show the onboarding window and reload the engine on demand" (body: reload replaces a worker even if an earlier load lands late; pause survives a reload; a second launch raises setup instead of an empty overlay).

---

### Task 7: Speech model combo in Settings

**Files:** Modify `echoline/ui/qml/Settings.qml` (Behavior page, first row); Test `tests/test_settings_window.py`

**Consumes:** `setup.chooseModel(str)`, `setup.phase`, `setup.progress` (Task 5); `settings_window` fixture builds `EchoLineApp` — extend it with `model_ops={"download": ..., "check_hardware": lambda: "tiny", "is_downloaded": lambda name: True}` and `Settings(model="tiny", onboarded=True)`.

- [ ] **Step 1: Failing test**

```python
def test_model_box_switches_model_and_reloads(settings_window):
    echoline, window, store, warnings = settings_window
    box = find(window, "modelBox")
    reloads = []
    echoline.reload_engine = lambda: reloads.append(True)

    assert box.property("currentText") == "Tiny — faster"
    box.activated.emit(1)                         # Small

    assert store.settings.model == "small" and reloads == [True]
    assert find(window, "modelProgress").property("visible") is False
    assert warnings == []
```
(`echoline.reload_engine` is looked up at call time by `Setup`, so the instance override takes effect.)

Fixture change in `tests/test_settings_window.py`:
```python
    store = SettingsStore(Settings(model="tiny", onboarded=True), tmp_path / "settings.json")
    echoline = EchoLineApp(lambda kind: FakeSource(), EchoEngine, store,
                           model_ops={"download": lambda name, cb: None, "check_hardware": lambda: "tiny",
                                      "is_downloaded": lambda name: True})
```

- [ ] **Step 2: Run → FAIL (`modelBox` is None).**

- [ ] **Step 3: Implement** — first item in the Behavior `ColumnLayout`:
```qml
            Row2 {
                label: "Speech model"
                ComboBox {
                    objectName: "modelBox"
                    Layout.fillWidth: true
                    textRole: "text"; valueRole: "value"
                    model: [{ text: "Tiny — faster", value: "tiny" }, { text: "Small — more accurate", value: "small" }]
                    currentIndex: model.findIndex(item => item.value === win.s.model)
                    enabled: setup.phase !== "downloading" && setup.phase !== "checking"
                    onActivated: (index) => setup.chooseModel(model[index].value)
                }
            }
            ProgressBar {
                objectName: "modelProgress"
                Layout.fillWidth: true
                visible: setup.phase === "downloading"
                value: setup.progress
            }
```
- [ ] **Step 4: Run** `pytest -q tests/test_settings_window.py` → PASS. **Commit** — "Let people switch between Tiny and Small in Settings".

---

### Task 8: Single-instance guard and startup wiring

**Files:** Create `echoline/instance.py`; Modify `echoline/__main__.py`; Test `tests/test_instance.py`, `tests/test_main_entry.py`

**Consumes:** `models.arch/models_dir/is_downloaded`, `EchoLineApp.run_setup/bring_to_front/start`, `MoonshineEngine.load(..., cache_root=)`.
**Produces:** `server_name() -> str`, `notify_running(name) -> bool`, `InstanceServer(name)` with signal `shown`; `__main__.startup_mode(settings, model, is_downloaded) -> "run" | "setup" | "repair"`.

- [ ] **Step 1: Failing tests**

`tests/test_instance.py`:
```python
import time
import uuid

from PySide6.QtGui import QGuiApplication

from echoline.instance import InstanceServer, notify_running, server_name

app = QGuiApplication.instance()


def test_server_name_is_per_user():
    assert server_name().startswith("EchoLine-") and len(server_name()) > len("EchoLine-")


def test_second_launch_reaches_the_first():
    name = f"EchoLine-test-{uuid.uuid4().hex}"
    assert notify_running(name) is False         # nobody there yet
    server = InstanceServer(name)
    shown = []
    server.shown.connect(lambda: shown.append(True))

    assert notify_running(name) is True
    deadline = time.monotonic() + 3
    while not shown and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    assert shown == [True]
    server.close()
```

Append to `tests/test_main_entry.py`:
```python
from echoline.settings.model import Settings


def test_startup_mode():
    from echoline.__main__ import startup_mode

    have = lambda name: name == "tiny"                       # noqa: E731
    assert startup_mode(Settings(), "", have) == "setup"
    assert startup_mode(Settings(onboarded=False, model="tiny"), "tiny", have) == "setup"
    assert startup_mode(Settings(onboarded=True, model="tiny"), "tiny", have) == "run"
    assert startup_mode(Settings(onboarded=True, model="small"), "small", have) == "repair"   # files gone
    assert startup_mode(Settings(onboarded=True), "", have) == "setup"
```

- [ ] **Step 2: Run** → FAIL (no module / no function).

- [ ] **Step 3: Implement `echoline/instance.py`**

```python
import getpass

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket


def server_name():
    return f"EchoLine-{getpass.getuser()}"


def notify_running(name, timeout_ms=500) -> bool:
    """Ask an already-running EchoLine to show itself; False if none answered."""
    socket = QLocalSocket()
    socket.connectToServer(name)
    if not socket.waitForConnected(timeout_ms):
        return False
    socket.write(b"show")
    socket.waitForBytesWritten(timeout_ms)
    socket.disconnectFromServer()
    return True


class InstanceServer(QObject):
    """Listens for later launches; emits `shown` when one asks us to come forward."""

    shown = Signal()

    def __init__(self, name, parent=None):
        super().__init__(parent)
        # ponytail: two launches in the same instant can both start; acceptable for a tray app.
        QLocalServer.removeServer(name)          # left behind by a crash
        self._server = QLocalServer(self)
        self._server.setSocketOptions(QLocalServer.UserAccessOption)
        self._server.newConnection.connect(self._accept)
        self._server.listen(name)

    def _accept(self):
        while self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            socket.readyRead.connect(lambda s=socket: self._read(s))
            socket.disconnected.connect(socket.deleteLater)

    def _read(self, socket):
        if bytes(socket.readAll()).startswith(b"show"):
            self.shown.emit()

    def close(self):
        self._server.close()
```

- [ ] **Step 4: Rewire `echoline/__main__.py`**

```python
def startup_mode(settings, model, is_downloaded):
    """run: captions now; setup: full onboarding; repair: re-fetch a missing model."""
    if not settings.onboarded:
        return "setup"
    if model and is_downloaded(model):
        return "run"
    return "repair" if model else "setup"


def main(argv=None):
    parser = argparse.ArgumentParser(prog="echoline", description="Live captions for anything playing on your PC.")
    parser.add_argument("--model", choices=["tiny", "small", "medium"], default=None,
                        help="use this model for this run (default: the one chosen at setup)")
    parser.add_argument("--show-latency", action="store_true", help="show p50/p95 caption latency")
    args = parser.parse_args(argv)

    qt_app = QApplication(sys.argv[:1])
    qt_app.setQuitOnLastWindowClosed(False)   # hiding captions or closing settings must not quit
    qt_app.setApplicationName("EchoLine")

    from .instance import InstanceServer, notify_running, server_name
    if notify_running(server_name()):
        return 0                               # the running copy shows itself
    instance = InstanceServer(server_name())

    from .ui.style import use_fluent_style
    use_fluent_style()

    from . import models
    from .app import EchoLineApp
    from .audio.loopback import LoopbackSource
    from .audio.microphone import MicrophoneSource
    from .engine.moonshine_engine import MoonshineEngine
    from .settings.model import default_settings_path, load_settings
    from .settings.store import SettingsStore

    settings, was_reset = load_settings(default_settings_path())
    store = SettingsStore(settings, default_settings_path())

    def chosen_model():
        # ponytail: --model also wins after a switch in Settings; it is a developer flag.
        return args.model or store.settings.model

    def make_source(kind):
        return MicrophoneSource() if kind == "microphone" else LoopbackSource()

    def make_engine():
        return MoonshineEngine.load(models.arch(chosen_model()), cache_root=models.models_dir())

    echoline = EchoLineApp(make_source, make_engine, store,
                           show_latency=args.show_latency, settings_reset=was_reset)
    instance.shown.connect(echoline.bring_to_front)
    mode = startup_mode(store.settings, chosen_model(), models.is_downloaded)
    if mode == "run":
        echoline.start()
    else:
        echoline.run_setup(chosen_model() if mode == "repair" else None)
    try:
        return qt_app.exec()
    finally:
        echoline.shutdown()
        instance.close()
```
Remove `DEFAULT_MODEL` and the `ModelArch` import. Search for other users first: `grep -rn DEFAULT_MODEL echoline tests`.

- [ ] **Step 5: Run** `pytest -q tests/test_instance.py tests/test_main_entry.py` → PASS. **Commit** (git add) — "Run one EchoLine per user and start with setup when needed" (body: a second launch brings the first forward instead of stacking overlays and fighting over hotkeys; missing model files go to repair instead of a model error).

---

### Task 9: Docs, full suite, graph

- [ ] Update `README.md` "Run" section: first launch opens setup (download + PC check), `--model` is a per-run override.
- [ ] Update `HANDOFF.md`-independent docs only (HANDOFF is untracked).
- [ ] Run `.venv/Scripts/python -m pytest -q` → all pass (192 + new). Run `graphify update .`.
- [ ] Manual smoke (real display): delete nothing; run `python -m echoline` with `LOCALAPPDATA` pointed at a scratch folder and `APPDATA` likewise → onboarding downloads Tiny with progress, checks PC, sound test shows captions, theme applies, Finish. Launch a second time → first comes forward. Record in ledger.
- [ ] Commit — "Document first-run setup".

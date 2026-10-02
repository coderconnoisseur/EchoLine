# M0 + M1: Engine Verification and Core Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove Moonshine streaming beats Vosk on this hardware (M0), then replace the Qt Widgets app with a low-latency WASAPI-loopback → Moonshine → QML rolling-caption pipeline (M1).

**Architecture:** A new `echoline/` package with four isolated units: `audio` (sources that emit 16 kHz mono float32), `engine` (adapters that turn audio into `Partial`/`Final` events), `pipeline` (a worker thread with backlog protection and latency tracking), and `captions` + `ui` (a `QAbstractListModel` rendered by a QML overlay). Threads talk through a bounded queue and one queued Qt signal.

**Tech Stack:** Python 3.11, PySide6 6.6 (QtQuick/QML), moonshine-voice 0.1.5, PyAudioWPatch 0.2.12.8, soxr 1.1, vosk 0.3.45, pytest; pyarrow (dev only, for benchmark clips).

**Spec:** `docs/superpowers/specs/2026-10-03-echoline-v1-design.md` (sections Architecture, Latency budget, Error handling, Testing, Milestones M0–M1).

## Global Constraints

- Windows 10+ only; Python >= 3.10 (moonshine-voice uses `X | Y` annotations at runtime). Develop and test with the project venv: `.venv/Scripts/python`.
- `PySide6==6.6.0` stays pinned; no other UI libraries.
- English only; Moonshine English models are MIT. Never call `get_model_for_language` with a non-English language.
- Sources emit float32 mono samples at **16 000 Hz**, in blocks of 20–50 ms.
- Engines emit `Partial(utterance_id, text)` / `Final(utterance_id, text)`; `utterance_id` is a small sequential `int` assigned by the adapter (Moonshine's own ids are 64-bit and overflow QML `int`).
- Backlog limit: more than **1.0 s** of queued audio drops the oldest audio and raises `lagging`.
- Latency targets: p50 < 300 ms, p95 < 600 ms sound-to-screen.
- Tests must not need a microphone, speakers, network or downloaded models, except tests marked `@pytest.mark.model`, which are skipped by default.
- Commit messages: plain imperative summary plus a short body explaining why. Never mention AI tools, assistants or co-authors in commits, PRs or code.
- One logical change per commit; run the full suite (`.venv/Scripts/python -m pytest`) before every commit.

## Review Focus

1. **Default output device changes mid-session** (headphones plugged in, Bluetooth connects): captions must keep flowing from the new device without a restart — pinned in Task 7 (`test_reopens_when_default_device_changes`).
2. **Engine slower than real time** on a weak CPU: captions must stay near real time by dropping old audio, never drift seconds behind — pinned in Task 8 (`test_backlog_drops_oldest_audio_and_flags_lagging`).
3. **No loopback device or the stream fails to open**: the app must show "No audio device" and retry, not crash — pinned in Task 7 (`test_reports_missing_device_and_retries`) and Task 12 (`test_status_shows_audio_errors`).
4. **A long monologue with no pauses** (one utterance growing for a minute): the overlay must show only the newest lines at a fixed height — pinned in Task 11 (`test_long_utterance_stays_within_line_budget`).
5. **Speech that stops mid-sentence then silence / app shutdown**: the last partial line must still become final, not hang as a partial forever — pinned in Task 8 (`test_stop_flushes_pending_partial_as_final`).

---

## File Structure

```
echoline/
  __init__.py
  __main__.py              # `python -m echoline` entry point (Task 12)
  app.py                   # wires source → worker → model → QML (Task 12)
  bench.py                 # M0 benchmark runner (Task 4)
  audio/
    __init__.py
    base.py                # AudioSource protocol (Task 7)
    convert.py             # StreamConverter: any rate/channels → 16 kHz mono float32 (Task 6)
    loopback.py            # LoopbackSource over PyAudioWPatch (Task 7)
  engine/
    __init__.py
    base.py                # Partial, Final, SpeechEngine (Task 1)
    moonshine_engine.py    # MoonshineEngine (Task 1)
    vosk_engine.py         # VoskEngine (Task 2)
    vosk_recognizer.py     # moved from transcription/speech_recognition.py (Task 13)
  pipeline/
    __init__.py
    worker.py              # EngineWorker thread with backlog protection (Task 8)
    latency.py             # LatencyTracker (Task 10)
  captions/
    __init__.py
    model.py               # CaptionModel(QAbstractListModel) (Task 9)
  ui/
    __init__.py
    overlay.py             # loads QML, exposes OverlayStatus (Task 11)
    qml/
      Overlay.qml          # rolling-caption window (Task 11)
scripts/
  fetch_bench_clips.py     # downloads LibriSpeech sample clips for M0 (Task 3)
docs/benchmarks/
  2026-10-engine-bench.md  # M0 results and decision (Task 5)
tests/
  test_engine_moonshine.py, test_engine_vosk.py, test_fetch_bench_clips.py,
  test_bench.py, test_audio_convert.py, test_loopback.py, test_worker.py,
  test_caption_model.py, test_latency.py, test_overlay_qml.py, test_echoline_app.py
```

Legacy top-level `app.py`, `main.py`, `audio/`, `ui/`, `utils/`, `transcription/` are removed in Task 13 once the new pipeline runs.

---

# M0 — Engine verification

### Task 1: Engine interface and Moonshine adapter

**Files:**
- Create: `echoline/__init__.py`, `echoline/engine/__init__.py`, `echoline/engine/base.py`, `echoline/engine/moonshine_engine.py`
- Modify: `pytest.ini`, `requirements.txt`
- Test: `tests/test_engine_moonshine.py`

**Interfaces:**
- Produces:
  - `echoline.engine.base.Partial(utterance_id: int, text: str)` and `Final(utterance_id: int, text: str)` — frozen dataclasses.
  - `echoline.engine.base.SpeechEngine` — Protocol with `feed(samples: np.ndarray) -> list[Partial | Final]` and `flush() -> list[Final]`.
  - `MoonshineEngine(stream)` where `stream` has `add_listener(cb)`, `start()`, `add_audio(list[float], sample_rate)`, `stop()`.
  - `MoonshineEngine.load(model_arch: ModelArch, update_interval: float = 0.15) -> MoonshineEngine` — downloads (cached) and opens the English model.

- [ ] **Step 1: Register the `model` marker and add the dependency**

`pytest.ini`:
```ini
[pytest]
pythonpath = .
testpaths = tests
addopts = -m "not model"
markers =
    model: needs downloaded speech models (run with: pytest -m model)
```

Append to `requirements.txt` under `# Core EchoLine Dependencies`:
```
moonshine-voice==0.1.5
```

- [ ] **Step 2: Write the failing tests**

`tests/test_engine_moonshine.py`:
```python
import os
from dataclasses import dataclass

import numpy as np
import pytest

from echoline.engine.base import Final, Partial
from echoline.engine.moonshine_engine import MoonshineEngine


@dataclass
class Line:
    line_id: int
    text: str
    is_complete: bool


@dataclass
class Event:
    line: Line


class LineTextChanged(Event):
    pass


class LineCompleted(Event):
    pass


class FakeStream:
    """Emits scripted Moonshine-style events, one batch per add_audio call."""

    def __init__(self, batches, on_stop=()):
        self.batches = list(batches)
        self.on_stop = list(on_stop)
        self.listeners = []
        self.started = False
        self.received = []

    def add_listener(self, listener):
        self.listeners.append(listener)

    def start(self):
        self.started = True

    def add_audio(self, audio, sample_rate):
        self.received.append((audio, sample_rate))
        for event in self.batches.pop(0) if self.batches else []:
            for listener in self.listeners:
                listener(event)

    def stop(self):
        for event in self.on_stop:
            for listener in self.listeners:
                listener(event)


BIG_ID = 17353615195091815899


def test_text_changes_become_partials_and_completions_become_finals():
    stream = FakeStream([
        [LineTextChanged(Line(BIG_ID, "It was", False))],
        [LineCompleted(Line(BIG_ID, "It was the best.", True))],
    ])
    engine = MoonshineEngine(stream)

    first = engine.feed(np.zeros(800, dtype=np.float32))
    second = engine.feed(np.zeros(800, dtype=np.float32))

    assert first == [Partial(0, "It was")]
    assert second == [Final(0, "It was the best.")]


def test_each_moonshine_line_gets_a_small_sequential_id():
    stream = FakeStream([
        [LineCompleted(Line(BIG_ID, "one", True))],
        [LineTextChanged(Line(BIG_ID + 1, "two", False))],
    ])
    engine = MoonshineEngine(stream)

    events = engine.feed(np.zeros(1, np.float32)) + engine.feed(np.zeros(1, np.float32))

    assert [event.utterance_id for event in events] == [0, 1]


def test_audio_is_passed_as_16khz_float_list():
    stream = FakeStream([])
    engine = MoonshineEngine(stream)

    engine.feed(np.array([0.5, -0.25], dtype=np.float32))

    assert stream.started
    assert stream.received == [([0.5, -0.25], 16000)]


def test_flush_finalizes_lines_completed_on_stop():
    stream = FakeStream([], on_stop=[LineCompleted(Line(BIG_ID, "last words", True))])
    engine = MoonshineEngine(stream)

    assert engine.flush() == [Final(0, "last words")]


def test_empty_text_changes_are_ignored():
    stream = FakeStream([[LineTextChanged(Line(BIG_ID, "", False))]])
    engine = MoonshineEngine(stream)

    assert engine.feed(np.zeros(1, np.float32)) == []


@pytest.mark.model
def test_real_tiny_model_transcribes_bundled_clip():
    from moonshine_voice import ModelArch, get_assets_path, load_wav_file
    import soxr

    engine = MoonshineEngine.load(ModelArch.TINY_STREAMING)
    audio, rate = load_wav_file(os.path.join(get_assets_path(), "two_cities.wav"))
    samples = soxr.resample(np.asarray(audio, dtype=np.float32), rate, 16000)

    events = []
    for start in range(0, len(samples), 800):
        events += engine.feed(samples[start:start + 800])
    events += engine.flush()

    finals = " ".join(e.text for e in events if isinstance(e, Final)).lower()
    assert "best of times" in finals
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_engine_moonshine.py -v`
Expected: FAIL / collection error with `ModuleNotFoundError: No module named 'echoline'`.

- [ ] **Step 4: Implement**

`echoline/__init__.py`:
```python
"""EchoLine: live, offline captions for anything playing on your PC."""
```

`echoline/engine/__init__.py`:
```python
from .base import Final, Partial, SpeechEngine

__all__ = ["Final", "Partial", "SpeechEngine"]
```

`echoline/engine/base.py`:
```python
from dataclasses import dataclass
from typing import Protocol, Union

import numpy as np

SAMPLE_RATE = 16000


@dataclass(frozen=True)
class Partial:
    """Text of an utterance that is still being spoken; may change."""
    utterance_id: int
    text: str


@dataclass(frozen=True)
class Final:
    """Settled text of a finished utterance."""
    utterance_id: int
    text: str


Event = Union[Partial, Final]


class SpeechEngine(Protocol):
    def feed(self, samples: np.ndarray) -> list[Event]:
        """Consume 16 kHz mono float32 samples, return any new events."""

    def flush(self) -> list[Final]:
        """Finish pending audio, returning the last finals."""
```

`echoline/engine/moonshine_engine.py`:
```python
import numpy as np

from .base import SAMPLE_RATE, Event, Final, Partial


class MoonshineEngine:
    """Adapts a moonshine_voice Stream to EchoLine's Partial/Final events."""

    def __init__(self, stream):
        self._stream = stream
        self._ids = {}       # Moonshine line id -> small sequential id
        self._pending = []
        stream.add_listener(self._on_event)
        stream.start()

    @classmethod
    def load(cls, model_arch, update_interval=0.15):
        from moonshine_voice import Transcriber, get_model_for_language

        path, arch = get_model_for_language("en", model_arch)
        transcriber = Transcriber(model_path=path, model_arch=arch, update_interval=update_interval)
        engine = cls(transcriber.create_stream(update_interval=update_interval))
        engine._transcriber = transcriber  # keep the native handle alive
        return engine

    def _on_event(self, event):
        kind = type(event).__name__
        if kind not in ("LineTextChanged", "LineCompleted") or not event.line.text:
            return
        utterance_id = self._ids.setdefault(event.line.line_id, len(self._ids))
        event_type = Final if kind == "LineCompleted" else Partial
        self._pending.append(event_type(utterance_id, event.line.text))

    def _take(self):
        events, self._pending = self._pending, []
        return events

    def feed(self, samples: np.ndarray) -> list[Event]:
        self._stream.add_audio(samples.astype(np.float32, copy=False).tolist(), SAMPLE_RATE)
        return self._take()

    def flush(self) -> list[Final]:
        self._stream.stop()
        return [event for event in self._take() if isinstance(event, Final)]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_engine_moonshine.py -v`
Expected: 5 passed, 1 deselected.
Then: `.venv/Scripts/python -m pytest -m model tests/test_engine_moonshine.py -v`
Expected: 1 passed (downloads the tiny model on first run).

- [ ] **Step 6: Commit**

```bash
git add echoline pytest.ini requirements.txt tests/test_engine_moonshine.py
git commit -m "Add speech engine interface and Moonshine streaming adapter" -m "Engines emit Partial/Final events with small sequential utterance ids; Moonshine's 64-bit line ids would overflow QML ints. Real-model tests are marked 'model' and skipped by default."
```

---

### Task 2: Vosk adapter

**Files:**
- Create: `echoline/engine/vosk_engine.py`
- Test: `tests/test_engine_vosk.py`

**Interfaces:**
- Consumes: `Partial`, `Final`, `SAMPLE_RATE` from `echoline.engine.base`.
- Produces: `VoskEngine(recognizer)` where `recognizer` has `AcceptWaveform(bytes) -> bool`, `Result() -> str`, `PartialResult() -> str`, `FinalResult() -> str`; `VoskEngine.load(model_path: str) -> VoskEngine`.

- [ ] **Step 1: Write the failing tests**

`tests/test_engine_vosk.py`:
```python
import json

import numpy as np

from echoline.engine.base import Final, Partial
from echoline.engine.vosk_engine import VoskEngine


class FakeKaldi:
    def __init__(self, script, final=""):
        self.script = list(script)   # list of (accepted, text)
        self.final = final
        self.waveforms = []
        self._last = ""

    def AcceptWaveform(self, data):
        self.waveforms.append(data)
        accepted, self._last = self.script.pop(0)
        return accepted

    def Result(self):
        return json.dumps({"text": self._last})

    def PartialResult(self):
        return json.dumps({"partial": self._last})

    def FinalResult(self):
        return json.dumps({"text": self.final})


def test_partials_then_final_share_an_utterance_id():
    engine = VoskEngine(FakeKaldi([(False, "hello"), (True, "hello world"), (False, "next")]))
    chunk = np.zeros(160, dtype=np.float32)

    events = engine.feed(chunk) + engine.feed(chunk) + engine.feed(chunk)

    assert events == [Partial(0, "hello"), Final(0, "hello world"), Partial(1, "next")]


def test_float_samples_are_sent_as_int16_pcm():
    kaldi = FakeKaldi([(False, "")])
    engine = VoskEngine(kaldi)

    engine.feed(np.array([0.5, -1.0], dtype=np.float32))

    assert kaldi.waveforms == [np.array([16383, -32767], dtype=np.int16).tobytes()]


def test_unchanged_or_empty_partials_are_not_repeated():
    engine = VoskEngine(FakeKaldi([(False, ""), (False, "hi"), (False, "hi")]))
    chunk = np.zeros(160, dtype=np.float32)

    events = engine.feed(chunk) + engine.feed(chunk) + engine.feed(chunk)

    assert events == [Partial(0, "hi")]


def test_flush_returns_remaining_text_as_final():
    engine = VoskEngine(FakeKaldi([(False, "almost")], final="almost done"))
    engine.feed(np.zeros(160, dtype=np.float32))

    assert engine.flush() == [Final(0, "almost done")]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_engine_vosk.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'echoline.engine.vosk_engine'`.

- [ ] **Step 3: Implement**

`echoline/engine/vosk_engine.py`:
```python
import json

import numpy as np

from .base import SAMPLE_RATE, Event, Final, Partial


class VoskEngine:
    """Adapts a Vosk KaldiRecognizer to EchoLine's Partial/Final events."""

    def __init__(self, recognizer):
        self._recognizer = recognizer
        self._utterance = 0
        self._last_partial = ""

    @classmethod
    def load(cls, model_path):
        from vosk import KaldiRecognizer, Model

        return cls(KaldiRecognizer(Model(model_path), SAMPLE_RATE))

    def _final(self, text):
        event = Final(self._utterance, text)
        self._utterance += 1
        self._last_partial = ""
        return event

    def feed(self, samples: np.ndarray) -> list[Event]:
        pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16).tobytes()
        if self._recognizer.AcceptWaveform(pcm):
            text = json.loads(self._recognizer.Result()).get("text", "")
            return [self._final(text)] if text else []
        text = json.loads(self._recognizer.PartialResult()).get("partial", "")
        if not text or text == self._last_partial:
            return []
        self._last_partial = text
        return [Partial(self._utterance, text)]

    def flush(self) -> list[Final]:
        text = json.loads(self._recognizer.FinalResult()).get("text", "")
        return [self._final(text)] if text else []
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_engine_vosk.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add echoline/engine/vosk_engine.py tests/test_engine_vosk.py
git commit -m "Add Vosk engine adapter" -m "Keeps Vosk available as a fallback engine behind the same Partial/Final interface as Moonshine."
```

---

### Task 3: Benchmark clip fetcher

**Files:**
- Create: `scripts/fetch_bench_clips.py`
- Modify: `requirements-dev.txt`, `.gitignore`
- Test: `tests/test_fetch_bench_clips.py`

**Interfaces:**
- Produces: `write_clips(rows, out_dir: Path) -> int` where each row is a dict `{"id": str, "text": str, "audio_bytes": bytes}` (FLAC or WAV bytes); writes `<id>.wav` (16 kHz mono PCM16) and `<id>.txt` (lowercase reference text). Clips land in `bench_clips/` (gitignored).

- [ ] **Step 1: Add dev dependency and ignore rule**

`requirements-dev.txt`:
```
-r requirements.txt
pytest>=7.0
pyarrow>=14.0
```

Append to `.gitignore`:
```
# Benchmark audio (downloaded by scripts/fetch_bench_clips.py)
bench_clips/
```

Run: `.venv/Scripts/python -m pip install -r requirements-dev.txt`

- [ ] **Step 2: Write the failing test**

`tests/test_fetch_bench_clips.py`:
```python
import io
import wave

import numpy as np
import soundfile as sf

from scripts.fetch_bench_clips import write_clips


def flac_bytes(samples, rate):
    buffer = io.BytesIO()
    sf.write(buffer, samples, rate, format="FLAC")
    return buffer.getvalue()


def test_clips_are_written_as_16khz_wav_with_lowercase_text(tmp_path):
    tone = (0.3 * np.sin(np.linspace(0, 200, 8000))).astype(np.float32)
    rows = [{"id": "1272-128104-0000", "text": "MISTER QUILTER IS", "audio_bytes": flac_bytes(tone, 8000)}]

    count = write_clips(rows, tmp_path)

    assert count == 1
    assert (tmp_path / "1272-128104-0000.txt").read_text() == "mister quilter is"
    with wave.open(str(tmp_path / "1272-128104-0000.wav")) as wav:
        assert wav.getframerate() == 16000
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert abs(wav.getnframes() - 16000) <= 1
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_fetch_bench_clips.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts'`.

- [ ] **Step 4: Implement**

`scripts/__init__.py`: empty file.

`scripts/fetch_bench_clips.py`:
```python
"""Download LibriSpeech sample clips (73 utterances, ~9 MB) for the engine benchmark.

Usage: python -m scripts.fetch_bench_clips [--out bench_clips]
"""
import argparse
import io
import wave
from pathlib import Path

import librosa
import numpy as np

PARQUET_URL = (
    "https://huggingface.co/api/datasets/hf-internal-testing/"
    "librispeech_asr_dummy/parquet/clean/validation/0.parquet"
)


def write_clips(rows, out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for row in rows:
        samples, _ = librosa.load(io.BytesIO(row["audio_bytes"]), sr=16000, mono=True)
        pcm = np.clip(np.round(samples * 32768), -32768, 32767).astype(np.int16)
        with wave.open(str(out_dir / f"{row['id']}.wav"), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(pcm.tobytes())
        (out_dir / f"{row['id']}.txt").write_text(row["text"].lower())
        count += 1
    return count


def download_rows():
    import pyarrow.parquet as pq
    import requests

    response = requests.get(PARQUET_URL, timeout=120)
    response.raise_for_status()
    table = pq.read_table(io.BytesIO(response.content), columns=["id", "text", "audio"])
    for record in table.to_pylist():
        yield {"id": record["id"], "text": record["text"], "audio_bytes": record["audio"]["bytes"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="bench_clips", type=Path)
    args = parser.parse_args()
    print(f"Wrote {write_clips(download_rows(), args.out)} clips to {args.out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run tests, then fetch the real clips**

Run: `.venv/Scripts/python -m pytest tests/test_fetch_bench_clips.py -v`
Expected: 1 passed.
Run: `.venv/Scripts/python -m scripts.fetch_bench_clips`
Expected: `Wrote 73 clips to bench_clips`.

- [ ] **Step 6: Commit**

```bash
git add scripts requirements-dev.txt .gitignore tests/test_fetch_bench_clips.py
git commit -m "Add script to fetch LibriSpeech sample clips for benchmarking" -m "Writes 16 kHz mono WAV files with lowercase reference transcripts into the gitignored bench_clips/ folder."
```

---

### Task 4: Benchmark runner

**Files:**
- Create: `echoline/bench.py`
- Test: `tests/test_bench.py`

**Interfaces:**
- Consumes: `SpeechEngine`, `Final` (Task 1); `TranscriptionEvaluator` from `metrics.accuracy_evaluator`.
- Produces:
  - `ClipResult(clip: str, hypothesis: str, wer: float, rtf: float, p95_feed_ms: float, first_text_s: float | None)`
  - `run_clip(engine, samples: np.ndarray, reference: str, clip: str, chunk_ms: int = 50) -> ClipResult`
  - `summarize(results: list[ClipResult]) -> dict` with keys `wer`, `rtf`, `p95_feed_ms`, `first_text_s`
  - CLI: `python -m echoline.bench --clips bench_clips --engines moonshine-tiny moonshine-small moonshine-medium vosk --vosk-model PATH --out bench_results.json`

`wer` is aggregated as total edit operations / total reference words; `rtf` is total processing time / total audio duration; `first_text_s` is the audio position (seconds) at which the first non-empty event appeared — how long a viewer waits for the first word.

- [ ] **Step 1: Write the failing tests**

`tests/test_bench.py`:
```python
import numpy as np
import pytest

from echoline.bench import ClipResult, run_clip, summarize
from echoline.engine.base import Final, Partial


class ScriptedEngine:
    """Emits a partial after the 2nd chunk and a final on flush."""

    def __init__(self, text):
        self.text = text
        self.calls = 0

    def feed(self, samples):
        self.calls += 1
        return [Partial(0, self.text.split()[0])] if self.calls == 2 else []

    def flush(self):
        return [Final(0, self.text)]


def test_run_clip_scores_hypothesis_against_reference():
    samples = np.zeros(16000, dtype=np.float32)   # 1 s of audio, 20 chunks of 50 ms

    result = run_clip(ScriptedEngine("hello there world"), samples, "hello big world", clip="c1")

    assert result.clip == "c1"
    assert result.hypothesis == "hello there world"
    assert result.wer == pytest.approx(1 / 3)
    assert result.first_text_s == pytest.approx(0.1)
    assert result.rtf >= 0


def test_no_output_means_no_first_text_and_full_error():
    class Silent:
        def feed(self, samples):
            return []

        def flush(self):
            return []

    result = run_clip(Silent(), np.zeros(1600, np.float32), "two words", clip="c2")

    assert result.first_text_s is None
    assert result.wer == 1.0


def test_summary_weights_wer_by_reference_length():
    results = [
        ClipResult("a", "", wer=1.0, rtf=0.2, p95_feed_ms=10, first_text_s=0.5, ref_words=1, audio_s=1, process_s=0.2),
        ClipResult("b", "", wer=0.0, rtf=0.4, p95_feed_ms=30, first_text_s=None, ref_words=3, audio_s=3, process_s=1.2),
    ]

    summary = summarize(results)

    assert summary["wer"] == pytest.approx(0.25)
    assert summary["rtf"] == pytest.approx(1.4 / 4)
    assert summary["p95_feed_ms"] == 30
    assert summary["first_text_s"] == pytest.approx(0.5)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_bench.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'echoline.bench'`.

- [ ] **Step 3: Implement**

`echoline/bench.py`:
```python
"""Compare speech engines on reference clips: accuracy (WER) and speed.

Usage:
    python -m echoline.bench --clips bench_clips \
        --engines moonshine-tiny moonshine-small moonshine-medium vosk \
        --vosk-model PATH_TO_VOSK_MODEL --out bench_results.json
"""
import argparse
import json
import statistics
import time
import wave
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import numpy as np

from metrics.accuracy_evaluator import TranscriptionEvaluator

from .engine.base import SAMPLE_RATE, Final


@dataclass
class ClipResult:
    clip: str
    hypothesis: str
    wer: float
    rtf: float
    p95_feed_ms: float
    first_text_s: Optional[float]
    ref_words: int = 0
    audio_s: float = 0.0
    process_s: float = 0.0


def run_clip(engine, samples, reference, clip, chunk_ms=50) -> ClipResult:
    chunk = SAMPLE_RATE * chunk_ms // 1000
    feed_times, finals, first_text_s = [], [], None
    for index, start in enumerate(range(0, len(samples), chunk)):
        began = time.perf_counter()
        events = engine.feed(samples[start:start + chunk])
        feed_times.append(time.perf_counter() - began)
        if first_text_s is None and any(event.text for event in events):
            first_text_s = (index + 1) * chunk / SAMPLE_RATE
        finals += [event.text for event in events if isinstance(event, Final)]
    began = time.perf_counter()
    finals += [event.text for event in engine.flush()]
    process_s = sum(feed_times) + time.perf_counter() - began

    hypothesis = " ".join(text for text in finals if text)
    metrics = TranscriptionEvaluator().evaluate_transcription(reference, hypothesis)
    audio_s = len(samples) / SAMPLE_RATE
    p95 = float(np.percentile(feed_times, 95)) * 1000 if feed_times else 0.0
    return ClipResult(clip, hypothesis, metrics.word_error_rate, process_s / max(audio_s, 1e-9),
                      p95, first_text_s, metrics.total_words, audio_s, process_s)


def summarize(results) -> dict:
    ref_words = sum(r.ref_words for r in results)
    first_texts = [r.first_text_s for r in results if r.first_text_s is not None]
    return {
        "wer": sum(r.wer * r.ref_words for r in results) / max(ref_words, 1),
        "rtf": sum(r.process_s for r in results) / max(sum(r.audio_s for r in results), 1e-9),
        "p95_feed_ms": max((r.p95_feed_ms for r in results), default=0.0),
        "first_text_s": statistics.median(first_texts) if first_texts else None,
    }


def load_clip(wav_path: Path) -> np.ndarray:
    with wave.open(str(wav_path)) as wav:
        pcm = np.frombuffer(wav.readframes(wav.getnframes()), dtype=np.int16)
    return pcm.astype(np.float32) / 32768


def make_engine(name, vosk_model):
    if name == "vosk":
        from .engine.vosk_engine import VoskEngine
        return VoskEngine.load(vosk_model)
    from moonshine_voice import ModelArch
    from .engine.moonshine_engine import MoonshineEngine
    arch = {"moonshine-tiny": ModelArch.TINY_STREAMING,
            "moonshine-small": ModelArch.SMALL_STREAMING,
            "moonshine-medium": ModelArch.MEDIUM_STREAMING}[name]
    return MoonshineEngine.load(arch)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--clips", type=Path, default=Path("bench_clips"))
    parser.add_argument("--engines", nargs="+", default=["moonshine-tiny", "moonshine-small"])
    parser.add_argument("--vosk-model", default=None)
    parser.add_argument("--out", type=Path, default=Path("bench_results.json"))
    args = parser.parse_args()

    clips = sorted(args.clips.glob("*.wav"))
    report = {}
    print(f"{'engine':<18}{'WER':>8}{'RTF':>8}{'p95 feed ms':>13}{'first text s':>14}")
    for name in args.engines:
        results = []
        for wav_path in clips:
            engine = make_engine(name, args.vosk_model)   # fresh engine: no state between clips
            reference = wav_path.with_suffix(".txt").read_text()
            results.append(run_clip(engine, load_clip(wav_path), reference, wav_path.stem))
        summary = summarize(results)
        report[name] = {"summary": summary, "clips": [asdict(r) for r in results]}
        first = summary["first_text_s"]
        print(f"{name:<18}{summary['wer']:>8.3f}{summary['rtf']:>8.3f}"
              f"{summary['p95_feed_ms']:>13.1f}{(first if first is not None else float('nan')):>14.2f}")
    args.out.write_text(json.dumps(report, indent=2))
    print(f"Full results: {args.out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_bench.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add echoline/bench.py tests/test_bench.py
git commit -m "Add engine benchmark runner" -m "Streams each reference clip through an engine in 50 ms chunks and reports WER, real-time factor, p95 per-chunk processing time and time to first text."
```

---

### Task 5: Run the benchmark and record the decision

**Files:**
- Create: `docs/benchmarks/2026-10-engine-bench.md`
- Modify: `.gitignore` (add `bench_results.json`)

**Interfaces:**
- Produces: the default model arch for M1 (`DEFAULT_MODEL_ARCH`, used in Task 12) and the Small/Tiny threshold M4 will use.

- [ ] **Step 1: Get a Vosk model for comparison**

Download `vosk-model-small-en-us-0.15` from https://alphacephei.com/vosk/models and extract it to `%USERPROFILE%\.cache\vosk\` (the path the legacy app already uses).

- [ ] **Step 2: Run the benchmark** (models download on first use)

```bash
.venv/Scripts/python -m echoline.bench --engines moonshine-tiny moonshine-small moonshine-medium vosk --vosk-model "%USERPROFILE%/.cache/vosk/vosk-model-small-en-us-0.15"
```
Expected: a four-row table, `bench_results.json` written.

- [ ] **Step 3: Write the results and decision**

`docs/benchmarks/2026-10-engine-bench.md` must contain: machine (CPU model, cores, RAM — from `wmic cpu get name,numberofcores` and `systeminfo | findstr Memory`), the printed table, and a decision section stating:
- the chosen default for M1: the most accurate Moonshine model whose RTF < 0.5 and p95 feed time < 150 ms (headroom for a busy PC); if none qualifies, Tiny;
- whether Moonshine beat Vosk on WER (expected: yes); if not, stop and raise it before starting M1;
- the RTF threshold M4's hardware check should use to choose between models.

Append `bench_results.json` to `.gitignore`.

- [ ] **Step 4: Commit**

```bash
git add docs/benchmarks/2026-10-engine-bench.md .gitignore
git commit -m "Record engine benchmark results and default model choice"
```

---

# M1 — Core pipeline

### Task 6: Streaming audio converter

**Files:**
- Create: `echoline/audio/__init__.py`, `echoline/audio/convert.py`
- Modify: `requirements.txt` (add `soxr>=0.3`)
- Test: `tests/test_audio_convert.py`

**Interfaces:**
- Produces: `StreamConverter(in_rate: int, channels: int)` with `process(block: np.ndarray) -> np.ndarray` taking interleaved int16 or float32 frames shaped `(frames, channels)` or flat, returning float32 mono at 16 kHz. Stateful across calls (no clicks at block edges).

- [ ] **Step 1: Write the failing tests**

`tests/test_audio_convert.py`:
```python
import numpy as np
import pytest

from echoline.audio.convert import StreamConverter


def stereo_sine(rate, seconds, freq=440, amplitude=0.5):
    t = np.arange(int(rate * seconds)) / rate
    mono = amplitude * np.sin(2 * np.pi * freq * t)
    return np.stack([mono, mono], axis=1).astype(np.float32)


def test_48k_stereo_float_becomes_16k_mono():
    converter = StreamConverter(in_rate=48000, channels=2)

    out = np.concatenate([converter.process(block) for block in np.array_split(stereo_sine(48000, 1.0), 50)])

    assert out.dtype == np.float32
    assert abs(len(out) - 16000) < 400            # streaming resampler holds back a few ms
    assert np.max(np.abs(out[2000:-2000])) == pytest.approx(0.5, abs=0.02)


def test_int16_input_is_scaled_to_unit_range():
    converter = StreamConverter(in_rate=16000, channels=1)
    block = np.full(1600, 16384, dtype=np.int16)

    out = converter.process(block)

    assert out.dtype == np.float32
    assert np.allclose(out, 0.5, atol=1e-3)


def test_16k_mono_passes_through_unchanged():
    converter = StreamConverter(in_rate=16000, channels=1)
    block = np.linspace(-1, 1, 800, dtype=np.float32)

    assert np.array_equal(converter.process(block), block)


def test_flat_interleaved_input_is_accepted():
    converter = StreamConverter(in_rate=16000, channels=2)
    interleaved = np.array([0.2, 0.4, 0.6, 0.8], dtype=np.float32)   # two stereo frames

    assert np.allclose(converter.process(interleaved), [0.3, 0.7])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_audio_convert.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'echoline.audio'`.

- [ ] **Step 3: Implement**

`echoline/audio/__init__.py`: empty file.

`echoline/audio/convert.py`:
```python
import numpy as np
import soxr

TARGET_RATE = 16000


class StreamConverter:
    """Turns device audio (any rate, any channel count) into 16 kHz mono float32."""

    def __init__(self, in_rate: int, channels: int):
        self.channels = channels
        self._resampler = None if in_rate == TARGET_RATE else soxr.ResampleStream(
            in_rate, TARGET_RATE, 1, dtype="float32", quality="HQ")

    def process(self, block: np.ndarray) -> np.ndarray:
        samples = block.astype(np.float32) / 32768 if block.dtype == np.int16 else block.astype(np.float32, copy=False)
        if self.channels > 1:
            samples = samples.reshape(-1, self.channels).mean(axis=1)
        else:
            samples = samples.reshape(-1)
        if self._resampler is None:
            return samples
        return self._resampler.resample_chunk(samples)
```

Append to `requirements.txt` under core dependencies: `soxr>=0.3`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_audio_convert.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add echoline/audio requirements.txt tests/test_audio_convert.py
git commit -m "Add streaming converter to 16 kHz mono float audio" -m "Uses a stateful soxr resampler so block boundaries do not click; engines all consume 16 kHz mono."
```

---

### Task 7: Audio source interface and WASAPI loopback source

**Files:**
- Create: `echoline/audio/base.py`, `echoline/audio/loopback.py`
- Modify: `requirements.txt` (add `PyAudioWPatch==0.2.12.8`)
- Test: `tests/test_loopback.py`

**Interfaces:**
- Consumes: `StreamConverter` (Task 6).
- Produces:
  - `echoline.audio.base.AudioSource` — Protocol: `name: str`, `start(on_audio: Callable[[np.ndarray, float], None], on_status: Callable[[str], None]) -> None`, `stop() -> None`. `on_audio(samples, captured_at)` receives 16 kHz mono float32 and the `time.monotonic()` at capture. `on_status` receives `"listening"` or `"no-device"`.
  - `LoopbackSource(pyaudio_module=None, poll_interval: float = 2.0, block_ms: int = 30)`; `pyaudio_module` defaults to `pyaudiowpatch`. Exposes `check_device()` (called by the poll thread; public for tests).

- [ ] **Step 1: Write the failing tests**

`tests/test_loopback.py`:
```python
import numpy as np

from echoline.audio.loopback import LoopbackSource


class FakeStream:
    def __init__(self, callback):
        self.callback = callback
        self.closed = False

    def start_stream(self):
        pass

    def stop_stream(self):
        pass

    def close(self):
        self.closed = True


class FakePyAudio:
    paContinue = 0
    paInt16 = 8

    def __init__(self, devices):
        self.devices = devices            # list of device dicts; first is default, [] = none
        self.streams = []

    def PyAudio(self):
        return self

    def get_default_wasapi_loopback(self):
        if not self.devices:
            raise OSError("no loopback device")
        return self.devices[0]

    def open(self, **kwargs):
        stream = FakeStream(kwargs["stream_callback"])
        stream.kwargs = kwargs
        self.streams.append(stream)
        return stream

    def terminate(self):
        pass


SPEAKERS = {"index": 24, "name": "Speakers [Loopback]", "maxInputChannels": 2, "defaultSampleRate": 48000.0}
HEADPHONES = {"index": 31, "name": "Headphones [Loopback]", "maxInputChannels": 2, "defaultSampleRate": 44100.0}


def start(source):
    received, statuses = [], []
    source.start(lambda samples, captured_at: received.append(samples), statuses.append)
    return received, statuses


def test_opens_default_loopback_and_delivers_16khz_mono():
    fake = FakePyAudio([SPEAKERS])
    source = LoopbackSource(pyaudio_module=fake, poll_interval=None)
    received, statuses = start(source)

    stream = fake.streams[0]
    assert stream.kwargs["input_device_index"] == 24
    assert stream.kwargs["rate"] == 48000 and stream.kwargs["channels"] == 2
    frames = np.full((4800, 2), 8192, dtype=np.int16)              # 100 ms of stereo
    stream.callback(frames.tobytes(), 4800, None, 0)
    assert statuses == ["listening"]
    total = sum(len(chunk) for chunk in received)
    assert 1200 <= total <= 1600                                    # ~100 ms at 16 kHz
    assert np.allclose(np.concatenate(received)[-200:], 0.25, atol=0.02)


def test_reopens_when_default_device_changes():
    fake = FakePyAudio([SPEAKERS])
    source = LoopbackSource(pyaudio_module=fake, poll_interval=None)
    start(source)

    fake.devices = [HEADPHONES]
    source.check_device()

    assert fake.streams[0].closed
    assert fake.streams[1].kwargs["input_device_index"] == 31
    assert fake.streams[1].kwargs["rate"] == 44100


def test_reports_missing_device_and_retries():
    fake = FakePyAudio([])
    source = LoopbackSource(pyaudio_module=fake, poll_interval=None)
    _, statuses = start(source)

    assert statuses == ["no-device"]
    fake.devices = [SPEAKERS]
    source.check_device()
    assert statuses == ["no-device", "listening"]
    assert len(fake.streams) == 1


def test_stop_closes_the_stream():
    fake = FakePyAudio([SPEAKERS])
    source = LoopbackSource(pyaudio_module=fake, poll_interval=None)
    start(source)

    source.stop()

    assert fake.streams[0].closed
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_loopback.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'echoline.audio.loopback'`.

- [ ] **Step 3: Implement**

`echoline/audio/base.py`:
```python
from typing import Callable, Protocol

import numpy as np

AudioCallback = Callable[[np.ndarray, float], None]   # (16 kHz mono float32, time.monotonic() at capture)
StatusCallback = Callable[[str], None]                 # "listening" | "no-device"


class AudioSource(Protocol):
    name: str

    def start(self, on_audio: AudioCallback, on_status: StatusCallback) -> None: ...

    def stop(self) -> None: ...
```

`echoline/audio/loopback.py`:
```python
import threading
import time

import numpy as np

from .base import AudioCallback, StatusCallback
from .convert import StreamConverter


class LoopbackSource:
    """Captures whatever plays on the default output device via WASAPI loopback."""

    name = "System audio"

    def __init__(self, pyaudio_module=None, poll_interval=2.0, block_ms=30):
        if pyaudio_module is None:
            import pyaudiowpatch as pyaudio_module
        self._pyaudio = pyaudio_module
        self._poll_interval = poll_interval
        self._block_ms = block_ms
        self._audio = None
        self._stream = None
        self._device_index = None
        self._stopping = threading.Event()
        self._lock = threading.Lock()

    def start(self, on_audio: AudioCallback, on_status: StatusCallback) -> None:
        self._on_audio, self._on_status = on_audio, on_status
        self._audio = self._pyaudio.PyAudio()
        self._stopping.clear()
        self.check_device()
        if self._poll_interval:
            threading.Thread(target=self._poll, daemon=True).start()

    def _poll(self):
        while not self._stopping.wait(self._poll_interval):
            self.check_device()

    def check_device(self):
        """Open the default loopback device, reopening if it changed."""
        try:
            device = self._audio.get_default_wasapi_loopback()
        except OSError:
            device = None
        with self._lock:
            if device is None:
                if self._device_index is not None or self._stream is None:
                    self._close_stream()
                    self._device_index = None
                    self._on_status("no-device")
                return
            if device["index"] == self._device_index:
                return
            self._close_stream()
            self._open(device)

    def _open(self, device):
        rate = int(device["defaultSampleRate"])
        channels = int(device["maxInputChannels"])
        converter = StreamConverter(rate, channels)

        def callback(data, frame_count, time_info, status):
            captured_at = time.monotonic()
            samples = converter.process(np.frombuffer(data, dtype=np.int16))
            if len(samples):
                self._on_audio(samples, captured_at)
            return (None, self._pyaudio.paContinue)

        self._stream = self._audio.open(
            format=self._pyaudio.paInt16, channels=channels, rate=rate, input=True,
            input_device_index=device["index"], frames_per_buffer=rate * self._block_ms // 1000,
            stream_callback=callback)
        self._stream.start_stream()
        self._device_index = device["index"]
        self._on_status("listening")

    def _close_stream(self):
        if self._stream is not None:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None

    def stop(self) -> None:
        self._stopping.set()
        with self._lock:
            self._close_stream()
            self._device_index = None
        if self._audio is not None:
            self._audio.terminate()
            self._audio = None
```

Append to `requirements.txt` under core dependencies: `PyAudioWPatch==0.2.12.8`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_loopback.py -v`
Expected: 4 passed.

- [ ] **Step 5: Manual check on real hardware**

Run (play any video while it runs):
```bash
.venv/Scripts/python -c "import time; from echoline.audio.loopback import LoopbackSource; n=[0]; s=LoopbackSource(); s.start(lambda a,t: n.__setitem__(0, n[0]+len(a)), print); time.sleep(3); s.stop(); print('samples', n[0])"
```
Expected: prints `listening`, then `samples` near 48000 (3 s at 16 kHz).

- [ ] **Step 6: Commit**

```bash
git add echoline/audio/base.py echoline/audio/loopback.py requirements.txt tests/test_loopback.py
git commit -m "Capture system audio with WASAPI loopback" -m "Replaces the Stereo Mix requirement: follows the default output device, reopens when it changes, and reports when no device is available."
```

---

### Task 8: Engine worker with backlog protection

**Files:**
- Create: `echoline/pipeline/__init__.py`, `echoline/pipeline/worker.py`
- Test: `tests/test_worker.py`

**Interfaces:**
- Consumes: `SpeechEngine`, `Partial`, `Final`, `SAMPLE_RATE` (Task 1).
- Produces: `EngineWorker(engine, on_events: Callable[[list, float], None], on_lagging: Callable[[bool], None], max_backlog_s: float = 1.0)` with:
  - `push(samples: np.ndarray, captured_at: float)` — thread-safe; called from the audio thread.
  - `start()`, `stop()` — `stop()` joins the thread and delivers `engine.flush()` finals.
  - `on_events(events, captured_at)` is called on the worker thread; `captured_at` is the capture time of the newest block fed before those events appeared.
  - `process_pending()` — drains the queue synchronously (used by tests; the thread loop calls it too).

- [ ] **Step 1: Write the failing tests**

`tests/test_worker.py`:
```python
import threading
import time

import numpy as np

from echoline.engine.base import Final, Partial
from echoline.pipeline.worker import EngineWorker


class RecordingEngine:
    def __init__(self, partial_text="hi", flush_text="hi there"):
        self.fed = []
        self.partial_text = partial_text
        self.flush_text = flush_text

    def feed(self, samples):
        self.fed.append(len(samples))
        return [Partial(0, self.partial_text)]

    def flush(self):
        return [Final(0, self.flush_text)]


def block(ms):
    return np.zeros(16 * ms, dtype=np.float32)


def collect():
    events, lagging = [], []
    return events, lagging, (lambda evs, ts: events.append((evs, ts))), lagging.append


def test_events_are_delivered_with_capture_time_of_newest_block():
    events, lagging, on_events, on_lagging = collect()
    worker = EngineWorker(RecordingEngine(), on_events, on_lagging)

    worker.push(block(30), captured_at=1.0)
    worker.push(block(30), captured_at=1.03)
    worker.process_pending()

    assert events == [([Partial(0, "hi")], 1.0), ([Partial(0, "hi")], 1.03)]


def test_backlog_drops_oldest_audio_and_flags_lagging():
    events, lagging, on_events, on_lagging = collect()
    engine = RecordingEngine()
    worker = EngineWorker(engine, on_events, on_lagging, max_backlog_s=1.0)

    for i in range(50):                       # 1.5 s of 30 ms blocks queued while the engine is busy
        worker.push(block(30), captured_at=i * 0.03)
    worker.process_pending()

    assert sum(engine.fed) <= 16000           # never more than 1 s fed
    assert events[-1][1] == 49 * 0.03         # newest audio survived
    assert lagging == [True]


def test_lagging_clears_once_caught_up():
    events, lagging, on_events, on_lagging = collect()
    worker = EngineWorker(RecordingEngine(), on_events, on_lagging, max_backlog_s=0.1)

    for i in range(10):
        worker.push(block(30), captured_at=i)
    worker.process_pending()
    worker.push(block(30), captured_at=99)
    worker.process_pending()

    assert lagging == [True, False]


def test_stop_flushes_pending_partial_as_final():
    events, lagging, on_events, on_lagging = collect()
    worker = EngineWorker(RecordingEngine(flush_text="the end"), on_events, on_lagging)
    worker.start()
    worker.push(block(30), captured_at=5.0)

    worker.stop()

    assert events[-1][0] == [Final(0, "the end")]


def test_worker_thread_processes_pushed_audio():
    delivered = threading.Event()
    worker = EngineWorker(RecordingEngine(), lambda evs, ts: delivered.set(), lambda flag: None)
    worker.start()

    worker.push(block(30), captured_at=time.monotonic())

    assert delivered.wait(timeout=2)
    worker.stop()


def test_engine_errors_do_not_kill_the_worker():
    class Flaky(RecordingEngine):
        def feed(self, samples):
            if not self.fed:
                self.fed.append(0)
                raise RuntimeError("model hiccup")
            return super().feed(samples)

    events, lagging, on_events, on_lagging = collect()
    worker = EngineWorker(Flaky(), on_events, on_lagging)

    worker.push(block(30), captured_at=1.0)
    worker.push(block(30), captured_at=2.0)
    worker.process_pending()

    assert events == [([Partial(0, "hi")], 2.0)]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_worker.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'echoline.pipeline'`.

- [ ] **Step 3: Implement**

`echoline/pipeline/__init__.py`: empty file.

`echoline/pipeline/worker.py`:
```python
import collections
import threading
import traceback

from ..engine.base import SAMPLE_RATE


class EngineWorker:
    """Feeds queued audio to a speech engine on its own thread, never falling behind real time."""

    def __init__(self, engine, on_events, on_lagging, max_backlog_s=1.0):
        self._engine = engine
        self._on_events = on_events
        self._on_lagging = on_lagging
        self._max_backlog = int(max_backlog_s * SAMPLE_RATE)
        self._queue = collections.deque()
        self._queued_samples = 0
        self._lagging = False
        self._lock = threading.Lock()
        self._wakeup = threading.Event()
        self._running = False
        self._thread = None

    def push(self, samples, captured_at):
        with self._lock:
            self._queue.append((samples, captured_at))
            self._queued_samples += len(samples)
        self._wakeup.set()

    def _take_batch(self):
        """Pop everything queued, dropping the oldest audio beyond the backlog limit."""
        with self._lock:
            batch, self._queue = list(self._queue), collections.deque()
            queued, self._queued_samples = self._queued_samples, 0
        dropped = False
        while queued > self._max_backlog and len(batch) > 1:
            queued -= len(batch.pop(0)[0])
            dropped = True
        return batch, dropped

    def _set_lagging(self, lagging):
        if lagging != self._lagging:
            self._lagging = lagging
            self._on_lagging(lagging)

    def process_pending(self):
        batch, dropped = self._take_batch()
        if not batch:
            return
        self._set_lagging(dropped)
        for samples, captured_at in batch:
            try:
                events = self._engine.feed(samples)
            except Exception:
                traceback.print_exc()
                continue
            if events:
                self._on_events(events, captured_at)

    def _run(self):
        while self._running:
            self._wakeup.wait(timeout=0.5)
            self._wakeup.clear()
            self.process_pending()

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, name="engine-worker", daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._wakeup.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self.process_pending()
        finals = self._engine.flush()
        if finals:
            self._on_events(finals, None)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_worker.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add echoline/pipeline tests/test_worker.py
git commit -m "Add engine worker that never falls behind real time" -m "Runs the speech engine on its own thread; when more than a second of audio is queued it drops the oldest audio and reports lagging, so captions stay live on slow machines. Stopping flushes the last utterance as final."
```

---

### Task 9: Caption list model

**Files:**
- Create: `echoline/captions/__init__.py`, `echoline/captions/model.py`
- Test: `tests/test_caption_model.py`

**Interfaces:**
- Consumes: `Partial`, `Final` (Task 1).
- Produces: `CaptionModel(QAbstractListModel)` with roles `utteranceId` (int), `text` (str), `final` (bool); `apply(events: list)` (GUI thread only); `max_utterances` (default 6); `Q_PROPERTY latestText` is not needed — QML binds to rows.

- [ ] **Step 1: Write the failing tests**

`tests/test_caption_model.py`:
```python
from PySide6.QtCore import QCoreApplication, Qt

from echoline.captions.model import CaptionModel
from echoline.engine.base import Final, Partial

app = QCoreApplication.instance() or QCoreApplication([])


def rows(model):
    names = {v.data().decode(): k for k, v in model.roleNames().items()}
    return [
        (model.data(model.index(r), names["utteranceId"]),
         model.data(model.index(r), names["text"]),
         model.data(model.index(r), names["final"]))
        for r in range(model.rowCount())
    ]


def test_partial_updates_its_row_in_place():
    model = CaptionModel()
    inserted, changed = [], []
    model.rowsInserted.connect(lambda *a: inserted.append(a[1]))
    model.dataChanged.connect(lambda top, bottom, roles: changed.append(top.row()))

    model.apply([Partial(0, "It was")])
    model.apply([Partial(0, "It was the best")])
    model.apply([Final(0, "It was the best.")])

    assert rows(model) == [(0, "It was the best.", True)]
    assert inserted == [0]
    assert changed == [0, 0]


def test_new_utterances_append_rows():
    model = CaptionModel()

    model.apply([Final(0, "one."), Partial(1, "two")])

    assert rows(model) == [(0, "one.", True), (1, "two", False)]


def test_oldest_rows_are_removed_beyond_the_limit():
    model = CaptionModel(max_utterances=3)

    model.apply([Final(i, f"line {i}") for i in range(5)])

    assert [r[0] for r in rows(model)] == [2, 3, 4]


def test_late_event_for_dropped_utterance_is_ignored():
    model = CaptionModel(max_utterances=2)
    model.apply([Final(i, f"line {i}") for i in range(4)])

    model.apply([Final(0, "late")])

    assert [r[0] for r in rows(model)] == [2, 3]


def test_unicode_text_round_trips():
    model = CaptionModel()

    model.apply([Final(0, "café — naïve 👍")])

    assert rows(model)[0][1] == "café — naïve 👍"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_caption_model.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'echoline.captions'`.

- [ ] **Step 3: Implement**

`echoline/captions/__init__.py`: empty file.

`echoline/captions/model.py`:
```python
from PySide6.QtCore import QAbstractListModel, QByteArray, QModelIndex, Qt

from ..engine.base import Final

ID_ROLE = Qt.UserRole + 1
TEXT_ROLE = Qt.UserRole + 2
FINAL_ROLE = Qt.UserRole + 3


class CaptionModel(QAbstractListModel):
    """Recent utterances for the overlay; partials update their row in place."""

    def __init__(self, max_utterances=6, parent=None):
        super().__init__(parent)
        self.max_utterances = max_utterances
        self._rows = []          # [utterance_id, text, final]
        self._highest_dropped = -1

    def roleNames(self):
        return {ID_ROLE: QByteArray(b"utteranceId"), TEXT_ROLE: QByteArray(b"text"),
                FINAL_ROLE: QByteArray(b"final")}

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        utterance_id, text, final = self._rows[index.row()]
        return {ID_ROLE: utterance_id, TEXT_ROLE: text, Qt.DisplayRole: text, FINAL_ROLE: final}.get(role)

    def apply(self, events):
        for event in events:
            self._apply_one(event.utterance_id, event.text, isinstance(event, Final))

    def _apply_one(self, utterance_id, text, final):
        if utterance_id <= self._highest_dropped:
            return
        for row, entry in enumerate(self._rows):
            if entry[0] == utterance_id:
                entry[1], entry[2] = text, final
                index = self.index(row)
                self.dataChanged.emit(index, index, [TEXT_ROLE, FINAL_ROLE])
                return
        self.beginInsertRows(QModelIndex(), len(self._rows), len(self._rows))
        self._rows.append([utterance_id, text, final])
        self.endInsertRows()
        if len(self._rows) > self.max_utterances:
            self.beginRemoveRows(QModelIndex(), 0, 0)
            self._highest_dropped = self._rows.pop(0)[0]
            self.endRemoveRows()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_caption_model.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add echoline/captions tests/test_caption_model.py
git commit -m "Add caption list model for the QML overlay" -m "Each utterance is a row keyed by its id; partial updates change the row in place so QML animates only what changed, and old rows are trimmed to keep memory flat."
```

---

### Task 10: Latency tracker

**Files:**
- Create: `echoline/pipeline/latency.py`
- Test: `tests/test_latency.py`

**Interfaces:**
- Produces: `LatencyTracker(window: int = 200)` with `record(captured_at: float, shown_at: float)`, `p50_ms() -> float | None`, `p95_ms() -> float | None`, `summary() -> str` (e.g. `"p50 182 ms · p95 340 ms"` or `"measuring…"`).

- [ ] **Step 1: Write the failing tests**

`tests/test_latency.py`:
```python
from echoline.pipeline.latency import LatencyTracker


def test_percentiles_from_recorded_latencies():
    tracker = LatencyTracker()
    for ms in range(1, 101):                 # 1..100 ms
        tracker.record(captured_at=10.0, shown_at=10.0 + ms / 1000)

    assert tracker.p50_ms() == 50
    assert tracker.p95_ms() == 95
    assert tracker.summary() == "p50 50 ms · p95 95 ms"


def test_empty_tracker_reports_measuring():
    tracker = LatencyTracker()

    assert tracker.p50_ms() is None
    assert tracker.summary() == "measuring…"


def test_only_recent_samples_count():
    tracker = LatencyTracker(window=3)
    for ms in (900, 900, 900, 10, 10, 10):
        tracker.record(0.0, ms / 1000)

    assert tracker.p95_ms() == 10
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_latency.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'echoline.pipeline.latency'`.

- [ ] **Step 3: Implement**

`echoline/pipeline/latency.py`:
```python
import collections
import math


class LatencyTracker:
    """Rolling sound-to-screen latency percentiles."""

    def __init__(self, window=200):
        self._samples = collections.deque(maxlen=window)

    def record(self, captured_at, shown_at):
        self._samples.append((shown_at - captured_at) * 1000)

    def _percentile(self, percent):
        if not self._samples:
            return None
        ordered = sorted(self._samples)
        return round(ordered[max(0, math.ceil(percent / 100 * len(ordered)) - 1)])

    def p50_ms(self):
        return self._percentile(50)

    def p95_ms(self):
        return self._percentile(95)

    def summary(self):
        if not self._samples:
            return "measuring…"
        return f"p50 {self.p50_ms()} ms · p95 {self.p95_ms()} ms"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_latency.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add echoline/pipeline/latency.py tests/test_latency.py
git commit -m "Add rolling sound-to-screen latency tracker"
```

---

### Task 11: QML rolling-caption overlay

**Files:**
- Create: `echoline/ui/__init__.py`, `echoline/ui/overlay.py`, `echoline/ui/qml/Overlay.qml`
- Test: `tests/test_overlay_qml.py`

**Interfaces:**
- Consumes: `CaptionModel` (Task 9).
- Produces:
  - `OverlayStatus(QObject)` with properties `state: str` (`"listening"`, `"no-device"`, `"lagging"`, `"loading"`), `latency: str`, `showLatency: bool`, each with a `<name>Changed` signal and a Python setter `set_state()`, `set_latency()`.
  - `load_overlay(engine: QQmlApplicationEngine, captions: CaptionModel, status: OverlayStatus, max_lines: int = 2) -> QQuickWindow` — sets context properties `captions`, `status`, `maxLines`, loads `Overlay.qml`, raises `RuntimeError` listing QML errors if loading fails.
  - The window `objectName` is `"overlay"`; the caption `ListView` `objectName` is `"captionList"`; the status pill `objectName` is `"statusPill"`.

Behavior: frameless, translucent, always on top, positioned bottom-center at 35% screen width; drag anywhere to move (`startSystemMove`); `Ctrl+Q` / `Esc` quit. Captions render bottom-up; the view height is exactly `maxLines` lines of text and always scrolls to the newest line with a 180 ms ease. New rows fade/slide in; removed rows fade out. Partial text uses 85% opacity, final 100%. The status pill appears for any state other than `listening`, and the latency line appears when `showLatency` is true.

- [ ] **Step 1: Write the failing tests**

`tests/test_overlay_qml.py`:
```python
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from echoline.captions.model import CaptionModel
from echoline.engine.base import Final, Partial
from echoline.ui.overlay import OverlayStatus, load_overlay

app = QGuiApplication.instance() or QGuiApplication([])


@pytest.fixture
def overlay():
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))
    captions, status = CaptionModel(), OverlayStatus()
    window = load_overlay(engine, captions, status, max_lines=2)
    yield window, captions, status, warnings
    window.close()
    engine.deleteLater()


def settle(seconds=0.4):
    """Process events long enough for the 180 ms scroll animation to finish."""
    import time
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)


def test_overlay_loads_without_qml_warnings(overlay):
    window, _, _, warnings = overlay
    settle()

    assert window.objectName() == "overlay"
    assert warnings == []


def test_captions_render_rows_from_the_model(overlay):
    window, captions, _, _ = overlay

    captions.apply([Final(0, "hello there."), Partial(1, "general")])
    settle()

    view = window.findChild(QObject, "captionList")
    assert view.property("count") == 2


def test_long_utterance_stays_within_line_budget(overlay):
    window, captions, _, _ = overlay
    view = window.findChild(QObject, "captionList")
    height_before = view.property("height")

    captions.apply([Partial(0, " ".join(["monologue"] * 400))])
    settle()

    assert view.property("height") == height_before
    assert view.property("atYEnd")


def test_status_pill_shows_only_when_not_listening(overlay):
    window, _, status, _ = overlay
    pill = window.findChild(QObject, "statusPill")

    status.set_state("listening")
    settle()
    assert not pill.property("visible")

    status.set_state("no-device")
    settle()
    assert pill.property("visible")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_overlay_qml.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'echoline.ui'`.

- [ ] **Step 3: Implement**

`echoline/ui/__init__.py`: empty file.

`echoline/ui/overlay.py`:
```python
from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal

QML_DIR = Path(__file__).parent / "qml"


class OverlayStatus(QObject):
    stateChanged = Signal()
    latencyChanged = Signal()
    showLatencyChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = "loading"
        self._latency = ""
        self._show_latency = False

    def _get_state(self):
        return self._state

    def set_state(self, value):
        if value != self._state:
            self._state = value
            self.stateChanged.emit()

    def _get_latency(self):
        return self._latency

    def set_latency(self, value):
        if value != self._latency:
            self._latency = value
            self.latencyChanged.emit()

    def _get_show_latency(self):
        return self._show_latency

    def set_show_latency(self, value):
        if value != self._show_latency:
            self._show_latency = value
            self.showLatencyChanged.emit()

    state = Property(str, _get_state, notify=stateChanged)
    latency = Property(str, _get_latency, notify=latencyChanged)
    showLatency = Property(bool, _get_show_latency, notify=showLatencyChanged)


def load_overlay(engine, captions, status, max_lines=2):
    context = engine.rootContext()
    context.setContextProperty("captions", captions)
    context.setContextProperty("status", status)
    context.setContextProperty("maxLines", max_lines)
    errors = []
    engine.warnings.connect(lambda items: errors.extend(w.toString() for w in items))
    engine.load(QUrl.fromLocalFile(str(QML_DIR / "Overlay.qml")))
    if not engine.rootObjects():
        raise RuntimeError("Could not load Overlay.qml:\n" + "\n".join(errors))
    return engine.rootObjects()[0]
```

`echoline/ui/qml/Overlay.qml`:
```qml
import QtQuick
import QtQuick.Window

Window {
    id: overlay
    objectName: "overlay"
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
    color: "transparent"
    visible: true
    width: Screen.width * 0.35
    height: panel.implicitHeight
    x: (Screen.width - width) / 2
    y: Screen.height * 0.85 - height / 2

    readonly property int fontSize: 26
    readonly property real lineHeight: metrics.height * 1.15

    FontMetrics { id: metrics; font.pixelSize: overlay.fontSize; font.family: "Segoe UI" }

    Shortcut { sequences: ["Ctrl+Q", "Escape"]; onActivated: Qt.quit() }

    Rectangle {
        id: panel
        anchors.fill: parent
        implicitHeight: content.implicitHeight + 24
        radius: 14
        color: Qt.rgba(0, 0, 0, 0.72)

        DragHandler { target: null; onActiveChanged: if (active) overlay.startSystemMove() }

        Column {
            id: content
            anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 18 }
            spacing: 4

            Rectangle {
                id: statusPill
                objectName: "statusPill"
                visible: status.state !== "listening"
                radius: height / 2
                color: status.state === "no-device" ? "#b3261e" : "#5a5a5a"
                width: statusText.implicitWidth + 20
                height: statusText.implicitHeight + 6
                anchors.horizontalCenter: parent.horizontalCenter
                Text {
                    id: statusText
                    anchors.centerIn: parent
                    color: "white"
                    font.pixelSize: 13
                    text: ({ "loading": "Loading speech model…", "no-device": "No audio device",
                             "lagging": "Catching up…" })[status.state] || status.state
                }
            }

            ListView {
                id: captionList
                objectName: "captionList"
                width: parent.width
                height: overlay.lineHeight * maxLines
                clip: true
                interactive: false
                model: captions
                spacing: 0

                onContentHeightChanged: scrollToEnd.restart()
                onCountChanged: scrollToEnd.restart()
                Timer { id: scrollToEnd; interval: 0; onTriggered: captionList.positionViewAtEnd() }
                Behavior on contentY { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }

                delegate: Text {
                    required property var model
                    width: captionList.width
                    wrapMode: Text.Wrap
                    horizontalAlignment: Text.AlignHCenter
                    color: "white"
                    opacity: model.final ? 1.0 : 0.85
                    font.pixelSize: overlay.fontSize
                    font.family: "Segoe UI"
                    lineHeight: 1.15
                    style: Text.Outline
                    styleColor: Qt.rgba(0, 0, 0, 0.6)
                    text: model.text
                    Behavior on opacity { NumberAnimation { duration: 120 } }
                }

                add: Transition {
                    NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 160 }
                    NumberAnimation { property: "y"; from: captionList.height; duration: 180; easing.type: Easing.OutCubic }
                }
                remove: Transition { NumberAnimation { property: "opacity"; to: 0; duration: 160 } }
                displaced: Transition { NumberAnimation { property: "y"; duration: 180; easing.type: Easing.OutCubic } }
            }

            Text {
                visible: status.showLatency
                anchors.horizontalCenter: parent.horizontalCenter
                color: "#bbbbbb"
                font.pixelSize: 11
                text: status.latency
            }
        }
    }
}
```

The delegate reads roles through `required property var model` because a `required property string text` would clash with `Text.text`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_overlay_qml.py -v`
Expected: 4 passed, and `test_overlay_loads_without_qml_warnings` reports no warnings. Fix any QML warning before continuing.

- [ ] **Step 5: Commit**

```bash
git add echoline/ui tests/test_overlay_qml.py
git commit -m "Add QML rolling-caption overlay" -m "GPU-rendered window that shows the newest caption lines at a fixed height, animates new and finished lines, and shows a status pill when audio or the engine needs attention."
```

---

### Task 12: Wire the app and entry point

**Files:**
- Create: `echoline/app.py`, `echoline/__main__.py`
- Test: `tests/test_echoline_app.py`

**Interfaces:**
- Consumes: `LoopbackSource` (7), `EngineWorker` (8), `CaptionModel` (9), `LatencyTracker` (10), `OverlayStatus`, `load_overlay` (11), `MoonshineEngine.load` (1).
- Produces:
  - `EchoLineApp(source, engine_factory: Callable[[], SpeechEngine], show_latency: bool = False)` with `start()`, `shutdown()`, and attributes `captions`, `status`, `latency`, `window`.
  - `echoline.__main__.main(argv=None) -> int` — parses `--model {tiny,small,medium}` (default from Task 5's decision, `DEFAULT_MODEL` constant) and `--show-latency`; runs the Qt event loop; returns the exit code.

Threading: the engine factory runs on a background thread (model load can take seconds; status shows `loading` meanwhile). Audio callbacks push into `EngineWorker`. Worker events reach the GUI thread through `Bridge.events` (a `Signal(object, object)` connected with `Qt.QueuedConnection`); the GUI slot applies them to `CaptionModel` and records latency on the next `frameSwapped`.

- [ ] **Step 1: Write the failing tests**

`tests/test_echoline_app.py`:
```python
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import time

import numpy as np
import pytest
from PySide6.QtCore import QObject
from PySide6.QtGui import QGuiApplication

from echoline.app import EchoLineApp
from echoline.engine.base import Final, Partial

app = QGuiApplication.instance() or QGuiApplication([])


class FakeSource:
    name = "fake"

    def start(self, on_audio, on_status):
        self.on_audio, self.on_status = on_audio, on_status
        on_status("listening")

    def stop(self):
        self.stopped = True


class EchoEngine:
    def __init__(self):
        self.count = 0

    def feed(self, samples):
        self.count += 1
        return [Partial(0, f"word {self.count}")]

    def flush(self):
        return [Final(0, "done.")]


def wait_until(condition, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    return False


@pytest.fixture
def running():
    source = FakeSource()
    echoline = EchoLineApp(source, EchoEngine, show_latency=True)
    echoline.start()
    assert wait_until(lambda: echoline.status.property("state") == "listening")
    yield echoline, source
    echoline.shutdown()


def test_audio_flows_through_to_caption_rows(running):
    echoline, source = running

    source.on_audio(np.zeros(480, np.float32), time.monotonic())

    assert wait_until(lambda: echoline.captions.rowCount() == 1)


def test_latency_is_measured_once_text_is_on_screen(running):
    echoline, source = running

    source.on_audio(np.zeros(480, np.float32), time.monotonic())

    assert wait_until(lambda: echoline.latency.p50_ms() is not None)
    assert echoline.latency.p50_ms() < 1000


def test_status_shows_audio_errors(running):
    echoline, source = running

    source.on_status("no-device")

    assert wait_until(lambda: echoline.status.property("state") == "no-device")


def test_shutdown_stops_audio_and_shows_last_final(running):
    echoline, source = running
    source.on_audio(np.zeros(480, np.float32), time.monotonic())
    wait_until(lambda: echoline.captions.rowCount() == 1)

    echoline.shutdown()
    app.processEvents()

    assert source.stopped
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_echoline_app.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'echoline.app'`.

- [ ] **Step 3: Implement**

`echoline/app.py`:
```python
import threading
import time

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtQml import QQmlApplicationEngine

from .captions.model import CaptionModel
from .pipeline.latency import LatencyTracker
from .pipeline.worker import EngineWorker
from .ui.overlay import OverlayStatus, load_overlay


class Bridge(QObject):
    """Carries worker-thread callbacks onto the GUI thread."""
    events = Signal(object, object)      # (events, captured_at)
    status = Signal(str)
    engine_ready = Signal(object)


class EchoLineApp:
    def __init__(self, source, engine_factory, show_latency=False):
        self.source = source
        self.engine_factory = engine_factory
        self.captions = CaptionModel()
        self.status = OverlayStatus()
        self.status.set_show_latency(show_latency)
        self.latency = LatencyTracker()
        self.worker = None
        self._source_state = "listening"
        self._pending_capture = None

        self.bridge = Bridge()
        self.bridge.events.connect(self._show_events, Qt.QueuedConnection)
        self.bridge.status.connect(self._on_status, Qt.QueuedConnection)
        self.bridge.engine_ready.connect(self._on_engine_ready, Qt.QueuedConnection)

        self.qml = QQmlApplicationEngine()
        self.window = load_overlay(self.qml, self.captions, self.status)
        self.window.frameSwapped.connect(self._on_frame_shown, Qt.DirectConnection)

    def start(self):
        self.status.set_state("loading")
        threading.Thread(target=lambda: self.bridge.engine_ready.emit(self.engine_factory()),
                         name="engine-load", daemon=True).start()

    def _on_engine_ready(self, engine):
        self.worker = EngineWorker(
            engine,
            on_events=lambda events, captured_at: self.bridge.events.emit(events, captured_at),
            on_lagging=lambda lagging: self.bridge.status.emit("lagging" if lagging else "caught-up"))
        self.worker.start()
        self.source.start(self.worker.push, self.bridge.status.emit)

    def _on_status(self, state):
        if state in ("listening", "no-device"):
            self._source_state = state
        self.status.set_state(self._source_state if state == "caught-up" else state)

    def _show_events(self, events, captured_at):
        self.captions.apply(events)
        if captured_at is not None:
            self._pending_capture = captured_at
            self.window.update()

    def _on_frame_shown(self):
        if self._pending_capture is not None:
            self.latency.record(self._pending_capture, time.monotonic())
            self._pending_capture = None
            self.status.set_latency(self.latency.summary())

    def shutdown(self):
        self.source.stop()
        if self.worker is not None:
            self.worker.stop()
            self.worker = None
```

Note: `frameSwapped` fires on the render thread; it only reads/writes `_pending_capture` and the tracker, and `set_latency` emits a signal that QML receives queued, so no GUI objects are touched off-thread. If Step 4 shows the latency test flaking on the offscreen platform (no real frame swaps), fall back to recording in `_show_events` right after `captions.apply` and note it in the commit.

`echoline/__main__.py`:
```python
import argparse
import sys

from PySide6.QtGui import QGuiApplication

DEFAULT_MODEL = "small"   # from docs/benchmarks/2026-10-engine-bench.md; update if the benchmark chose otherwise


def main(argv=None):
    parser = argparse.ArgumentParser(prog="echoline", description="Live captions for anything playing on your PC.")
    parser.add_argument("--model", choices=["tiny", "small", "medium"], default=DEFAULT_MODEL)
    parser.add_argument("--show-latency", action="store_true", help="show p50/p95 caption latency")
    args = parser.parse_args(argv)

    qt_app = QGuiApplication(sys.argv[:1])
    qt_app.setApplicationName("EchoLine")

    from moonshine_voice import ModelArch

    from .app import EchoLineApp
    from .audio.loopback import LoopbackSource
    from .engine.moonshine_engine import MoonshineEngine

    arch = {"tiny": ModelArch.TINY_STREAMING, "small": ModelArch.SMALL_STREAMING,
            "medium": ModelArch.MEDIUM_STREAMING}[args.model]
    echoline = EchoLineApp(LoopbackSource(), lambda: MoonshineEngine.load(arch), show_latency=args.show_latency)
    echoline.start()
    try:
        return qt_app.exec()
    finally:
        echoline.shutdown()


if __name__ == "__main__":
    sys.exit(main())
```

Set `DEFAULT_MODEL` to the model chosen in Task 5.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_echoline_app.py -v`
Expected: 4 passed.
Run the full suite: `.venv/Scripts/python -m pytest`
Expected: all passed.

- [ ] **Step 5: Manual end-to-end check**

Run: `.venv/Scripts/python -m echoline --show-latency` and play a YouTube video with speech.
Expected: the "Loading speech model…" pill, then live captions; partial words settle in place; finished lines slide up; the latency line reads p50 < 300 ms after ~30 s. Unplug or switch the output device: captions continue on the new device (or "No audio device" appears and clears when one returns). `Esc` quits cleanly.

- [ ] **Step 6: Commit**

```bash
git add echoline/app.py echoline/__main__.py tests/test_echoline_app.py
git commit -m "Run EchoLine on the new loopback, Moonshine and QML pipeline" -m "python -m echoline loads the model in the background, captures system audio, and shows rolling captions; --show-latency displays live p50/p95 sound-to-screen latency."
```

---

### Task 13: Remove the legacy Widgets app

**Files:**
- Delete: `app.py`, `main.py`, `audio/`, `ui/`, `utils/`, `tests/test_app.py`, `tests/test_main.py`, `tests/test_audio_capture.py`, `tests/test_overlay_ui.py`, `tests/test_caption_buffer.py`
- Move: `transcription/speech_recognition.py` → `echoline/engine/vosk_recognizer.py`; `tests/test_speech_recognition.py` imports updated
- Modify: `metrics/audio_ml_evaluator.py` (import path), `tests/test_audio_ml_evaluator.py` (import path), `requirements.txt` (drop `sounddevice`), `README.md`

**Interfaces:**
- Consumes: everything above; nothing new is produced.

- [ ] **Step 1: Move the Vosk recognizer used by the evaluator**

```bash
git mv transcription/speech_recognition.py echoline/engine/vosk_recognizer.py
```
In `metrics/audio_ml_evaluator.py`, `tests/test_audio_ml_evaluator.py` and `tests/test_speech_recognition.py`, replace `from transcription.speech_recognition import SpeechRecognizer` with `from echoline.engine.vosk_recognizer import SpeechRecognizer`.

Run: `.venv/Scripts/python -m pytest tests/test_audio_ml_evaluator.py tests/test_speech_recognition.py -v`
Expected: all passed.

- [ ] **Step 2: Delete the legacy app and its tests**

```bash
git rm -r app.py main.py audio ui utils transcription tests/test_app.py tests/test_main.py tests/test_audio_capture.py tests/test_overlay_ui.py tests/test_caption_buffer.py
```
Remove the `sounddevice==0.4.6` line from `requirements.txt` (moonshine-voice still installs it for its own CLI; EchoLine no longer imports it).

Check nothing still imports the removed modules:
```bash
grep -rnE "^(from|import) (app|audio|ui|utils|transcription)\b" --include=*.py . | grep -v .venv
```
Expected: no output.

- [ ] **Step 3: Update the README**

In `README.md`:
- Requirements: replace "Python 3.8 or higher" with "Python 3.10 or higher"; delete "Stereo Mix enabled in sound settings".
- Installation step 3 (download Vosk model): replace with "The speech model downloads automatically on first run (about 50–200 MB depending on the model)."
- Run step: `python -m echoline` (add `--show-latency` to see caption latency, `--model tiny` on slower PCs).
- Troubleshooting: replace the Stereo Mix and Vosk model sections with "No captions: check that sound is playing through your default output device."
- Features: "Real-time captions of any audio playing on your PC, no Stereo Mix needed".
- Badges: Python 3.10+; replace the Vosk badge with Moonshine.

- [ ] **Step 4: Run the full suite**

Run: `.venv/Scripts/python -m pytest`
Expected: all passed. Run `.venv/Scripts/python -m pytest -m model` as well: all passed.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Remove the legacy Qt Widgets app" -m "python -m echoline replaces main.py. The Vosk recognizer used by the metrics evaluator moves into echoline.engine; sounddevice is no longer used directly. README describes loopback capture and automatic model download."
```

- [ ] **Step 6: Refresh the code graph**

Run: `graphify update .` (not committed; graphify-out is gitignored).

---

## Spec coverage (self-review)

| Spec item | Task |
|---|---|
| M0: compare Moonshine Tiny/Small and Vosk with data | 3, 4, 5 |
| `AudioSource` interface, loopback, device-change reopen | 7 |
| 16 kHz mono float32, 20–50 ms blocks | 6, 7 (30 ms) |
| `SpeechEngine`, `Partial`/`Final`, Moonshine + Vosk | 1, 2 |
| Backlog > 1 s drops oldest, lagging status | 8, 12 |
| `CaptionModel` as `QAbstractListModel`, bounded history | 9 |
| Rolling mode QML overlay, status pill | 11 |
| Latency measured live, p50/p95 debug display | 10, 12 |
| Move code into `echoline/`, replace Widgets UI | 12, 13 |
| No audio device → status + retry | 7, 12 |
| Engine errors do not kill captions | 8 |
| MicrophoneSource, settings, themes, tray, hotkeys, onboarding, packaging | Out of M0/M1 scope (M2–M5 plans) |

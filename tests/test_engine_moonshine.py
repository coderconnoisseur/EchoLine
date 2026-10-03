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


def test_close_releases_the_native_transcriber():
    class Closable:
        closed = False

        def close(self):
            self.closed = True

    stream, transcriber = FakeStream([]), Closable()
    stream.close = lambda: setattr(stream, "closed", True)
    engine = MoonshineEngine(stream)
    engine._transcriber = transcriber

    engine.close()

    assert stream.closed and transcriber.closed


def test_load_uses_streaming_settings_that_keep_cost_flat(monkeypatch):
    # By default Moonshine returns every line's audio on every update, so each
    # update got slower as the session grew until captions fell behind.
    import moonshine_voice

    created = {}

    class FakeTranscriber:
        def __init__(self, model_path, model_arch, update_interval, options):
            created.update(update_interval=update_interval, options=options)

        def create_stream(self, update_interval):
            created["stream_interval"] = update_interval
            return FakeStream([])

    monkeypatch.setattr(moonshine_voice, "Transcriber", FakeTranscriber, raising=False)
    monkeypatch.setattr(moonshine_voice, "get_model_for_language", lambda language, arch: ("path", arch))

    MoonshineEngine.load(moonshine_voice.ModelArch.TINY_STREAMING)

    assert created["options"]["return_audio_data"] == "false"
    # Capping lines shorter than Moonshine's default split sentences and doubled WER.
    assert "vad_max_segment_duration" not in created["options"]
    # Moonshine's native layer also gates re-transcription (0.5 s by default),
    # which capped updates at ~1.4/s whatever the Python interval was.
    assert created["options"]["transcription_interval"] == "0.1"
    assert created["update_interval"] == created["stream_interval"] == 0.1


def test_flush_restarts_the_stream_so_feeding_can_continue():
    stream = FakeStream([[LineTextChanged(Line(1, "after", False))]])
    engine = MoonshineEngine(stream)
    stream.started = False

    engine.flush()

    assert stream.started
    assert engine.feed(np.zeros(1, np.float32)) == [Partial(0, "after")]

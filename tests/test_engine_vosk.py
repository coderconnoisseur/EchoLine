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

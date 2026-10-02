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

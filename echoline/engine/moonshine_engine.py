import numpy as np

from .base import SAMPLE_RATE, Event, Final, Partial


def preload_native_library():
    """Load moonshine.dll now. It fails to initialise (WinError 1114) if Qt is loaded first."""
    from moonshine_voice.moonshine_api import _MoonshineLib

    _MoonshineLib()


class MoonshineEngine:
    """Adapts a moonshine_voice Stream to EchoLine's Partial/Final events."""

    def __init__(self, stream):
        self._stream = stream
        self._ids = {}       # Moonshine line id -> small sequential id
        self._pending = []
        stream.add_listener(self._on_event)
        stream.start()

    # By default every update returns every past line's audio, so update cost
    # grows with session length until captions fall behind. We only need text.
    # The native layer only re-transcribes after transcription_interval seconds of new
    # audio (0.5 by default), which held captions to ~1.4 updates a second.
    STREAMING_OPTIONS = {"return_audio_data": "false", "transcription_interval": "0.1"}

    @classmethod
    def load(cls, model_arch, update_interval=0.1, options=None):
        from moonshine_voice import Transcriber, get_model_for_language

        path, arch = get_model_for_language("en", model_arch)
        transcriber = Transcriber(model_path=path, model_arch=arch, update_interval=update_interval,
                                  options={**cls.STREAMING_OPTIONS, **(options or {})})
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

    def close(self):
        """Release the native stream and model; the engine is unusable afterwards."""
        self._stream.close()
        transcriber = getattr(self, "_transcriber", None)
        if transcriber is not None:
            transcriber.close()

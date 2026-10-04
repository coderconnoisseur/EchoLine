from PySide6.QtCore import Property, QObject, QTimer

from ..captions.model import CaptionModel
from ..engine.base import Final, Partial


class SampleCaptions(QObject):
    """A short scripted sentence for the settings preview, replayed in a loop."""

    # One entry per step: words arriving, a correction, a final, then a pause.
    SCRIPT = [
        [Partial(0, "It was")], [Partial(0, "It was the best")], [Partial(0, "It was the beast of")],
        [Partial(0, "It was the best of times,")], [Partial(0, "It was the best of times, it was")],
        [Partial(0, "It was the best of times, it was the worst of times")],
        [Final(0, "It was the best of times, it was the worst of times.")], [], [], [], [],
    ]

    def __init__(self, step_ms=350, parent=None):
        super().__init__(parent)
        self._model = CaptionModel(max_utterances=2, settle_after_ms=500, parent=self)
        self._timer = QTimer(self, interval=step_ms)
        self._timer.timeout.connect(self._step)
        self._index = 0
        self._utterance = 0
        self.loops = 0

    captions = Property(QObject, lambda self: self._model, constant=True)

    @property
    def running(self):
        return self._timer.isActive()

    def start(self):
        self._timer.start()

    def stop(self):
        self._timer.stop()

    def _step(self):
        events = self.SCRIPT[self._index]
        # A fresh utterance id per loop so the preview shows a new line each time.
        self._model.apply([type(e)(self._utterance, e.text) for e in events])
        self._index += 1
        if self._index == len(self.SCRIPT):
            self._index = 0
            self._utterance += 1
            self.loops += 1

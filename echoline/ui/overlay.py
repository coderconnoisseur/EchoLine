from pathlib import Path

import shiboken6
from PySide6.QtCore import Property, QObject, QUrl, Signal
from PySide6.QtQuick import QQuickWindow

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
    # PySide types the QML root as a plain QWindow; rewrap it to reach QQuickWindow API.
    root = engine.rootObjects()[0]
    return shiboken6.wrapInstance(shiboken6.getCppPointer(root)[0], QQuickWindow)

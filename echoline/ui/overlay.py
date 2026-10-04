from pathlib import Path

import shiboken6
from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal
from PySide6.QtQuick import QQuickWindow

from .motion import Motion, animations_enabled

QML_DIR = Path(__file__).parent / "qml"


class OverlayStatus(QObject):
    stateChanged = Signal()
    latencyChanged = Signal()
    showLatencyChanged = Signal()
    noticeChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = "loading"
        self._latency = ""
        self._show_latency = False
        self._notice = ""
        self._notice_timer = QTimer(self, singleShot=True)
        self._notice_timer.timeout.connect(lambda: self._set_notice_text(""))

    def _get_notice(self):
        return self._notice

    def _set_notice_text(self, text):
        if text != self._notice:
            self._notice = text
            self.noticeChanged.emit()

    def set_notice(self, text, ms=6000):
        """Show a one-off message in the status pill for `ms` milliseconds."""
        self._set_notice_text(text)
        self._notice_timer.start(ms)

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
    notice = Property(str, _get_notice, notify=noticeChanged)


def load_overlay(engine, captions, status, settings_store, controller=None, motion=None):
    context = engine.rootContext()
    engine._motion = motion or Motion(animations_enabled(), engine)     # kept alive with the engine
    context.setContextProperty("motion", engine._motion)
    context.setContextProperty("captions", captions)
    context.setContextProperty("status", status)
    context.setContextProperty("settingsStore", settings_store)
    context.setContextProperty("controller", controller)
    errors = []
    engine.warnings.connect(lambda items: errors.extend(w.toString() for w in items))
    engine.load(QUrl.fromLocalFile(str(QML_DIR / "Overlay.qml")))
    if not engine.rootObjects():
        raise RuntimeError("Could not load Overlay.qml:\n" + "\n".join(errors))
    # PySide types the QML root as a plain QWindow; rewrap it to reach QQuickWindow API.
    root = engine.rootObjects()[0]
    return shiboken6.wrapInstance(shiboken6.getCppPointer(root)[0], QQuickWindow)

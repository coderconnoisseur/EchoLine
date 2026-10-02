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

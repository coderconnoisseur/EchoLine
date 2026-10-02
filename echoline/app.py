import threading
import time
import traceback

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
    frame_shown = Signal(float)          # monotonic time a frame reached the screen


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
        self._closed = False

        self.bridge = Bridge()
        self.bridge.events.connect(self._show_events, Qt.QueuedConnection)
        self.bridge.status.connect(self._on_status, Qt.QueuedConnection)
        self.bridge.engine_ready.connect(self._on_engine_ready, Qt.QueuedConnection)
        self.bridge.frame_shown.connect(self._record_latency, Qt.QueuedConnection)

        self.qml = QQmlApplicationEngine()
        self.window = load_overlay(self.qml, self.captions, self.status)
        self.window.frameSwapped.connect(self._on_frame_shown, Qt.DirectConnection)

    def start(self):
        self.status.set_state("loading")
        threading.Thread(target=self._load_engine, name="engine-load", daemon=True).start()

    def _load_engine(self):
        try:
            engine = self.engine_factory()
        except Exception:
            traceback.print_exc()
            self.bridge.status.emit("model-error")
            return
        self.bridge.engine_ready.emit(engine)

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
        # Runs on Qt's render thread: only timestamp here, update the UI on the GUI thread.
        if self._pending_capture is not None:
            self.bridge.frame_shown.emit(time.monotonic())

    def _record_latency(self, shown_at):
        if self._pending_capture is not None:
            self.latency.record(self._pending_capture, shown_at)
            self._pending_capture = None
            self.status.set_latency(self.latency.summary())

    def shutdown(self):
        if self._closed:
            return
        self._closed = True
        self.source.stop()
        if self.worker is not None:
            self.worker.stop()
            self.worker = None
        # Stop rendering before this object goes away: frameSwapped fires on the
        # render thread and would call into a freed EchoLineApp.
        self.window.frameSwapped.disconnect(self._on_frame_shown)
        self.window.close()
        self.qml.deleteLater()

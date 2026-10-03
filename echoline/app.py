import threading
import time
import traceback

import shiboken6
from PySide6.QtCore import Property, QCoreApplication, QObject, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QFontDatabase, QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow

from .captions.model import CaptionModel
from .pipeline.latency import LatencyTracker
from .pipeline.worker import EngineWorker
from .ui.fonts import caption_fonts
from .ui.overlay import QML_DIR, OverlayStatus, load_overlay
from .ui.blur import set_acrylic
from .ui.placement import clamp_to_screen, snap_position


class Bridge(QObject):
    """Carries worker-thread callbacks onto the GUI thread."""
    events = Signal(object, object)      # (events, captured_at)
    status = Signal(str)
    engine_ready = Signal(object)
    frame_shown = Signal(float)          # monotonic time a frame reached the screen


class Controller(QObject):
    """Actions the QML UI can trigger."""

    def __init__(self, app):
        super().__init__()
        self._app = app

    @Slot(str)
    def snap(self, where):
        self._app.snap(where)

    @Slot()
    def dragStarted(self):
        self._app.release_snap()

    @Slot()
    def openSettings(self):
        self._app.open_settings()

    @Slot()
    def quit(self):
        QCoreApplication.quit()

    def _get_fonts(self):
        return caption_fonts(QFontDatabase.families())

    fonts = Property(list, _get_fonts, constant=True)


class EchoLineApp:
    def __init__(self, source, engine_factory, settings_store, show_latency=False, settings_reset=False):
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
        self._settings_reset = settings_reset
        self._notice_active = False
        self.settings_window = None

        self.bridge = Bridge()
        self.bridge.events.connect(self._show_events, Qt.QueuedConnection)
        self.bridge.status.connect(self._on_status, Qt.QueuedConnection)
        self.bridge.engine_ready.connect(self._on_engine_ready, Qt.QueuedConnection)
        self.bridge.frame_shown.connect(self._record_latency, Qt.QueuedConnection)

        self.settings_store = settings_store
        self.controller = Controller(self)
        self.qml = QQmlApplicationEngine()
        self.window = load_overlay(self.qml, self.captions, self.status, settings_store, self.controller)
        self.window.frameSwapped.connect(self._on_frame_shown, Qt.DirectConnection)

        self._save_position = QTimer(singleShot=True, interval=500)
        self._save_position.timeout.connect(
            lambda: self.settings_store.setValue("position", [self.window.x(), self.window.y()]))
        self._anchor = None          # "top" | "center" | "bottom" after a snap, until dragged
        self._place_window()
        self.window.widthChanged.connect(self._keep_anchor)
        self.window.heightChanged.connect(self._keep_anchor)
        self.window.xChanged.connect(self._save_position.start)
        self.window.yChanged.connect(self._save_position.start)

        self._apply_blur()
        settings_store.valuesChanged.connect(self._apply_blur)

    def _apply_blur(self):
        enabled = self.settings_store.settings.blur_behind
        if enabled != getattr(self, "_blur_applied", None):
            self._blur_applied = enabled
            set_acrylic(int(self.window.winId()), enabled)

    def _screen_rects(self):
        primary = QGuiApplication.primaryScreen()
        screens = [primary] + [s for s in QGuiApplication.screens() if s is not primary]
        return [(g.x(), g.y(), g.width(), g.height()) for g in (s.availableGeometry() for s in screens)]

    def _place_window(self):
        if self.settings_store.settings.position is None:
            self.snap("bottom")          # first run: sit at the bottom and stay there as it grows
            return
        size = (self.window.width(), self.window.height())
        x, y = clamp_to_screen(self.settings_store.settings.position, size, self._screen_rects())
        self.window.setPosition(x, y)

    def snap(self, where):
        self._anchor = where
        g = self.window.screen().availableGeometry()
        size = (self.window.width(), self.window.height())
        x, y = snap_position((g.x(), g.y(), g.width(), g.height()), size, where)
        self.window.setPosition(x, y)

    def _keep_anchor(self):
        # A snapped overlay stays centered / on its edge as fonts, lines or width change.
        if self._anchor:
            self.snap(self._anchor)

    def release_snap(self):
        self._anchor = None

    def start(self):
        self.status.set_state("loading")
        if self._settings_reset:
            self._notice_active = True
            self.status.set_state("settings-reset")
            QTimer.singleShot(6000, self._end_notice)
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
        if self._notice_active:
            return      # keep the notice up; _end_notice shows the latest state
        self.status.set_state(self._source_state if state == "caught-up" else state)

    def _end_notice(self):
        self._notice_active = False
        if not self._closed:
            self.status.set_state(self._source_state if self.worker else "loading")

    def open_settings(self):
        if self.settings_window is None:
            before = len(self.qml.rootObjects())
            self.qml.load(QUrl.fromLocalFile(str(QML_DIR / "Settings.qml")))
            root = self.qml.rootObjects()[before]
            self.settings_window = shiboken6.wrapInstance(shiboken6.getCppPointer(root)[0], QQuickWindow)
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.requestActivate()
        return self.settings_window

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
        self._save_position.stop()
        self.settings_store.setValue("position", [self.window.x(), self.window.y()])
        self.settings_store.save_now()
        self.source.stop()
        if self.worker is not None:
            self.worker.stop()
            self.worker = None
        # Stop rendering before this object goes away: frameSwapped fires on the
        # render thread and would call into a freed EchoLineApp.
        self.window.frameSwapped.disconnect(self._on_frame_shown)
        self.window.close()
        if self.settings_window is not None:
            self.settings_window.close()
        self.qml.deleteLater()

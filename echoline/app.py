import threading
import time
import traceback

import shiboken6
from PySide6.QtCore import Property, QCoreApplication, QObject, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QFontDatabase, QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow

from .captions.model import CaptionModel
from .hotkeys import HotkeyManager
from .pipeline.latency import LatencyTracker
from .pipeline.worker import EngineWorker
from .ui.fonts import caption_fonts
from .ui.icon import app_icon
from .ui.tray import TrayIcon
from .ui.overlay import QML_DIR, OverlayStatus, load_overlay
from .ui.blur import set_blur
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
        self._app.quit()

    @Slot()
    def hide(self):
        self._app.set_visible(False)

    pausedChanged = Signal()
    sourceChanged = Signal()

    @Slot()
    def togglePause(self):
        self._app.set_paused(not self._app.paused)

    @Slot()
    def toggleSource(self):
        current = self._app.settings_store.settings.audio_source
        self._app.set_source("microphone" if current == "system" else "system")

    def _get_paused(self):
        return self._app.paused

    def _get_source_name(self):
        return self._app.source.name

    paused = Property(bool, _get_paused, notify=pausedChanged)
    sourceName = Property(str, _get_source_name, notify=sourceChanged)

    def _get_fonts(self):
        return caption_fonts(QFontDatabase.families())

    fonts = Property(list, _get_fonts, constant=True)


class EchoLineApp:
    def __init__(self, source_factory, engine_factory, settings_store, show_latency=False, settings_reset=False):
        self.source_factory = source_factory
        self.source = source_factory(settings_store.settings.audio_source)
        self.paused = False
        self.visible = True
        self.tray = None
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
        self._save_width = QTimer(singleShot=True, interval=500)
        self._save_width.timeout.connect(self._store_width)
        self.window.widthChanged.connect(self._save_width.start)
        self._anchor = None          # "top" | "center" | "bottom" after a snap, until dragged
        self._place_window()
        self.window.widthChanged.connect(self._keep_anchor)
        self.window.heightChanged.connect(self._keep_anchor)
        self.window.xChanged.connect(self._save_position.start)
        self.window.yChanged.connect(self._save_position.start)

        self._blur_applied = None
        self._apply_blur()
        settings_store.valuesChanged.connect(self._apply_blur)

        self.window.setIcon(app_icon())
        self.window.setFlag(Qt.WindowTransparentForInput, settings_store.settings.click_through)
        self.tray = TrayIcon(self)
        settings_store.valuesChanged.connect(self._refresh_tray)

        # Thread-level hotkeys (no window): WM_HOTKEY arrives in this thread's queue.
        self.hotkeys = HotkeyManager(hwnd=None)
        QCoreApplication.instance().installNativeEventFilter(self.hotkeys)
        self._register_hotkeys()
        settings_store.valuesChanged.connect(self._hotkeys_changed)

    def _hotkey_texts(self):
        s = self.settings_store.settings
        return (s.hotkey_show_hide, s.hotkey_pause, s.hotkey_click_through)

    def _register_hotkeys(self):
        self._registered_hotkeys = self._hotkey_texts()
        self.hotkeys.unregister_all()
        s = self.settings_store.settings
        self.hotkeys.register("show_hide", s.hotkey_show_hide, lambda: self.set_visible(not self.visible))
        self.hotkeys.register("pause", s.hotkey_pause, lambda: self.set_paused(not self.paused))
        self.hotkeys.register("click_through", s.hotkey_click_through,
                              lambda: self.set_click_through(not self.settings_store.settings.click_through))
        if self.hotkeys.failed:
            keys = {"show_hide": s.hotkey_show_hide, "pause": s.hotkey_pause,
                    "click_through": s.hotkey_click_through}
            self.status.set_notice(f"Hotkey {keys[self.hotkeys.failed[0]]} is used by another app")

    def set_visible(self, visible):
        self.visible = visible
        self.window.setVisible(visible)
        self._refresh_tray()

    def quit(self):
        QCoreApplication.quit()

    def set_click_through(self, enabled):
        """Let clicks pass through the captions to the window below."""
        self.settings_store.setValue("click_through", enabled)
        self.window.setFlag(Qt.WindowTransparentForInput, enabled)
        if enabled:
            key = self.settings_store.settings.hotkey_click_through
            how = f"{key} or the tray icon" if key else "the tray icon"
            self.status.set_notice(f"Click-through on — use {how} to turn it off")
        self._refresh_tray()

    def _refresh_tray(self):
        if self.tray is not None:
            self.tray.refresh()

    def _hotkeys_changed(self):
        if self._hotkey_texts() != self._registered_hotkeys:
            self._register_hotkeys()
        self.window.widthChanged.connect(self._apply_blur)
        self.window.heightChanged.connect(self._apply_blur)

    def _apply_blur(self):
        settings = self.settings_store.settings
        scale = self.window.devicePixelRatio()
        size = (round(self.window.width() * scale), round(self.window.height() * scale))
        state = (settings.blur_behind, size, round(settings.corner_radius * scale))
        if not settings.blur_behind:
            state = (False, None, None)      # nothing to re-clip while blur is off
        if state != self._blur_applied:
            if state[0] or self._blur_applied is not None:
                set_blur(int(self.window.winId()), settings.blur_behind,
                         size, round(settings.corner_radius * scale))
            self._blur_applied = state

    def _store_width(self):
        # Widths set from the setting round back to the same percent, so this does not loop.
        percent = round(self.window.width() * 100 / self.window.screen().geometry().width())
        self.settings_store.setValue("width_percent", percent)

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
        self._start_source()

    def _start_source(self):
        self.source.start(self.worker.push, self.bridge.status.emit)

    def set_paused(self, paused):
        if paused == self.paused or self.worker is None:
            return
        self.paused = paused
        if paused:
            self.source.stop()
            self.worker.flush()
            self.status.set_state("paused")
        else:
            self._source_state = "listening"
            self.status.set_state("listening")
            self._start_source()
        self.controller.pausedChanged.emit()
        self._refresh_tray()

    def set_source(self, kind):
        if kind == self.settings_store.settings.audio_source:
            return
        self.settings_store.setValue("audio_source", kind)
        self.source.stop()
        self.source = self.source_factory(kind)
        if self.worker is not None and not self.paused:
            self._start_source()
        self.controller.sourceChanged.emit()
        self._refresh_tray()

    def _on_status(self, state):
        if state in ("listening", "no-device", "no-microphone"):
            self._source_state = state
        if self.paused and state != "model-error":
            return      # a late source status must not hide "Paused"
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
        self._save_width.stop()
        self.hotkeys.unregister_all()
        QCoreApplication.instance().removeNativeEventFilter(self.hotkeys)
        self.tray.hide()
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
        # Delete the QML engine now, not later: once the caller returns, Python frees
        # the store and models in arbitrary order and live bindings would read null.
        shiboken6.delete(self.qml)

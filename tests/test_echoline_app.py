import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import time

import numpy as np
import pytest
from PySide6.QtGui import QGuiApplication

from echoline.app import EchoLineApp
from echoline.engine.base import Final, Partial
from echoline.settings.model import Settings
from echoline.settings.store import SettingsStore

app = QGuiApplication.instance() or QGuiApplication([])


class FakeSource:
    name = "fake"

    def start(self, on_audio, on_status):
        self.on_audio, self.on_status = on_audio, on_status
        on_status("listening")

    def stop(self):
        self.stopped = True


class EchoEngine:
    def __init__(self):
        self.count = 0

    def feed(self, samples):
        self.count += 1
        return [Partial(0, f"word {self.count}")]

    def flush(self):
        return [Final(0, "done.")]


def wait_until(condition, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    return False


@pytest.fixture
def running(tmp_path):
    source = FakeSource()
    echoline = EchoLineApp(source, EchoEngine, SettingsStore(Settings(), tmp_path / "settings.json"),
                           show_latency=True)
    echoline.start()
    assert wait_until(lambda: echoline.status.property("state") == "listening")
    yield echoline, source
    echoline.shutdown()


def test_audio_flows_through_to_caption_rows(running):
    echoline, source = running

    source.on_audio(np.zeros(480, np.float32), time.monotonic())

    assert wait_until(lambda: echoline.captions.rowCount() == 1)


def test_latency_is_measured_once_text_is_on_screen(running):
    echoline, source = running

    source.on_audio(np.zeros(480, np.float32), time.monotonic())

    assert wait_until(lambda: echoline.latency.p50_ms() is not None)
    assert echoline.latency.p50_ms() < 1000


def test_status_shows_audio_errors(running):
    echoline, source = running

    source.on_status("no-device")

    assert wait_until(lambda: echoline.status.property("state") == "no-device")


def test_shutdown_stops_audio_and_shows_last_final(running):
    echoline, source = running
    source.on_audio(np.zeros(480, np.float32), time.monotonic())
    wait_until(lambda: echoline.captions.rowCount() == 1)

    echoline.shutdown()
    app.processEvents()

    assert source.stopped


def test_entry_point_loads_moonshine_before_qt():
    # moonshine.dll fails to initialise (WinError 1114) once Qt is loaded, so
    # the entry module must load it first. Runs in a fresh interpreter because
    # this test process already has Qt loaded.
    import subprocess
    import sys

    script = (
        "import echoline.__main__\n"
        "from PySide6.QtGui import QGuiApplication\n"
        "app = QGuiApplication([])\n"
        "from moonshine_voice.moonshine_api import _MoonshineLib\n"
        "_MoonshineLib()\n"
        "print('loaded')\n"
    )
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=60,
                            env={**os.environ, "QT_QPA_PLATFORM": "offscreen"})

    assert "loaded" in result.stdout, result.stderr[-500:]


def test_shutdown_closes_the_overlay_window(running):
    # A window left rendering after shutdown fires frameSwapped into a freed
    # EchoLineApp, crashing the process.
    echoline, _ = running

    echoline.shutdown()
    echoline.shutdown()                      # idempotent: safe to call twice

    assert not echoline.window.isVisible()


def test_latency_display_is_updated_on_the_gui_thread(running):
    # frameSwapped fires on Qt's render thread; touching QML-bound objects
    # there is unsafe, so the update must hop back to the GUI thread.
    import threading

    echoline, _ = running
    threads = []
    original = echoline.status.set_latency
    echoline.status.set_latency = lambda value: (threads.append(threading.current_thread()), original(value))
    echoline._pending_capture = time.monotonic()

    render_thread = threading.Thread(target=echoline._on_frame_shown)
    render_thread.start()
    render_thread.join()
    wait_until(lambda: threads)

    assert threads == [threading.main_thread()]


def test_failed_model_load_is_reported(tmp_path):
    def offline_engine():
        raise ConnectionError("could not download model")

    echoline = EchoLineApp(FakeSource(), offline_engine, SettingsStore(Settings(), tmp_path / "s.json"))
    echoline.start()
    try:
        assert wait_until(lambda: echoline.status.property("state") == "model-error")
    finally:
        echoline.shutdown()


def test_snap_moves_window_and_remembers_position(running):
    echoline, _ = running

    echoline.controller.snap("top")

    # Startup placement may already have saved a position; wait for the snapped one.
    assert wait_until(lambda: echoline.settings_store.settings.position
                      == [echoline.window.x(), echoline.window.y()], timeout=2)
    assert echoline.window.y() < 100


def test_shutdown_saves_pending_settings(tmp_path):
    from echoline.settings.model import load_settings

    path = tmp_path / "settings.json"
    store = SettingsStore(Settings(), path, save_delay_ms=60_000)
    echoline = EchoLineApp(FakeSource(), EchoEngine, store)
    store.setValue("font_size", 33)

    echoline.shutdown()

    assert load_settings(path)[0].font_size == 33


def test_reset_settings_are_announced(tmp_path):
    echoline = EchoLineApp(FakeSource(), EchoEngine, SettingsStore(Settings(), tmp_path / "s.json"),
                           settings_reset=True)
    echoline.start()
    try:
        assert wait_until(lambda: echoline.status.property("state") == "settings-reset")
        wait_until(lambda: False, timeout=0.3)
        assert echoline.status.property("state") == "settings-reset"     # not hidden by "listening"
    finally:
        echoline.shutdown()


def test_snap_stays_on_the_overlays_screen(running):
    # Snapping used to always jump to the primary monitor.
    echoline, _ = running
    echoline.window.setPosition(1366 + 200, 300)       # second monitor
    wait_until(lambda: echoline.window.x() > 1366)

    echoline.controller.snap("top")
    wait_until(lambda: False, timeout=0.2)

    assert echoline.window.x() > 1366


def test_snapped_overlay_stays_anchored_when_it_grows(running):
    # A bottom-snapped overlay grew downward into the taskbar when lines were added.
    echoline, _ = running
    echoline.controller.snap("bottom")
    wait_until(lambda: False, timeout=0.2)
    height, bottom = echoline.window.height(), echoline.window.y() + echoline.window.height()

    echoline.settings_store.setValue("line_count", 3)
    assert wait_until(lambda: echoline.window.height() > height, timeout=1)
    wait_until(lambda: False, timeout=0.2)

    assert echoline.window.y() + echoline.window.height() == bottom


def test_dragging_releases_the_snap(running):
    echoline, _ = running
    echoline.controller.snap("bottom")
    wait_until(lambda: False, timeout=0.2)

    echoline.controller.dragStarted()
    y = echoline.window.y()
    echoline.settings_store.setValue("line_count", 3)
    wait_until(lambda: False, timeout=0.3)

    assert echoline.window.y() == y


def test_position_moved_just_before_quit_is_saved(running):
    echoline, _ = running
    echoline.window.setPosition(123, 145)

    echoline.shutdown()

    assert echoline.settings_store.settings.position == [123, 145]


def test_first_run_overlay_is_anchored_to_the_bottom(running):
    echoline, _ = running                     # fresh settings: no saved position
    height, bottom = echoline.window.height(), echoline.window.y() + echoline.window.height()

    echoline.settings_store.setValue("line_count", 3)
    assert wait_until(lambda: echoline.window.height() > height, timeout=1)
    wait_until(lambda: False, timeout=0.2)

    assert echoline.window.y() + echoline.window.height() == bottom

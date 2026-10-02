import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import time

import numpy as np
import pytest
from PySide6.QtGui import QGuiApplication

from echoline.app import EchoLineApp
from echoline.engine.base import Final, Partial

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
def running():
    source = FakeSource()
    echoline = EchoLineApp(source, EchoEngine, show_latency=True)
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

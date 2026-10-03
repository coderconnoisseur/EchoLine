import time

import pytest
from PySide6.QtGui import QAction, QGuiApplication
from PySide6.QtWidgets import QMenu

from echoline.app import EchoLineApp
from echoline.engine.base import Partial
from echoline.settings.model import Settings
from echoline.settings.store import SettingsStore

app = QGuiApplication.instance()


class FakeSource:
    name = "System audio"

    def start(self, on_audio, on_status):
        on_status("listening")

    def stop(self):
        pass


class EchoEngine:
    def feed(self, samples):
        return [Partial(0, "hi")]

    def flush(self):
        return []


def wait_until(condition, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    return False


@pytest.fixture
def echoline(tmp_path):
    instance = EchoLineApp(lambda kind: FakeSource(), EchoEngine, SettingsStore(Settings(), tmp_path / "s.json"))
    instance.start()
    wait_until(lambda: instance.worker is not None)
    yield instance
    instance.shutdown()


def action(instance, name):
    return instance.tray.menu.findChild(QAction, name)


def test_hide_and_show_from_the_tray(echoline):
    action(echoline, "showHide").trigger()
    assert not echoline.window.isVisible()
    assert action(echoline, "showHide").text() == "Show captions"

    action(echoline, "showHide").trigger()
    assert echoline.window.isVisible()


def test_pause_item_reflects_and_toggles_pause(echoline):
    action(echoline, "pause").trigger()

    assert echoline.paused and action(echoline, "pause").isChecked()


def test_source_submenu_switches_source(echoline):
    submenu = echoline.tray.menu.findChild(QMenu, "source")
    mic = [a for a in submenu.actions() if a.text() == "Microphone"][0]

    mic.trigger()

    assert echoline.settings_store.settings.audio_source == "microphone"
    assert mic.isChecked()

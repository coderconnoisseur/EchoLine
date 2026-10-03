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


def test_click_through_can_always_be_turned_off_from_the_tray(echoline):
    echoline.set_click_through(True)
    item = action(echoline, "clickThrough")
    assert item.isChecked()

    item.trigger()

    assert not echoline.settings_store.settings.click_through


def test_pause_before_the_model_loads_does_not_leave_the_tray_wrong(tmp_path):
    def never_ready():
        import threading
        threading.Event().wait(5)      # model still loading

    instance = EchoLineApp(lambda kind: FakeSource(), never_ready, SettingsStore(Settings(), tmp_path / "s.json"))
    instance.start()
    try:
        action(instance, "pause").trigger()

        assert not instance.paused
        assert not action(instance, "pause").isChecked()
    finally:
        instance.shutdown()


def test_first_hide_from_the_overlay_says_the_app_keeps_running(echoline):
    told = []
    echoline.tray.notify = lambda title, text: told.append(title)

    echoline.controller.hide()
    echoline.set_visible(True)
    echoline.controller.hide()

    assert not echoline.window.isVisible()
    assert told == ["EchoLine is still running"]               # once, ever
    assert echoline.settings_store.settings.told_about_tray is True


def test_tray_click_turns_click_through_off_instead_of_hiding(echoline):
    from PySide6.QtWidgets import QSystemTrayIcon

    echoline.set_click_through(True)
    assert "click the tray icon" in echoline.status.property("notice")
    echoline.tray._activated(QSystemTrayIcon.Trigger)

    assert not echoline.settings_store.settings.click_through
    assert echoline.window.isVisible()

    echoline.tray._activated(QSystemTrayIcon.Trigger)          # back to show/hide
    assert not echoline.window.isVisible()


def test_tray_click_shows_hidden_captions_even_in_click_through(echoline):
    from PySide6.QtWidgets import QSystemTrayIcon

    echoline.set_click_through(True)
    echoline.set_visible(False)
    echoline.tray._activated(QSystemTrayIcon.Trigger)

    assert echoline.window.isVisible()

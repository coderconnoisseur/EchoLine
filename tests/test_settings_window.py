import time

import pytest
from PySide6.QtCore import QObject
from PySide6.QtGui import QGuiApplication

from echoline.app import EchoLineApp
from echoline.engine.base import Partial
from echoline.settings.model import Settings
from echoline.settings.store import SettingsStore

app = QGuiApplication.instance()


class FakeSource:
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
def settings_window(tmp_path):
    store = SettingsStore(Settings(), tmp_path / "settings.json")
    echoline = EchoLineApp(lambda kind: FakeSource(), EchoEngine, store)
    warnings = []
    echoline.qml.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))
    window = echoline.open_settings()
    yield echoline, window, store, warnings
    echoline.shutdown()


def test_settings_window_opens_without_qml_warnings(settings_window):
    _, window, _, warnings = settings_window
    wait_until(lambda: False, timeout=0.3)

    assert window.objectName() == "settingsWindow"
    assert window.isVisible()
    assert warnings == []


def test_moving_the_size_slider_updates_the_store(settings_window):
    _, window, store, _ = settings_window
    slider = window.findChild(QObject, "sizeSlider")

    slider.setProperty("value", 40)
    slider.moved.emit()

    assert store.settings.font_size == 40


def test_choosing_a_theme_applies_it(settings_window):
    _, window, store, _ = settings_window
    box = window.findChild(QObject, "themeBox")

    box.activated.emit(box.property("model").index("High contrast"))

    assert store.settings.theme == "High contrast"


def test_opening_twice_reuses_the_window(settings_window):
    echoline, window, _, _ = settings_window

    assert echoline.open_settings() is window


def test_choice_boxes_show_the_current_values(settings_window):
    # Seen blank in the first render: indexOfValue() ran before the model existed.
    _, window, _, _ = settings_window

    assert window.findChild(QObject, "weightBox").property("currentText") == "Medium"
    assert window.findChild(QObject, "effectBox").property("currentText") == "Outline"
    assert window.findChild(QObject, "modeBox").property("currentText") == "Rolling lines"


def test_always_on_top_is_not_offered_yet(settings_window):
    _, window, _, _ = settings_window

    labels = [o.property("text") for o in window.findChildren(QObject) if o.property("text")]

    assert "Always on top" not in labels

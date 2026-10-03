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


def find(window, name):
    return window.findChild(QObject, name)


def test_behavior_controls_update_settings(settings_window):
    echoline, window, store, warnings = settings_window

    find(window, "autoHideSwitch").setProperty("checked", True)
    find(window, "autoHideSwitch").toggled.emit()
    find(window, "autostartSwitch").setProperty("checked", False)
    find(window, "autostartSwitch").toggled.emit()

    assert store.settings.auto_hide is True
    assert warnings == []


def test_click_through_switch_uses_the_app_action(settings_window):
    echoline, window, store, _ = settings_window

    find(window, "clickThroughSwitch").setProperty("checked", True)
    find(window, "clickThroughSwitch").toggled.emit()

    assert store.settings.click_through is True
    assert echoline.status.property("notice") != ""


def test_source_box_switches_source(settings_window):
    echoline, window, store, _ = settings_window
    box = find(window, "sourceBox")

    box.activated.emit(1)            # Microphone

    assert store.settings.audio_source == "microphone"


def test_always_on_top_is_offered_again(settings_window):
    _, window, store, _ = settings_window
    switch = find(window, "onTopSwitch")

    switch.setProperty("checked", False)
    switch.toggled.emit()

    assert store.settings.always_on_top is False


def test_hotkey_buttons_show_current_keys(settings_window):
    _, window, _, _ = settings_window

    assert find(window, "hotkeyPause").property("text") == "Ctrl+Alt+P"
    assert find(window, "hotkeyShowHide").property("text") == "Ctrl+Alt+C"


def test_pressing_keys_records_a_new_hotkey(settings_window):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    _, window, store, _ = settings_window
    button = find(window, "hotkeyPause")
    button.clicked.emit()
    wait_until(lambda: False, timeout=0.2)

    QTest.keyClick(window, Qt.Key_K, Qt.ControlModifier | Qt.AltModifier)

    assert store.settings.hotkey_pause == "Ctrl+Alt+K"
    assert button.property("text") == "Ctrl+Alt+K"

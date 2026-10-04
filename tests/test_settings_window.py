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
    store = SettingsStore(Settings(model="tiny", onboarded=True), tmp_path / "settings.json")
    echoline = EchoLineApp(lambda kind: FakeSource(), EchoEngine, store,
                           model_ops={"download": lambda name, cb: None, "check_hardware": lambda: "tiny",
                                      "is_downloaded": lambda name: True})
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

    assert find(window, "hotkeyPause").property("text") == "Ctrl+Alt+Shift+P"
    assert find(window, "hotkeyShowHide").property("text") == "Ctrl+Alt+Shift+C"


def test_pressing_keys_records_a_new_hotkey(settings_window):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    _, window, store, _ = settings_window
    window.setProperty("page", "shortcuts")
    wait_until(lambda: False, timeout=0.2)
    button = find(window, "hotkeyPause")
    button.clicked.emit()
    wait_until(lambda: False, timeout=0.2)

    QTest.keyClick(window, Qt.Key_K, Qt.ControlModifier | Qt.AltModifier)

    assert store.settings.hotkey_pause == "Ctrl+Alt+K"
    assert button.property("text") == "Ctrl+Alt+K"


def test_model_box_switches_model_and_reloads(settings_window):
    echoline, window, store, warnings = settings_window
    box = find(window, "modelBox")
    reloads = []
    echoline.reload_engine = lambda: reloads.append(True)

    assert box.property("currentText") == "Tiny — faster"
    box.activated.emit(1)                         # Small

    assert store.settings.model == "small" and reloads == [True]
    assert find(window, "modelProgress").property("visible") is False
    assert warnings == []


def test_model_box_shows_the_old_model_after_a_failed_download(settings_window):
    echoline, window, store, _ = settings_window
    box = find(window, "modelBox")

    def offline(name, on_progress):
        raise OSError("offline")

    echoline.setup._is_downloaded = lambda name: False
    echoline.setup._download = offline
    box.setProperty("currentIndex", 1)            # what a click does before onActivated
    box.activated.emit(1)

    assert wait_until(lambda: echoline.setup.property("phase") == "idle")
    assert store.settings.model == "tiny"
    assert box.property("currentText") == "Tiny — faster"


PAGES = ["appearance", "position", "behavior", "speech", "shortcuts", "about"]


def test_sidebar_switches_pages(settings_window):
    _, window, _, warnings = settings_window
    for name in PAGES:
        window.setProperty("page", name)
        wait_until(lambda: False, timeout=0.05)
        assert find(window, f"page {name}").property("visible"), name
        assert all(not find(window, f"page {o}").property("visible") for o in PAGES if o != name)
    assert warnings == []


def test_arrow_keys_move_through_pages(settings_window):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    _, window, _, _ = settings_window
    find(window, "sidebar").forceActiveFocus()
    QTest.keyClick(window, Qt.Key_Down)
    QTest.keyClick(window, Qt.Key_Down)

    assert window.property("page") == "behavior"


def test_sample_runs_only_while_visible(settings_window):
    echoline, window, _, _ = settings_window
    assert echoline.sample.running
    window.close()
    assert wait_until(lambda: not echoline.sample.running, timeout=1)


def visual(item, name):
    for child in item.childItems():
        if child.objectName() == name:
            return child
        found = visual(child, name)
        if found is not None:
            return found
    return None


def focus_in_sidebar(window):
    """The sidebar is a focus scope: focus lands on its current entry."""
    item = window.activeFocusItem()
    while item is not None:
        if item.objectName() == "sidebar":
            return True
        item = item.parentItem()
    return False


def test_light_theme_renders_without_warnings(settings_window):
    # setColorScheme is a no-op offscreen, so flip the window's theme directly.
    _, window, _, warnings = settings_window
    theme = find(window, "theme")
    dark_card = theme.property("card")
    theme.setProperty("dark", False)
    for name in PAGES:
        window.setProperty("page", name)
        wait_until(lambda: False, timeout=0.05)
    assert theme.property("card") != dark_card
    assert warnings == []


def test_clicking_the_sidebar_takes_keyboard_focus(settings_window):
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest

    # Review find: after a mouse click, Space still toggled a switch on the page you left.
    _, window, store, _ = settings_window
    window.setProperty("page", "position")
    wait_until(lambda: False, timeout=0.1)
    find(window, "onTopSwitch").forceActiveFocus()
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, QPoint(60, 16 + 5 * 38 + 18))    # "About"
    wait_until(lambda: False, timeout=0.1)
    QTest.keyClick(window, Qt.Key_Space)

    assert window.property("page") == "about"
    assert store.settings.always_on_top is True
    assert focus_in_sidebar(window)


def test_shift_tab_leads_back_to_the_sidebar(settings_window):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    _, window, _, _ = settings_window
    window.setProperty("page", "behavior")
    wait_until(lambda: False, timeout=0.1)
    find(window, "autoHideSwitch").forceActiveFocus()
    for _ in range(12):
        QTest.keyClick(window, Qt.Key_Backtab)
        if focus_in_sidebar(window):
            break
    assert focus_in_sidebar(window)


def test_theme_cards_work_from_the_keyboard(settings_window):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    _, window, store, _ = settings_window
    card = visual(window.contentItem(), "theme High contrast")
    assert card.property("activeFocusOnTab")
    card.forceActiveFocus()
    QTest.keyClick(window, Qt.Key_Space)
    assert store.settings.theme == "High contrast"


def test_sample_pauses_while_minimised(settings_window):
    echoline, window, _, _ = settings_window
    window.showMinimized()
    assert wait_until(lambda: not echoline.sample.running, timeout=1)
    window.showNormal()
    assert wait_until(lambda: echoline.sample.running, timeout=1)

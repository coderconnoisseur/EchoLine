import time

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


def visual_child(item, name):
    """Repeater delegates are visual children only, so findChild cannot see them."""
    for child in item.childItems():
        if child.objectName() == name:
            return child
        found = visual_child(child, name)
        if found is not None:
            return found
    return None


def test_onboarding_walks_through_all_steps_without_warnings(tmp_path):
    store = SettingsStore(Settings(), tmp_path / "settings.json")
    echoline = EchoLineApp(lambda kind: FakeSource(), EchoEngine, store,
                           model_ops={"download": lambda name, cb: cb(1.0), "check_hardware": lambda: "tiny",
                                      "is_downloaded": lambda name: True})
    warnings = []
    echoline.qml.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))
    window = echoline.run_setup()
    find = lambda name: window.findChild(QObject, name)  # noqa: E731

    assert window.objectName() == "onboardingWindow"
    assert wait_until(lambda: find("nextButton").property("enabled"))
    find("nextButton").clicked.emit()
    assert echoline.visible and find("echoLabel") is not None
    find("soundNextButton").clicked.emit()
    visual_child(window.contentItem(), "theme High contrast").clicked.emit()
    assert store.settings.theme == "High contrast"
    find("finishButton").clicked.emit()
    assert store.settings.onboarded and not window.isVisible()
    assert warnings == []
    echoline.shutdown()


def make_app(tmp_path, engine=EchoEngine, download=lambda name, cb: cb(1.0)):
    store = SettingsStore(Settings(), tmp_path / "settings.json")
    return EchoLineApp(lambda kind: FakeSource(), engine, store,
                       model_ops={"download": download, "check_hardware": lambda: "tiny",
                                  "is_downloaded": lambda name: True})


def test_tray_and_hotkey_raise_setup_instead_of_showing_an_empty_overlay(tmp_path):
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import QSystemTrayIcon

    echoline = make_app(tmp_path)
    window = echoline.run_setup()
    raised = []
    echoline._present = raised.append
    hotkeys = {}
    echoline.hotkeys.register = lambda name, text, callback: hotkeys.update({name: callback})
    echoline._register_hotkeys()

    echoline.tray.menu.findChild(QAction, "showHide").trigger()
    echoline.tray._activated(QSystemTrayIcon.Trigger)
    hotkeys["show_hide"]()

    assert not echoline.window.isVisible()
    assert raised == [window, window, window]

    assert wait_until(lambda: echoline.setup.property("phase") == "ready")
    echoline.setup.finish()                         # afterwards the usual toggle is back
    echoline.tray.menu.findChild(QAction, "showHide").trigger()
    assert not echoline.window.isVisible()
    echoline.shutdown()


def test_tray_hides_and_shows_captions_from_the_sound_test_onward(tmp_path):
    from PySide6.QtGui import QAction

    echoline = make_app(tmp_path)
    echoline.run_setup()
    assert wait_until(lambda: echoline.setup.property("phase") == "ready")
    echoline.setup.nextStep()                       # the sound test shows the real overlay
    item = echoline.tray.menu.findChild(QAction, "showHide")

    item.trigger()
    assert not echoline.window.isVisible()
    item.trigger()
    assert echoline.window.isVisible()
    echoline.shutdown()


def test_a_minimized_window_is_restored_when_presented():
    from PySide6.QtGui import QWindow

    calls = []

    class Minimized:
        def visibility(self):
            return QWindow.Minimized

        def __getattr__(self, name):
            return lambda: calls.append(name)

    EchoLineApp._present(Minimized())

    assert "showNormal" in calls and "show" not in calls


def test_model_box_waits_for_setup_to_finish(tmp_path):
    import threading

    release = threading.Event()

    def slow_download(name, on_progress):
        release.wait(5)

    echoline = make_app(tmp_path, download=slow_download)
    echoline.run_setup()
    box = visual_child(echoline.open_settings().contentItem(), "modelBox")

    assert box.property("displayText") != ""        # no model chosen yet, but not blank
    release.set()
    assert wait_until(lambda: echoline.setup.property("phase") == "ready")
    assert not box.property("enabled")              # choosing here would be ignored

    echoline.setup.finish()
    assert box.property("enabled")
    echoline.settings_store.setValue("model", "medium")     # developer-only model, not in the list
    assert box.property("displayText") == "medium"
    echoline.shutdown()


def test_sound_test_says_when_the_model_could_not_load(tmp_path):
    def crashing_engine():
        raise OSError("exception: access violation reading 0x0000000000000018")

    echoline = make_app(tmp_path, engine=crashing_engine)
    window = echoline.run_setup()
    assert wait_until(lambda: echoline.status.property("state") == "model-error")

    echoline.setup.nextStep()
    text = window.findChild(QObject, "echoLabel").property("text")

    assert "couldn't load" in text and "%LOCALAPPDATA%\\EchoLine\\echoline.log" in text
    echoline.shutdown()

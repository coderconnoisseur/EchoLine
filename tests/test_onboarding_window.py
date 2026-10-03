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

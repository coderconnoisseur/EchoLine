import time
from pathlib import Path

import pytest
from PySide6.QtGui import QGuiApplication

from echoline.app import EchoLineApp
from echoline.engine.base import Partial
from echoline.settings.model import Settings
from echoline.settings.store import SettingsStore
from echoline.ui.overlay import QML_DIR

app = QGuiApplication.instance()


def test_no_qml_depends_on_windows_icon_fonts():
    # A tester's Windows 11 PC drew every icon as an empty box: icon fonts are
    # not guaranteed to exist, so EchoLine ships its own vector icons.
    for qml in Path(QML_DIR).rglob("*.qml"):
        text = qml.read_text(encoding="utf-8")
        assert "MDL2" not in text and "Fluent Icons" not in text, qml.name


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


def icons(item):
    found = []
    for child in item.childItems():
        if child.objectName() == "icon":
            found.append(child)
        found.extend(icons(child))
    return found


@pytest.fixture
def echoline(tmp_path):
    instance = EchoLineApp(lambda kind: FakeSource(), EchoEngine,
                           SettingsStore(Settings(model="tiny", onboarded=True), tmp_path / "s.json"))
    yield instance
    instance.shutdown()


def test_every_icon_in_the_overlay_and_settings_exists(echoline):
    settings = echoline.open_settings()
    deadline = time.monotonic() + 0.3
    while time.monotonic() < deadline:
        app.processEvents()
    used = icons(echoline.window.contentItem()) + icons(settings.contentItem())
    assert len(used) >= 10                            # 4 hover-bar + 6 sidebar
    for icon in used:
        assert icon.property("known"), icon.property("name")
        assert icon.width() > 0

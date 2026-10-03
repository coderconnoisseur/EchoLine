import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import time

import pytest
from PySide6.QtCore import QObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from echoline.captions.model import CaptionModel
from echoline.engine.base import Final, Partial
from echoline.ui.overlay import OverlayStatus, load_overlay

app = QGuiApplication.instance() or QGuiApplication([])


@pytest.fixture
def overlay():
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))
    captions, status = CaptionModel(), OverlayStatus()
    window = load_overlay(engine, captions, status, max_lines=2)
    yield window, captions, status, warnings
    window.close()
    engine.deleteLater()


def settle(seconds=0.4):
    """Process events long enough for the 180 ms scroll animation to finish."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)


def test_overlay_loads_without_qml_warnings(overlay):
    window, _, _, warnings = overlay
    settle()

    assert window.objectName() == "overlay"
    assert warnings == []


def test_captions_render_rows_from_the_model(overlay):
    window, captions, _, _ = overlay

    captions.apply([Final(0, "hello there."), Partial(1, "general")])
    settle()

    view = window.findChild(QObject, "captionList")
    assert view.property("count") == 2


def test_long_utterance_stays_within_line_budget(overlay):
    window, captions, _, _ = overlay
    view = window.findChild(QObject, "captionList")
    height_before = view.property("height")

    captions.apply([Partial(0, " ".join(["monologue"] * 400))])
    settle()

    assert view.property("height") == height_before
    assert view.property("atYEnd")


def test_status_pill_shows_only_when_not_listening(overlay):
    window, _, status, _ = overlay
    pill = window.findChild(QObject, "statusPill")

    status.set_state("listening")
    settle()
    assert not pill.property("visible")

    status.set_state("no-device")
    settle()
    assert pill.property("visible")


def test_overlay_is_returned_as_a_quick_window(overlay):
    # The app needs QQuickWindow API (frameSwapped) to measure sound-to-screen latency.
    from PySide6.QtQuick import QQuickWindow

    window, _, _, _ = overlay

    assert isinstance(window, QQuickWindow)

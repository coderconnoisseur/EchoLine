import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QTimer

import app as app_module


class FakeRecognizer:
    recognizer = object()

    def __init__(self):
        self.received = []

    def process_audio_data(self, data):
        self.received.append(data)
        return "hello", False


class FakeCapture:
    def __init__(self, callback=None):
        self.callback = callback
        self.starts = 0
        self.stops = 0

    def start(self):
        self.starts += 1
        return True

    def stop(self):
        self.stops += 1
        return True


class SharedQApplication:
    """Reuses the test session's QApplication; Qt allows only one per process."""

    def __new__(cls, argv):
        from PySide6.QtWidgets import QApplication
        return QApplication.instance() or QApplication(argv)

    @staticmethod
    def quit():
        from PySide6.QtWidgets import QApplication
        QApplication.quit()


@pytest.fixture
def echoline(monkeypatch):
    monkeypatch.setattr(app_module, 'SpeechRecognizer', FakeRecognizer)
    monkeypatch.setattr(app_module, 'AudioCapture', FakeCapture)
    monkeypatch.setattr(app_module, 'QApplication', SharedQApplication)
    return app_module.EchoLineApp()


def test_closing_the_overlay_stops_capture_once(echoline):
    QTimer.singleShot(0, echoline.overlay.close_app)

    exit_code = echoline.run()

    assert exit_code == 0
    assert echoline.audio_capture.starts == 1
    assert echoline.audio_capture.stops == 1


def test_recognized_text_reaches_the_overlay(echoline):
    echoline.process_audio(b"\x00\x00")

    assert echoline.overlay.caption_label.text() == "hello"

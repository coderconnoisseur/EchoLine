import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from ui.overlay_ui import YouTubeCaptionOverlay
from utils.signals import OverlaySignals


@pytest.fixture
def overlay():
    app = QApplication.instance() or QApplication([])
    widget = YouTubeCaptionOverlay(OverlaySignals())
    yield widget
    widget.deleteLater()
    app.processEvents()


def test_caption_shows_partial_after_final_text(overlay):
    overlay._update_caption_safe("hello", is_partial=False)
    overlay._update_caption_safe("world", is_partial=True)

    assert overlay.caption_label.text() == "hello world"


def test_caption_stays_bounded_over_a_long_session(overlay):
    for i in range(500):
        overlay._update_caption_safe(f"sentence number {i}", is_partial=False)

    shown = overlay.caption_label.text().split()
    assert len(shown) <= overlay.captions.max_words
    assert shown[-1] == "499"

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import time

import pytest
from PySide6.QtCore import QObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from echoline.captions.model import CaptionModel
from echoline.engine.base import Final, Partial
from echoline.settings.model import Settings
from echoline.settings.store import SettingsStore
from echoline.ui.overlay import OverlayStatus, load_overlay

app = QGuiApplication.instance() or QGuiApplication([])


@pytest.fixture
def overlay(tmp_path):
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))
    captions, status = CaptionModel(), OverlayStatus()
    store = SettingsStore(Settings(), tmp_path / "settings.json")
    window = load_overlay(engine, captions, status, store)
    window.store = store
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

    assert len(caption_lines(window)) == 2


def test_long_utterance_stays_within_line_budget(overlay):
    window, captions, _, _ = overlay
    area = window.findChild(QObject, "captionArea")
    height_before = area.property("height")

    captions.apply([Partial(0, " ".join(["monologue"] * 400))])
    settle()

    assert area.property("height") == height_before
    top, bottom, height = newest_line_bounds(window)
    assert abs(bottom - height) <= 2              # the end of the monologue is what shows


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


def test_overlay_follows_style_settings(overlay):
    window, captions, _, warnings = overlay
    captions.apply([Final(0, "hello")])
    settle()
    view = window.findChild(QObject, "captionArea")
    one_line_view = view.property("height")

    window.store.setValue("font_size", 52)
    window.store.setValue("corner_radius", 0)
    settle()

    assert view.property("height") > one_line_view * 1.5
    assert window.findChild(QObject, "panel").property("radius") == 0
    assert warnings == []


def test_line_count_sets_view_height(overlay):
    window, _, _, _ = overlay
    view = window.findChild(QObject, "captionArea")
    two_lines = view.property("height")

    window.store.setValue("line_count", 1)
    settle()

    assert abs(view.property("height") - two_lines / 2) < 1


def test_width_follows_width_percent(overlay):
    window, _, _, _ = overlay

    window.store.setValue("width_percent", 50)
    settle()

    assert abs(window.width() - window.screen().geometry().width() * 0.5) <= 1


def test_overlay_height_is_capped_on_small_screens(overlay):
    window, _, _, _ = overlay

    window.store.setValue("font_size", 64)
    window.store.setValue("line_count", 3)
    settle()

    assert window.height() <= window.screen().geometry().height() * 0.4 + 1


def visible_text(item):
    return item.findChild(QObject, "subtitleText").property("text")


def test_subtitle_mode_shows_only_the_newest_utterance(overlay):
    window, captions, _, warnings = overlay
    window.store.setValue("caption_mode", "subtitle")
    captions.apply([Final(0, "first sentence."), Partial(1, "second")])
    settle()

    subtitle = window.findChild(QObject, "subtitleView")
    assert subtitle.property("visible")
    assert not window.findChild(QObject, "captionArea").property("visible")
    assert visible_text(subtitle) == "second"
    assert warnings == []


def test_switching_mode_keeps_current_text(overlay):
    window, captions, _, _ = overlay
    captions.apply([Partial(0, "mid sentence")])
    settle()

    window.store.setValue("caption_mode", "subtitle")
    settle()
    assert visible_text(window.findChild(QObject, "subtitleView")) == "mid sentence"

    window.store.setValue("caption_mode", "rolling")
    settle()
    assert len(caption_lines(window)) == 1


def as_item(obj):
    import shiboken6
    from PySide6.QtQuick import QQuickItem
    return shiboken6.wrapInstance(shiboken6.getCppPointer(obj)[0], QQuickItem)


def caption_lines(window):
    from PySide6.QtCore import Q_ARG, Q_RETURN_ARG, QMetaObject, Qt
    from PySide6.QtQuick import QQuickItem

    repeater = window.findChild(QObject, "captionLines")
    return [QMetaObject.invokeMethod(repeater, "itemAt", Qt.DirectConnection,
                                     Q_RETURN_ARG(QQuickItem), Q_ARG(int, i))
            for i in range(repeater.property("count"))]


def newest_line_bounds(window):
    """(top, bottom, area height) of the newest caption line inside the visible caption area."""
    from PySide6.QtCore import QPointF

    area = as_item(window.findChild(QObject, "captionArea"))
    newest = caption_lines(window)[-1]
    top = newest.mapToItem(area, QPointF(0, 0)).y()
    return top, top + newest.height(), area.height()


def test_newest_line_stays_fully_visible_after_restyling(overlay):
    # Seen in the Netflix theme: after a font change the rolling view stopped
    # mid-scroll, cutting off the newest line.
    window, captions, _, _ = overlay
    captions.apply([Final(0, "It was the best of times, it was the worst of times."),
                    Partial(1, "it was the age of wisdom")])
    settle()

    for theme in ("Netflix", "High contrast", "Classic CC", "Netflix"):
        window.store.applyTheme(theme)
        settle(0.6)
        top, bottom, height = newest_line_bounds(window)
        # The end of the newest text sits on the bottom edge (a long line may extend above).
        assert abs(bottom - height) <= 2, (theme, top, bottom, height)


def test_caption_lines_never_overlap_after_restyling(overlay):
    # Seen after switching themes: the line move animation left lines overlapping.
    window, captions, _, _ = overlay
    captions.apply([Final(0, "It was the best of times, it was the worst of times."),
                    Partial(1, "it was the age of wisdom")])
    settle()

    for theme in ("Netflix", "High contrast", "Minimal"):
        window.store.applyTheme(theme)
        settle(0.6)
        first, second = caption_lines(window)
        assert first.y() + first.height() <= second.y() + 1, (theme, first.y(), first.height(), second.y())


def test_newest_line_is_inside_the_window_when_height_is_capped(overlay):
    # With a big font and 3 lines the window is capped at 40% of the screen;
    # the caption area must shrink with it, not spill past the window edge.
    from PySide6.QtCore import QPointF

    window, captions, status, _ = overlay
    captions.apply([Final(0, "one two three four five six"), Partial(1, "newest words here")])
    status.set_state("lagging")                       # the pill takes space too
    window.store.setValue("font_size", 64)
    window.store.setValue("line_count", 3)
    settle()

    newest = caption_lines(window)[-1]
    bottom = newest.mapToScene(QPointF(0, newest.height())).y()
    content = window.findChild(QObject, "content").property("height")
    assert window.height() <= window.screen().geometry().height() * 0.4 + 1
    assert content + 24 <= window.height() + 1, (content, window.height())   # nothing spills out
    assert bottom <= window.height() + 1, (bottom, window.height())

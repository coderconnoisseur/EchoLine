import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import re
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
    captions, status = CaptionModel(settle_after_ms=60_000), OverlayStatus()   # no idle settling mid-test
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


def plain(markup):
    """Caption text without the dimming markup."""
    return re.sub(r"<[^>]+>", "", markup).replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def visible_text(item):
    return plain(item.findChild(QObject, "subtitleText").property("text"))


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


def test_always_on_top_setting_controls_the_flag(overlay):
    from PySide6.QtCore import Qt

    window, _, _, _ = overlay
    assert window.flags() & Qt.WindowStaysOnTopHint

    window.store.setValue("always_on_top", False)
    settle()

    assert not window.flags() & Qt.WindowStaysOnTopHint

def test_subtitle_cross_fades_from_the_previous_phrase(overlay):
    # The new text used to appear instantly, then blink out and back in.
    window, captions, _, _ = overlay
    window.store.setValue("caption_mode", "subtitle")
    captions.apply([Final(0, "first phrase.")])
    settle()

    captions.apply([Partial(1, "second")])
    app.processEvents()
    outgoing = window.findChild(QObject, "subtitleOutgoing")
    assert outgoing.property("text") == "first phrase."
    assert outgoing.property("opacity") > 0.5           # old phrase still fading out
    assert visible_text(window.findChild(QObject, "subtitleView")) == "second"

    settle()
    assert outgoing.property("opacity") == 0


def test_hover_bar_starts_hidden(tmp_path):
    from PySide6.QtGui import QCursor

    # The offscreen cursor starts at (10, 10), over a window at (0, 0); move it first.
    QCursor.setPos(1300, 600)
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))
    keep = CaptionModel(), OverlayStatus(), SettingsStore(Settings(), tmp_path / "s.json")   # QML does not own these
    window = load_overlay(engine, *keep)
    try:
        settle()
        bar = window.findChild(QObject, "hoverBar")
        assert bar is not None and bar.property("opacity") == 0
        assert warnings == []
    finally:
        window.close()
        engine.deleteLater()


def test_hover_bar_appears_while_hovered(overlay):
    window, _, _, _ = overlay
    bar = window.findChild(QObject, "hoverBar")

    window.findChild(QObject, "overlayHover").setProperty("forceHovered", True)
    settle()

    assert bar.property("opacity") == 1


def test_auto_hide_fades_after_silence_and_returns_with_speech(overlay):
    window, captions, status, _ = overlay
    window.findChild(QObject, "overlayHover").setProperty("enabled", False)   # offscreen cursor sits on the window
    status.set_state("listening")
    window.setProperty("autoHideDelay", 200)
    window.store.setValue("auto_hide", True)
    captions.apply([Partial(0, "hello")])
    settle(0.9)
    panel = window.findChild(QObject, "panel")
    assert panel.property("opacity") == 0

    window.setProperty("autoHideDelay", 5000)     # don't fade again while we look
    captions.apply([Partial(0, "hello again")])
    settle(0.5)
    assert panel.property("opacity") == 1


def test_auto_hide_keeps_status_visible(overlay):
    window, captions, status, _ = overlay
    window.findChild(QObject, "overlayHover").setProperty("enabled", False)
    status.set_state("no-device")
    window.setProperty("autoHideDelay", 200)
    window.store.setValue("auto_hide", True)
    settle(0.9)

    assert window.findChild(QObject, "panel").property("opacity") == 1


def test_auto_hide_off_never_fades(overlay):
    window, captions, status, _ = overlay
    window.findChild(QObject, "overlayHover").setProperty("enabled", False)
    status.set_state("listening")
    window.setProperty("autoHideDelay", 200)
    captions.apply([Partial(0, "hello")])
    settle(0.9)

    assert window.findChild(QObject, "panel").property("opacity") == 1


def test_dim_mode_dims_only_the_words_still_changing(overlay):
    window, captions, _, warnings = overlay
    captions.apply([Partial(0, "It was the")])
    captions.apply([Partial(0, "It was the best <of>")])
    settle()

    text = caption_lines(window)[0].property("text")
    assert text == 'It was the<font color="#8cffffff"> best &lt;of&gt;</font>'
    captions.apply([Final(0, "It was the best of times.")])
    settle()
    assert caption_lines(window)[0].property("text") == "It was the best of times."
    assert warnings == []


def test_hide_mode_shows_only_settled_words(overlay):
    window, captions, _, warnings = overlay
    window.store.setValue("unsettled_words", "hide")
    captions.apply([Partial(0, "It was the")])
    captions.apply([Partial(0, "It was the beast")])
    settle()
    assert caption_lines(window)[0].property("text") == "It was the"

    window.store.setValue("caption_mode", "subtitle")
    settle()
    assert visible_text(window.findChild(QObject, "subtitleView")) == "It was the"
    assert warnings == []


def test_hide_mode_never_shows_a_blank_line_or_blank_subtitle(overlay):
    window, captions, _, _ = overlay
    window.store.setValue("unsettled_words", "hide")
    captions.apply([Final(0, "first phrase.")])
    captions.apply([Partial(1, "second")])            # nothing settled yet
    settle()
    lines = caption_lines(window)
    assert lines[1].property("height") == 0 or not lines[1].property("visible")

    window.store.setValue("caption_mode", "subtitle")
    settle()
    assert visible_text(window.findChild(QObject, "subtitleView")) == "first phrase."
    captions.apply([Partial(1, "second phrase")])
    settle()
    assert visible_text(window.findChild(QObject, "subtitleView")) == "second"


def test_subtitle_follows_a_switch_between_dim_and_hide(overlay):
    window, captions, _, _ = overlay
    window.store.setValue("caption_mode", "subtitle")
    captions.apply([Partial(0, "It was")])
    captions.apply([Partial(0, "It was the")])
    settle()
    window.store.setValue("unsettled_words", "hide")
    settle()
    assert visible_text(window.findChild(QObject, "subtitleView")) == "It was"

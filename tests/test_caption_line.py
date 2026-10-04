import time

import shiboken6
from PySide6.QtCore import QObject, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem

from echoline.captions.words import WordModel
from echoline.settings.model import Settings
from echoline.ui.motion import Motion
from echoline.ui.overlay import QML_DIR

app = QGuiApplication.instance()


def settle(seconds=0.5):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)


def make(width=300, animate=True, **settings):
    from dataclasses import asdict

    engine = QQmlEngine()
    warnings = []
    engine.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))
    motion = Motion(animate, engine)
    words = WordModel(engine)
    engine.rootContext().setContextProperty("motion", motion)
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML_DIR / "CaptionLine.qml")))
    line = component.createWithInitialProperties({"words": words, "s": asdict(Settings(**settings)), "width": width})
    assert line is not None, component.errors()
    engine.created = (component, line)   # the item dies with these wrappers; keep them alive
    line = shiboken6.wrapInstance(shiboken6.getCppPointer(line)[0], QQuickItem)
    return engine, words, line, warnings


def word_items(line):
    items = [i for i in line.childItems() if i.objectName() == "word"]
    return sorted(items, key=lambda i: (round(i.y()), i.x()))


def test_words_fit_the_width_centered_without_overlap():
    engine, words, line, warnings = make(width=300)
    words.update("It was the best of times it was the worst of times".split(), 0)
    settle()
    items = word_items(line)
    assert len(items) == 12 and line.property("rows") >= 2
    rows = {}
    for item in items:
        assert item.x() >= 0 and item.x() + item.width() <= 300 + 1
        rows.setdefault(round(item.y()), []).append(item)
    for row in rows.values():
        left = row[0].x()
        right = 300 - (row[-1].x() + row[-1].width())
        assert abs(left - right) <= 2                         # centered
        for a, b in zip(row, row[1:]):
            assert a.x() + a.width() <= b.x()                 # no overlap
    assert line.height() == line.property("rows") * line.property("lineHeight")
    assert warnings == []


def test_a_correction_keeps_the_same_word_item():
    engine, words, line, _ = make()
    words.update(["It", "was", "the", "best"], 0)
    settle()
    before = word_items(line)[3]
    words.update(["It", "was", "the", "beast"], 0)
    settle()
    after = word_items(line)[3]
    assert shiboken6.getCppPointer(before)[0] == shiboken6.getCppPointer(after)[0]
    assert after.property("text") == "beast"


def test_unsettled_words_are_dim_and_settled_words_full():
    engine, words, line, _ = make()
    words.update(["It", "was", "the"], 2)
    settle()
    assert [round(i.opacity(), 2) for i in word_items(line)] == [1.0, 1.0, 0.55]


def test_empty_line_has_no_height():
    engine, words, line, _ = make()
    settle(0.1)
    assert line.height() == 0 and line.property("rows") == 0


def test_overlong_word_gets_its_own_row():
    engine, words, line, _ = make(width=80, font_size=26)
    words.update(["a", "Supercalifragilistic", "b"], 0)
    settle()
    items = word_items(line)
    assert line.property("rows") == 3 and all(i.x() >= 0 for i in items)


def test_layout_follows_a_font_change():
    engine, words, line, _ = make(width=300)
    words.update("It was the best of times it was".split(), 0)
    settle()
    rows_before = line.property("rows")
    line.setProperty("s", __import__("dataclasses").asdict(Settings(font_size=48)))
    settle(0.6)
    assert line.property("rows") > rows_before
    for item in word_items(line):
        assert item.x() + item.width() <= 300 + 1


def test_motion_off_shows_final_state_at_once():
    engine, words, line, _ = make(animate=False)
    words.update(["hello", "there"], 2)
    app.processEvents()
    app.processEvents()
    items = word_items(line)
    assert all(i.opacity() == 1.0 for i in items)
    assert all(i.findChild(QObject, "body").property("opacity") == 1.0 for i in items)


def test_new_words_stay_hidden_until_placed():
    # Seen in recorded frames: a new word flashed at the left edge for a frame
    # before the layout pass moved it into its row.
    engine, words, line, _ = make()
    words.update(["It", "was"], 0)
    settle()
    words.update(["It", "was", "the", "best"], 0)       # delegates exist, layout not yet run
    fresh = [i for i in line.childItems() if i.objectName() == "word" and not i.property("placed")]
    assert fresh and not any(i.isVisible() for i in fresh)
    settle()
    assert all(i.isVisible() for i in word_items(line))


def test_words_never_overlap_while_the_row_recenters():
    # Seen in recorded frames: appended words appeared at their final spot while
    # the rest of the centered row was still gliding left, overlapping it.
    engine, words, line, _ = make(width=400)
    words.update(["It", "was"], 0)
    settle()
    words.update(["It", "was", "the", "best", "of"], 0)
    deadline = time.monotonic() + 0.5
    while time.monotonic() < deadline:
        app.processEvents()
        items = sorted((i for i in line.childItems() if i.objectName() == "word" and i.isVisible()),
                       key=lambda i: i.property("index"))
        for a, b in zip(items, items[1:]):
            if a.y() == b.y():                            # neighbours on the same row
                assert a.x() + a.width() <= b.x() + 1, (a.property("text"), a.x(), b.property("text"), b.x())
        time.sleep(0.005)

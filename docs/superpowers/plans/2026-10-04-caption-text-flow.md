# Caption Text Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render captions word by word so new words fade in softly, corrections cross-fade in place, words glide on re-wrap and settle from dim to full brightness.

**Architecture:** A Python `WordModel` per caption line turns each new guess into minimal insert/remove/change signals (difflib). A reusable `CaptionLine.qml` lays the words out in centered rows and animates them; the rolling overlay and `SubtitleView` both use it. A `motion` context property zeroes every duration when Windows animations are off. The dim/hide markup path and its setting are removed.

**Tech Stack:** Python 3.11, PySide6 6.11 (QtQuick, QtQuick.Effects MultiEffect), stdlib difflib/ctypes, pytest offscreen.

**Spec:** `docs/superpowers/specs/2026-10-04-caption-text-flow-design.md`

## Global Constraints

- Run with `D:/EchoLine/.venv/Scripts/python -m pytest -q`; the worktree-only failure `test_autostart.py::test_launch_command_runs_the_checkout_without_a_console` is known and unrelated.
- Durations: entry 180 ms (opacity 0→1, 6 px drift up, blur 0.6→0), correction cross-fade 160 ms, glide 220 ms, settle 200 ms; all `Easing.OutCubic`; each multiplied by `motion.scale`.
- Unsettled word opacity 0.55; settled 1.0.
- Blur layer enabled only while a word's entry animation runs.
- No QML warnings in any test.
- Commits: "why" bodies, never mention Claude/AI.

## Review Focus

1. A guess that rewrites most of a line (difflib replace spans) → no duplicated or missing words, same count as the text (Task 1 `test_full_rewrite_matches_new_words`).
2. Font/theme change mid-caption → words re-layout inside the width, no overlap (Task 4 `test_layout_follows_a_font_change`).
3. A word wider than the line → own row, nothing negative x (Task 4 `test_overlong_word_gets_its_own_row`).
4. Rows dropped from CaptionModel → their WordModel is released, QML shows no "of null" warnings (Task 2 `test_dropped_rows_release_their_words`, overlay suite warnings == []).
5. Windows animations off → final state with no motion (Task 4 `test_motion_off_shows_final_state_at_once`).

---

### Task 1: WordModel

**Files:** Create `echoline/captions/words.py`; Test `tests/test_words.py`

**Produces:** `WordModel(QAbstractListModel)` roles `text`, `settled`; `update(words: list[str], settled_count: int)`; `words() -> list[str]`; Qt property `text` (joined, notify `textChanged`).

- [ ] **Step 1: Failing tests**

```python
from PySide6.QtCore import QCoreApplication

from echoline.captions.words import WordModel

app = QCoreApplication.instance() or QCoreApplication([])


def spy(model):
    log = []
    model.rowsInserted.connect(lambda parent, first, last: log.append(("insert", first, last)))
    model.rowsRemoved.connect(lambda parent, first, last: log.append(("remove", first, last)))
    model.dataChanged.connect(lambda top, bottom, roles: log.append(("change", top.row(), bottom.row())))
    return log


def flags(model):
    return [model.data(model.index(i), model.SETTLED) for i in range(model.rowCount())]


def test_appending_words_only_inserts():
    model = WordModel()
    model.update(["It", "was"], 0)
    log = spy(model)
    model.update(["It", "was", "the", "best"], 0)
    assert model.words() == ["It", "was", "the", "best"]
    assert log == [("insert", 2, 3)]


def test_a_correction_changes_the_word_in_place():
    model = WordModel()
    model.update(["It", "was", "the", "best"], 0)
    log = spy(model)
    model.update(["It", "was", "the", "beast", "of"], 0)
    assert model.words() == ["It", "was", "the", "beast", "of"]
    assert ("change", 3, 3) in log and ("insert", 4, 4) in log
    assert not any(kind == "remove" for kind, *_ in log)


def test_a_word_inserted_mid_line_is_an_insert():
    model = WordModel()
    model.update(["the", "best", "times"], 0)
    log = spy(model)
    model.update(["the", "best", "of", "times"], 0)
    assert log == [("insert", 2, 2)]


def test_deleted_words_are_removed():
    model = WordModel()
    model.update(["a", "b", "c", "d"], 0)
    log = spy(model)
    model.update(["a", "d"], 0)
    assert model.words() == ["a", "d"] and log == [("remove", 1, 2)]


def test_full_rewrite_matches_new_words():
    model = WordModel()
    model.update(["I", "scream", "for", "it"], 0)
    model.update(["Ice", "cream", "is", "nice", "today"], 0)
    assert model.words() == ["Ice", "cream", "is", "nice", "today"]
    assert model.rowCount() == 5


def test_settled_flags_follow_the_count_and_only_changed_rows_signal():
    model = WordModel()
    model.update(["It", "was", "the"], 0)
    assert flags(model) == [False, False, False]
    log = spy(model)
    model.update(["It", "was", "the"], 2)
    assert flags(model) == [True, True, False]
    assert log == [("change", 0, 0), ("change", 1, 1)]


def test_text_property_joins_words_and_notifies():
    model = WordModel()
    seen = []
    model.textChanged.connect(lambda: seen.append(model.property("text")))
    model.update(["hello", "there"], 0)
    model.update(["hello", "there"], 2)          # flags only: text unchanged
    assert model.property("text") == "hello there" and seen == ["hello there"]
```

- [ ] **Step 2:** `pytest -q tests/test_words.py` → FAIL (no module).

- [ ] **Step 3: Implement `echoline/captions/words.py`**

```python
import difflib

from PySide6.QtCore import Property, QAbstractListModel, QByteArray, QModelIndex, Qt, Signal


class WordModel(QAbstractListModel):
    """One caption line as words, changed minimally so each word item can animate."""

    TEXT = Qt.UserRole + 1
    SETTLED = Qt.UserRole + 2
    textChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = []          # [text, settled]

    def roleNames(self):
        return {self.TEXT: QByteArray(b"text"), self.SETTLED: QByteArray(b"settled")}

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        text, settled = self._rows[index.row()]
        return {self.TEXT: text, Qt.DisplayRole: text, self.SETTLED: settled}.get(role)

    def words(self):
        return [text for text, _ in self._rows]

    def _get_text(self):
        return " ".join(self.words())

    text = Property(str, _get_text, notify=textChanged)

    def _insert(self, at, words):
        self.beginInsertRows(QModelIndex(), at, at + len(words) - 1)
        self._rows[at:at] = [[word, False] for word in words]
        self.endInsertRows()

    def _remove(self, first, last):
        self.beginRemoveRows(QModelIndex(), first, last)
        del self._rows[first:last + 1]
        self.endRemoveRows()

    def update(self, words, settled_count):
        """Move to `words`; the first `settled_count` count as settled."""
        before = self.words()
        if words != before:
            matcher = difflib.SequenceMatcher(None, before, words, autojunk=False)
            # Back to front, so earlier indices stay valid while later ones change.
            for tag, i1, i2, j1, j2 in reversed(matcher.get_opcodes()):
                if tag == "equal":
                    continue
                common = min(i2 - i1, j2 - j1)
                for k in range(common):
                    self._rows[i1 + k][0] = words[j1 + k]
                if common:
                    self.dataChanged.emit(self.index(i1), self.index(i1 + common - 1), [self.TEXT])
                if j2 - j1 > common:
                    self._insert(i1 + common, words[j1 + common:j2])
                elif i2 - i1 > common:
                    self._remove(i1 + common, i2 - 1)
            self.textChanged.emit()
        for row, entry in enumerate(self._rows):
            settled = row < settled_count
            if entry[1] != settled:
                entry[1] = settled
                self.dataChanged.emit(self.index(row), self.index(row), [self.SETTLED])
```

Note `test_a_correction_changes_the_word_in_place` expects `("change", 3, 3)` from the replace and `("insert", 4, 4)`; SequenceMatcher yields `replace best→beast` + `insert of` (or a single replace 3..4→3..5, which this code turns into change 3 + insert 4). Both satisfy the test.

- [ ] **Step 4:** run → PASS. **Commit** (git add) — "Model a caption line word by word".

---

### Task 2: CaptionModel keeps a WordModel per row

**Files:** Modify `echoline/captions/model.py`; Test `tests/test_caption_model.py`

**Consumes:** `WordModel` (Task 1). **Produces:** role `words` (QObject), property `latestWords` (QObject, notify `latestChanged`).

- [ ] **Step 1: Failing tests** (append)

```python
def words_of(model, row=0):
    names = {v.data().decode(): k for k, v in model.roleNames().items()}
    return model.data(model.index(row), names["words"])


def test_each_row_carries_its_words_with_settled_flags():
    model = CaptionModel(settle_after_ms=60_000)
    model.apply([Partial(0, "It was the")])
    model.apply([Partial(0, "It was the best")])
    words = words_of(model)
    assert words.words() == ["It", "was", "the", "best"]
    assert [words.data(words.index(i), words.SETTLED) for i in range(4)] == [True, True, True, False]
    assert model.property("latestWords") is words

    model.apply([Final(0, "It was the best of times.")])
    assert all(words.data(words.index(i), words.SETTLED) for i in range(words.rowCount()))


def test_dropped_rows_release_their_words():
    model = CaptionModel(max_utterances=1, settle_after_ms=60_000)
    model.apply([Final(0, "first.")])
    first = words_of(model)
    destroyed = []
    first.destroyed.connect(lambda: destroyed.append(True))
    model.apply([Final(1, "second.")])
    QCoreApplication.sendPostedEvents(None, 0)       # run deleteLater
    assert destroyed == [True]


def test_idle_settling_reaches_the_words():
    model = CaptionModel(settle_after_ms=50)
    model.apply([Partial(0, "hello there")])
    words = words_of(model)
    deadline = time.monotonic() + 1
    while not words.data(words.index(1), words.SETTLED) and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    assert words.data(words.index(1), words.SETTLED)
```

- [ ] **Step 2:** run → FAIL (no role `words`).

- [ ] **Step 3: Implement** — in `model.py`:
  - `from .words import WordModel`; `WORDS_ROLE = Qt.UserRole + 5`; roleNames adds `WORDS_ROLE: QByteArray(b"words")`.
  - Rows become `[utterance_id, text, final, settled, words]`; `data` returns `words` for `WORDS_ROLE`; `_latest()` default `(-1, "", False, "", None)`.
  - New helper:
    ```python
    @staticmethod
    def _sync_words(entry):
        entry[4].update(entry[1].split(), len(entry[3].split()))
    ```
    Called after each row's text/settled changes (in `_apply_one` for update and insert, and in `_settle_all`).
  - Insert creates `WordModel(self)`.
  - Dropping a row calls `self._rows.pop(0)[4].deleteLater()` (keep `_highest_dropped` from its id).
  - `latestWords = Property(QObject, lambda self: self._latest()[4], notify=latestChanged)`.
  - `apply`'s `before`/after comparison must use `tuple(self._latest()[:4])` (the WordModel object never changes identity for a row).
- [ ] **Step 4:** run `tests/test_caption_model.py` → PASS. **Commit** — "Give every caption row its own word model".

---

### Task 3: Motion follows Windows

**Files:** Create `echoline/ui/motion.py`; Modify `echoline/ui/overlay.py` (`load_overlay` sets context property `motion`); Test `tests/test_motion.py`

**Produces:** `animations_enabled() -> bool`; `Motion(enabled: bool)` QObject with constant properties `enabled` (bool) and `scale` (float 1.0/0.0); `load_overlay(..., motion=None)` defaults to `Motion(animations_enabled())`.

- [ ] **Step 1: Failing tests**

```python
from echoline.ui import motion


def test_reads_the_windows_animation_setting(monkeypatch):
    class User32:
        def __init__(self, value):
            self.value = value

        def SystemParametersInfoW(self, action, param, out, flags):
            assert action == 0x1042                      # SPI_GETCLIENTAREAANIMATION
            out._obj.value = self.value
            return 1

    monkeypatch.setattr(motion, "_user32", lambda: User32(False))
    assert motion.animations_enabled() is False
    monkeypatch.setattr(motion, "_user32", lambda: User32(True))
    assert motion.animations_enabled() is True


def test_unreadable_setting_means_animate(monkeypatch):
    def broken():
        raise OSError("no user32")

    monkeypatch.setattr(motion, "_user32", broken)
    assert motion.animations_enabled() is True


def test_scale_is_zero_when_disabled():
    assert motion.Motion(False).property("scale") == 0.0
    assert motion.Motion(True).property("scale") == 1.0
```

- [ ] **Step 2:** run → FAIL.

- [ ] **Step 3: Implement**

```python
import ctypes

from PySide6.QtCore import Property, QObject

SPI_GETCLIENTAREAANIMATION = 0x1042


def _user32():
    return ctypes.windll.user32


def animations_enabled() -> bool:
    """Windows' "Show animations in Windows"; animate if it cannot be read."""
    try:
        value = ctypes.c_bool(True)
        if not _user32().SystemParametersInfoW(SPI_GETCLIENTAREAANIMATION, 0, ctypes.byref(value), 0):
            return True
        return bool(value.value)
    except (OSError, AttributeError):
        return True


class Motion(QObject):
    """Exposed to QML: multiply every caption animation duration by `scale`."""

    def __init__(self, enabled, parent=None):
        super().__init__(parent)
        self._enabled = enabled

    enabled = Property(bool, lambda self: self._enabled, constant=True)
    scale = Property(float, lambda self: 1.0 if self._enabled else 0.0, constant=True)
```

`load_overlay(engine, captions, status, settings_store, controller=None, motion=None)`: before loading, `motion = motion or Motion(animations_enabled(), engine)` and `context.setContextProperty("motion", motion)`; keep a reference on the engine (`engine._motion = motion`) so it is not collected.

- [ ] **Step 4:** run → PASS. **Commit** — "Respect the Windows animation setting".

---

### Task 4: CaptionLine.qml

**Files:** Create `echoline/ui/qml/CaptionLine.qml`; Test `tests/test_caption_line.py`

**Consumes:** `WordModel`, `Motion`. **Produces:** QML type `CaptionLine` with required properties `words` (WordModel) and `s` (settings map); readonly `text` (words.text); `rows` (int); `implicitHeight = rows * lineHeight`; per-word delegate objectName `"word"`, function `place(x, y)`.

- [ ] **Step 1: Failing tests** (`tests/test_caption_line.py`)

```python
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
```

- [ ] **Step 2:** run → FAIL (no file).

- [ ] **Step 3: Implement `echoline/ui/qml/CaptionLine.qml`**

```qml
import QtQuick
import QtQuick.Effects

// One caption line laid out word by word, so words can fade in softly,
// cross-fade when corrected and glide when the line re-wraps.
Item {
    id: line
    required property var words
    required property var s
    readonly property string text: words ? words.text : ""
    readonly property real lineHeight: metrics.height * 1.15
    readonly property real ms: motion.scale
    property int rows: 0
    implicitHeight: rows * lineHeight
    height: implicitHeight

    FontMetrics {
        id: metrics
        font.family: line.s.font_family
        font.pixelSize: line.s.font_size
        font.weight: line.s.font_weight
    }

    onWidthChanged: Qt.callLater(relayout)
    onLineHeightChanged: Qt.callLater(relayout)

    // Greedy rows, each centered; Flow cannot center rows.
    function relayout() {
        const space = metrics.advanceWidth(" ")
        const rowsOut = []
        let current = [], used = 0
        for (let i = 0; i < repeater.count; i++) {
            const item = repeater.itemAt(i)
            if (!item)
                continue
            const w = item.implicitWidth
            const needed = current.length ? used + space + w : w
            if (current.length && needed > width) {
                rowsOut.push({ items: current, width: used })
                current = []
                used = 0
            }
            used = current.length ? used + space + w : w
            current.push(item)
        }
        if (current.length)
            rowsOut.push({ items: current, width: used })
        rows = rowsOut.length
        for (let r = 0; r < rowsOut.length; r++) {
            let x = Math.max(0, (width - rowsOut[r].width) / 2)
            for (const item of rowsOut[r].items) {
                item.place(x, r * lineHeight)
                x += item.implicitWidth + space
            }
        }
    }

    component WordText: Text {
        color: line.s.text_color
        font.family: line.s.font_family
        font.pixelSize: line.s.font_size
        font.weight: line.s.font_weight
        style: ({ "outline": Text.Outline, "shadow": Text.Raised, "none": Text.Normal })[line.s.outline]
        styleColor: line.s.outline_color
    }

    Repeater {
        id: repeater
        model: line.words
        onItemAdded: Qt.callLater(line.relayout)
        onItemRemoved: Qt.callLater(line.relayout)

        delegate: Item {
            id: word
            objectName: "word"
            required property string text
            required property bool settled
            property bool placed: false
            implicitWidth: label.implicitWidth
            width: implicitWidth
            height: line.lineHeight
            opacity: settled ? 1.0 : 0.55
            onImplicitWidthChanged: Qt.callLater(line.relayout)

            Behavior on opacity { NumberAnimation { duration: 200 * line.ms; easing.type: Easing.OutCubic } }
            Behavior on x { enabled: word.placed; NumberAnimation { duration: 220 * line.ms; easing.type: Easing.OutCubic } }
            Behavior on y { enabled: word.placed; NumberAnimation { duration: 220 * line.ms; easing.type: Easing.OutCubic } }

            function place(px, py) {
                x = px
                y = py
                if (!placed) {
                    placed = true
                    if (line.ms > 0)
                        entry.restart()
                }
            }

            onTextChanged: {
                if (ghost.text === "" && label.text === "") {
                    label.text = text
                    return
                }
                ghost.text = label.text
                label.text = text
                if (line.ms > 0)
                    correction.restart()
            }
            Component.onCompleted: label.text = text

            Item {
                id: body
                objectName: "body"
                width: word.width
                height: word.height
                layer.enabled: entry.running
                layer.effect: MultiEffect { blurEnabled: true; blurMax: 16; blur: body.blur }
                property real blur: 0
                property real drift: 0
                transform: Translate { y: body.drift }

                WordText { id: ghost; opacity: 0 }
                WordText { id: label }
            }

            ParallelAnimation {
                id: entry
                NumberAnimation { target: body; property: "opacity"; from: 0; to: 1; duration: 180 * line.ms; easing.type: Easing.OutCubic }
                NumberAnimation { target: body; property: "drift"; from: 6; to: 0; duration: 180 * line.ms; easing.type: Easing.OutCubic }
                NumberAnimation { target: body; property: "blur"; from: 0.6; to: 0; duration: 180 * line.ms; easing.type: Easing.OutCubic }
            }

            ParallelAnimation {
                id: correction
                NumberAnimation { target: ghost; property: "opacity"; from: 1; to: 0; duration: 160 * line.ms; easing.type: Easing.OutCubic }
                NumberAnimation { target: label; property: "opacity"; from: 0; to: 1; duration: 160 * line.ms; easing.type: Easing.OutCubic }
            }
        }
    }
}
```

Note `text` of the delegate is the model role; the test reads `property("text")` on the delegate, which is the role value.

- [ ] **Step 4:** run → PASS (tune only if a test exposes a real bug; ledger rulings). **Commit** (git add) — "Lay out caption words one by one with soft motion".

---

### Task 5: Overlay and SubtitleView use CaptionLine; remove the markup path

**Files:** Modify `echoline/ui/qml/Overlay.qml`, `echoline/ui/qml/SubtitleView.qml`, `echoline/ui/qml/Settings.qml`, `echoline/settings/model.py`; Delete `echoline/ui/qml/captions.js`; Test `tests/test_overlay_qml.py`, `tests/test_settings_window.py`, `tests/test_settings_model.py`

**Consumes:** `CaptionLine` (Task 4), `latestWords`/`words` (Task 2), `motion` context (Task 3).

- [ ] **Step 1: Update tests first**
  - Remove from `tests/test_overlay_qml.py`: `test_dim_mode_dims_only_the_words_still_changing`, `test_hide_mode_shows_only_settled_words`, `test_hide_mode_never_shows_a_blank_line_or_blank_subtitle`, `test_subtitle_follows_a_switch_between_dim_and_hide`, the `plain()` helper (and `import re`).
  - `visible_text(item)` → `item.findChild(QObject, "subtitleLine").property("text")`.
  - In `test_subtitle_cross_fades_from_the_previous_phrase`, keep the `subtitleOutgoing` assertions (plain text) and `visible_text == "second"`.
  - Remove `test_unsettled_words_box_switches_between_dim_and_hide` from `tests/test_settings_window.py`.
  - Add to `tests/test_overlay_qml.py`:
    ```python
    def test_rolling_lines_are_word_layouts(overlay):
        window, captions, _, warnings = overlay
        captions.apply([Final(0, "first line."), Partial(1, "second words")])
        settle()
        lines = caption_lines(window)
        assert [line.property("text") for line in lines] == ["first line.", "second words"]
        assert warnings == []


    def test_lines_scrolled_above_the_top_fade_out(overlay):
        window, captions, _, _ = overlay
        window.store.setValue("line_count", 1)
        captions.apply([Final(0, "older line."), Final(1, "newest line.")])
        settle(0.8)
        older, newest = caption_lines(window)
        assert newest.opacity() == 1.0 and older.opacity() < 0.5
    ```
  - Add to `tests/test_settings_model.py`:
    ```python
    def test_removed_unsettled_words_setting_is_ignored():
        assert not hasattr(validate({"unsettled_words": "hide"}), "unsettled_words")
    ```
- [ ] **Step 2:** run the three files → new tests FAIL.
- [ ] **Step 3: Implement**
  - `Overlay.qml`: drop `import "captions.js"`; rolling delegate becomes
    ```qml
    delegate: CaptionLine {
        required property var model
        objectName: "captionLine"
        property int utteranceId: model.utteranceId
        width: captionColumn.width
        words: model.words
        s: overlay.s
        // Fade out as the line scrolls above the top edge instead of being cut off.
        opacity: Math.max(0, Math.min(1, 1 + (captionColumn.y + y) / Math.max(1, overlay.lineHeight)))
    }
    ```
    Keep `CaptionText` component only if still used elsewhere in Overlay (the status/latency texts don't use it → remove it if unused).
  - `SubtitleView.qml`: remove the markup import/property; incoming phrase:
    ```qml
    CaptionLine {
        id: incoming
        objectName: "subtitleLine"
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        words: captions.latestWords
        s: root.s
    }
    ```
    Outgoing stays a plain `SubtitleText` (objectName `subtitleOutgoing`). `Connections { target: captions; function onLatestChanged() { if (captions.latestId !== root.shownId && root.shownId !== -1) { outgoing.text = root.shownText; crossFade.restart() } root.shownId = captions.latestId; root.shownText = captions.latestText } }`; crossFade animates `outgoing` 1→0 and `incoming` 0→1 (200 ms × `motion.scale`).
  - `Settings.qml`: delete the "Words still changing" `Row2`.
  - `settings/model.py`: delete `unsettled_words` field and its `CHOICES` entry.
  - `git rm echoline/ui/qml/captions.js`.
- [ ] **Step 4:** run `tests/test_overlay_qml.py tests/test_settings_window.py tests/test_settings_model.py tests/test_onboarding_window.py` → PASS, no warnings. **Commit** — "Draw overlay captions word by word; drop the hide mode" (body: Dimmed won the comparison; settled words fade to full brightness instead of markup).

---

### Task 6: Real-display motion check, docs, full suite

- [ ] Script (scratchpad) that loads the real overlay on the Windows platform, feeds a scripted sequence (append words, a correction, a long line that re-wraps, settle, a Final, the next utterance), grabs `window.grabWindow()` every ~33 ms for ~4 s, and writes `text-flow.gif` with Pillow (`frames[0].save(..., save_all=True, append_images=frames[1:], duration=33, loop=0)`). Review the frames; fix real problems with failing-first tests.
- [ ] README "Customizing": mention captions fade in word by word, still-changing words are dimmed, and motion follows Windows' animation setting.
- [ ] `pytest -q` full → green except the known worktree failure; `graphify update .`.
- [ ] Commit — "Document the new caption motion".

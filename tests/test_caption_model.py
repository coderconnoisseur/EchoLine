from PySide6.QtCore import QCoreApplication, Qt

from echoline.captions.model import CaptionModel
from echoline.engine.base import Final, Partial

app = QCoreApplication.instance() or QCoreApplication([])


def rows(model):
    names = {v.data().decode(): k for k, v in model.roleNames().items()}
    return [
        (model.data(model.index(r), names["utteranceId"]),
         model.data(model.index(r), names["text"]),
         model.data(model.index(r), names["final"]))
        for r in range(model.rowCount())
    ]


def test_partial_updates_its_row_in_place():
    model = CaptionModel()
    inserted, changed = [], []
    model.rowsInserted.connect(lambda *a: inserted.append(a[1]))
    model.dataChanged.connect(lambda top, bottom, roles: changed.append(top.row()))

    model.apply([Partial(0, "It was")])
    model.apply([Partial(0, "It was the best")])
    model.apply([Final(0, "It was the best.")])

    assert rows(model) == [(0, "It was the best.", True)]
    assert inserted == [0]
    assert changed == [0, 0]


def test_new_utterances_append_rows():
    model = CaptionModel()

    model.apply([Final(0, "one."), Partial(1, "two")])

    assert rows(model) == [(0, "one.", True), (1, "two", False)]


def test_oldest_rows_are_removed_beyond_the_limit():
    model = CaptionModel(max_utterances=3)

    model.apply([Final(i, f"line {i}") for i in range(5)])

    assert [r[0] for r in rows(model)] == [2, 3, 4]


def test_late_event_for_dropped_utterance_is_ignored():
    model = CaptionModel(max_utterances=2)
    model.apply([Final(i, f"line {i}") for i in range(4)])

    model.apply([Final(0, "late")])

    assert [r[0] for r in rows(model)] == [2, 3]


def test_unicode_text_round_trips():
    model = CaptionModel()

    model.apply([Final(0, "café — naïve 👍")])

    assert rows(model)[0][1] == "café — naïve 👍"

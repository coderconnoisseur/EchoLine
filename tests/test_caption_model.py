import time

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


def test_latest_utterance_is_exposed_for_subtitle_mode():
    model = CaptionModel()
    seen = []
    model.latestChanged.connect(lambda: seen.append((model.property("latestId"), model.property("latestText"))))

    model.apply([Final(0, "one.")])
    model.apply([Partial(1, "tw")])
    model.apply([Partial(1, "two")])

    assert seen == [(0, "one."), (1, "tw"), (1, "two")]


def test_latest_is_empty_before_any_caption():
    model = CaptionModel()

    assert (model.property("latestId"), model.property("latestText")) == (-1, "")


def settled(model, row=0):
    names = {v.data().decode(): k for k, v in model.roleNames().items()}
    return model.data(model.index(row), names["settled"])


def test_settled_text_is_the_words_that_survived_an_update():
    model = CaptionModel()

    model.apply([Partial(0, "It was the")])
    assert settled(model) == ""                       # nothing confirmed yet

    model.apply([Partial(0, "It was the best")])
    assert settled(model) == "It was the"

    model.apply([Partial(0, "It was the beast of")])  # "best" was corrected
    assert settled(model) == "It was the"
    assert model.property("latestSettled") == "It was the"

    model.apply([Final(0, "It was the best of times.")])
    assert settled(model) == "It was the best of times."
    assert model.property("latestSettled") == "It was the best of times."


def test_a_correction_inside_settled_words_shrinks_them():
    model = CaptionModel()
    model.apply([Partial(0, "I scream")])
    model.apply([Partial(0, "I scream for")])
    model.apply([Partial(0, "Ice cream for you")])

    assert settled(model) == ""


def test_spacing_differences_do_not_unsettle_words():
    model = CaptionModel()
    model.apply([Partial(0, " It was")])
    model.apply([Partial(0, " It  was the best")])

    assert settled(model) == "It was"
    assert model.property("latestText") == "It was the best"


def test_a_guess_that_stops_changing_settles_after_a_pause():
    model = CaptionModel(settle_after_ms=50)
    model.apply([Partial(0, "It was the best of times")])
    deadline = time.monotonic() + 1
    while settled(model) != "It was the best of times" and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)

    assert settled(model) == "It was the best of times"
    assert model.property("latestSettled") == "It was the best of times"

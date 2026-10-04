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

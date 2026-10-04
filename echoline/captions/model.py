from PySide6.QtCore import Property, QAbstractListModel, QByteArray, QModelIndex, QObject, Qt, QTimer, Signal

from ..engine.base import Final
from .words import WordModel

ID_ROLE = Qt.UserRole + 1
TEXT_ROLE = Qt.UserRole + 2
FINAL_ROLE = Qt.UserRole + 3
SETTLED_ROLE = Qt.UserRole + 4
WORDS_ROLE = Qt.UserRole + 5


def settled_prefix(before, after):
    """The leading words two successive guesses agree on: unlikely to change again."""
    same = []
    for old, new in zip(before.split(), after.split()):
        if old != new:
            break
        same.append(new)
    return " ".join(same)


class CaptionModel(QAbstractListModel):
    """Recent utterances for the overlay; partials update their row in place."""

    latestChanged = Signal()

    def __init__(self, max_utterances=6, settle_after_ms=600, parent=None):
        super().__init__(parent)
        self.max_utterances = max_utterances
        # Moonshine only sends a new guess when the text changes, so the last words
        # of a phrase would wait for the final; a guess that holds this long has settled.
        self._settle_timer = QTimer(self, singleShot=True, interval=settle_after_ms)
        self._settle_timer.timeout.connect(self._settle_all)
        self._rows = []          # [utterance_id, text, final, settled, WordModel]
        self._highest_dropped = -1

    def roleNames(self):
        return {ID_ROLE: QByteArray(b"utteranceId"), TEXT_ROLE: QByteArray(b"text"),
                FINAL_ROLE: QByteArray(b"final"), SETTLED_ROLE: QByteArray(b"settled"),
                WORDS_ROLE: QByteArray(b"words")}

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        utterance_id, text, final, settled, words = self._rows[index.row()]
        return {ID_ROLE: utterance_id, TEXT_ROLE: text, Qt.DisplayRole: text, FINAL_ROLE: final,
                SETTLED_ROLE: settled, WORDS_ROLE: words}.get(role)

    def _latest(self):
        return self._rows[-1] if self._rows else (-1, "", False, "", None)

    def _get_latest_text(self):
        return self._latest()[1]

    def _get_latest_id(self):
        return self._latest()[0]

    def _get_latest_settled(self):
        return self._latest()[3]

    latestText = Property(str, _get_latest_text, notify=latestChanged)
    latestSettled = Property(str, _get_latest_settled, notify=latestChanged)
    latestId = Property(int, _get_latest_id, notify=latestChanged)
    latestWords = Property(QObject, lambda self: self._latest()[4], notify=latestChanged)

    @staticmethod
    def _sync_words(entry):
        entry[4].update(entry[1].split(), len(entry[3].split()))

    def apply(self, events):
        before = tuple(self._latest()[:4])
        for event in events:
            self._apply_one(event.utterance_id, " ".join(event.text.split()), isinstance(event, Final))
        if tuple(self._latest()[:4]) != before:
            self.latestChanged.emit()
        if any(not entry[2] for entry in self._rows):
            self._settle_timer.start()

    def _settle_all(self):
        before = tuple(self._latest()[:4])
        for row, entry in enumerate(self._rows):
            if entry[3] != entry[1]:
                entry[3] = entry[1]
                self._sync_words(entry)
                index = self.index(row)
                self.dataChanged.emit(index, index, [SETTLED_ROLE])
        if tuple(self._latest()[:4]) != before:
            self.latestChanged.emit()

    def _apply_one(self, utterance_id, text, final):
        if utterance_id <= self._highest_dropped:
            return
        for row, entry in enumerate(self._rows):
            if entry[0] == utterance_id:
                entry[1], entry[2], entry[3] = text, final, text if final else settled_prefix(entry[1], text)
                self._sync_words(entry)
                index = self.index(row)
                self.dataChanged.emit(index, index, [TEXT_ROLE, FINAL_ROLE, SETTLED_ROLE])
                return
        self.beginInsertRows(QModelIndex(), len(self._rows), len(self._rows))
        entry = [utterance_id, text, final, text if final else "", WordModel(self)]
        self._sync_words(entry)
        self._rows.append(entry)
        self.endInsertRows()
        if len(self._rows) > self.max_utterances:
            self.beginRemoveRows(QModelIndex(), 0, 0)
            dropped = self._rows.pop(0)
            self._highest_dropped = dropped[0]
            dropped[4].deleteLater()
            self.endRemoveRows()

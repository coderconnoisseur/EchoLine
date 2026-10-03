from PySide6.QtCore import Property, QAbstractListModel, QByteArray, QModelIndex, Qt, Signal

from ..engine.base import Final

ID_ROLE = Qt.UserRole + 1
TEXT_ROLE = Qt.UserRole + 2
FINAL_ROLE = Qt.UserRole + 3


class CaptionModel(QAbstractListModel):
    """Recent utterances for the overlay; partials update their row in place."""

    latestChanged = Signal()

    def __init__(self, max_utterances=6, parent=None):
        super().__init__(parent)
        self.max_utterances = max_utterances
        self._rows = []          # [utterance_id, text, final]
        self._highest_dropped = -1

    def roleNames(self):
        return {ID_ROLE: QByteArray(b"utteranceId"), TEXT_ROLE: QByteArray(b"text"),
                FINAL_ROLE: QByteArray(b"final")}

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        utterance_id, text, final = self._rows[index.row()]
        return {ID_ROLE: utterance_id, TEXT_ROLE: text, Qt.DisplayRole: text, FINAL_ROLE: final}.get(role)

    def _latest(self):
        return self._rows[-1] if self._rows else (-1, "", False)

    def _get_latest_text(self):
        return self._latest()[1]

    def _get_latest_id(self):
        return self._latest()[0]

    latestText = Property(str, _get_latest_text, notify=latestChanged)
    latestId = Property(int, _get_latest_id, notify=latestChanged)

    def apply(self, events):
        before = tuple(self._latest()[:2])
        for event in events:
            self._apply_one(event.utterance_id, event.text, isinstance(event, Final))
        if tuple(self._latest()[:2]) != before:
            self.latestChanged.emit()

    def _apply_one(self, utterance_id, text, final):
        if utterance_id <= self._highest_dropped:
            return
        for row, entry in enumerate(self._rows):
            if entry[0] == utterance_id:
                entry[1], entry[2] = text, final
                index = self.index(row)
                self.dataChanged.emit(index, index, [TEXT_ROLE, FINAL_ROLE])
                return
        self.beginInsertRows(QModelIndex(), len(self._rows), len(self._rows))
        self._rows.append([utterance_id, text, final])
        self.endInsertRows()
        if len(self._rows) > self.max_utterances:
            self.beginRemoveRows(QModelIndex(), 0, 0)
            self._highest_dropped = self._rows.pop(0)[0]
            self.endRemoveRows()

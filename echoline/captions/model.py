from PySide6.QtCore import QAbstractListModel, QByteArray, QModelIndex, Qt

from ..engine.base import Final

ID_ROLE = Qt.UserRole + 1
TEXT_ROLE = Qt.UserRole + 2
FINAL_ROLE = Qt.UserRole + 3


class CaptionModel(QAbstractListModel):
    """Recent utterances for the overlay; partials update their row in place."""

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

    def apply(self, events):
        for event in events:
            self._apply_one(event.utterance_id, event.text, isinstance(event, Final))

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

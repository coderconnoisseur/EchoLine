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

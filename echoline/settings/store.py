from dataclasses import asdict, replace

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from .model import save_settings, validate
from .themes import PRESETS, THEMED_KEYS, apply_theme, theme_name_for


class SettingsStore(QObject):
    """Live settings shared by the overlay and the settings window; saves after edits settle."""

    valuesChanged = Signal()

    def __init__(self, settings, path, save_delay_ms=400, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.path = path
        self.pending_save = False
        self._timer = QTimer(self, singleShot=True, interval=save_delay_ms)
        self._timer.timeout.connect(self.save_now)

    def _get_values(self):
        return asdict(self.settings)

    values = Property("QVariantMap", _get_values, notify=valuesChanged)

    def _get_theme_names(self):
        return list(PRESETS)

    themeNames = Property(list, _get_theme_names, constant=True)

    def _update(self, settings):
        if settings == self.settings:
            return
        self.settings = settings
        self.valuesChanged.emit()
        self.pending_save = True
        self._timer.start()

    @Slot(str, "QVariant")
    def setValue(self, key, value):
        current = asdict(self.settings)
        if key not in current:
            return
        updated = validate({**current, key: value})
        if key in THEMED_KEYS:
            updated = replace(updated, theme=theme_name_for(updated))
        self._update(updated)

    @Slot(str)
    def applyTheme(self, name):
        self._update(apply_theme(self.settings, name))

    @Slot()
    def save_now(self):
        if self.pending_save:
            self._timer.stop()
            save_settings(self.settings, self.path)
            self.pending_save = False

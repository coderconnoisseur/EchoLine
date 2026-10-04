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

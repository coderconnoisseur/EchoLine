from PySide6.QtCore import QObject, Signal

class OverlaySignals(QObject):
    """Signal object for thread-safe GUI updates"""
    update_text = Signal(str, bool)  # text, is_partial
    app_closing = Signal()  # Signal to notify app is closing
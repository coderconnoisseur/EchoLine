from PySide6.QtQuickControls2 import QQuickStyle


def use_fluent_style():
    """Native-looking Windows 11 controls for the settings window."""
    QQuickStyle.setStyle("FluentWinUI3")
    return QQuickStyle.name()

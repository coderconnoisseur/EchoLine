from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from .icon import app_icon


class TrayIcon:
    """Tray icon and menu: the way back to EchoLine when captions are hidden or click-through."""

    def __init__(self, app):
        self.app = app
        self.menu = QMenu()
        self.icon = QSystemTrayIcon(app_icon())
        self.icon.setToolTip("EchoLine — live captions")
        self.icon.setContextMenu(self.menu)
        self.icon.activated.connect(self._activated)

        def item(name, text, slot, checkable=False):
            act = QAction(text, self.menu, checkable=checkable)
            act.setObjectName(name)
            act.triggered.connect(slot)
            self.menu.addAction(act)
            return act

        self.show_hide = item("showHide", "Hide captions", lambda: app.set_visible(not app.visible))
        self.pause = item("pause", "Pause", lambda checked: app.set_paused(checked), checkable=True)
        self.click_through = item("clickThrough", "Click-through",
                                  lambda checked: app.set_click_through(checked), checkable=True)
        self.source_menu = self.menu.addMenu("Audio source")
        self.source_menu.setObjectName("source")
        group = QActionGroup(self.source_menu)
        self.sources = {}
        for kind, label in (("system", "System audio"), ("microphone", "Microphone")):
            act = QAction(label, self.source_menu, checkable=True)
            act.triggered.connect(lambda checked, k=kind: app.set_source(k))
            group.addAction(act)
            self.source_menu.addAction(act)
            self.sources[kind] = act
        self.menu.addSeparator()
        item("settings", "Settings…", app.open_settings)
        item("quit", "Quit EchoLine", app.quit)
        self.refresh()
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.icon.show()

    def _activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.app.set_visible(not self.app.visible)

    def refresh(self):
        self.show_hide.setText("Hide captions" if self.app.visible else "Show captions")
        self.pause.setChecked(self.app.paused)
        self.click_through.setChecked(self.app.settings_store.settings.click_through)
        self.sources[self.app.settings_store.settings.audio_source].setChecked(True)

    def hide(self):
        self.icon.hide()

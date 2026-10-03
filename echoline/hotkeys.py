import ctypes
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter

MODIFIERS = {"Alt": 0x1, "Ctrl": 0x2, "Shift": 0x4, "Win": 0x8}
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312


def parse_hotkey(text):
    """'Ctrl+Alt+C' -> (modifier bits, virtual key), or None if empty/invalid."""
    parts = text.split("+") if text else []
    if len(parts) < 2:
        return None
    *mods, key = parts
    if any(m not in MODIFIERS for m in mods):
        return None
    if len(key) == 1 and (key.isdigit() or "A" <= key <= "Z"):
        vk = ord(key)
    elif key.startswith("F") and key[1:].isdigit() and 1 <= int(key[1:]) <= 12:
        vk = 0x70 + int(key[1:]) - 1
    else:
        return None
    bits = MOD_NOREPEAT
    for m in mods:
        bits |= MODIFIERS[m]
    return bits, vk


class HotkeyManager(QAbstractNativeEventFilter):
    """System-wide hotkeys via RegisterHotKey on a hidden window."""

    def __init__(self, hwnd, user32=None):
        super().__init__()
        self._hwnd = hwnd
        self._user32 = user32 or ctypes.windll.user32
        self._callbacks = {}      # id -> callback
        self._next_id = 1
        self.failed = []

    def register(self, name, text, callback):
        parsed = parse_hotkey(text)
        if parsed is None:
            return False
        hotkey_id = self._next_id
        self._next_id += 1
        if not self._user32.RegisterHotKey(self._hwnd, hotkey_id, *parsed):
            self.failed.append(name)
            return False
        self._callbacks[hotkey_id] = callback
        return True

    def unregister_all(self):
        for hotkey_id in list(self._callbacks):
            self._user32.UnregisterHotKey(self._hwnd, hotkey_id)
        self._callbacks.clear()
        self.failed = []

    def nativeEventFilter(self, event_type, message):
        msg = wintypes.MSG.from_address(int(message))
        if msg.message == WM_HOTKEY and msg.wParam in self._callbacks:
            self._callbacks[msg.wParam]()
            return True, 0           # consume: Windows delivers it through two hooks
        return False, 0

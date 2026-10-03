import ctypes
from ctypes import wintypes

from echoline.hotkeys import HotkeyManager, parse_hotkey


def test_parse_hotkey():
    assert parse_hotkey("Ctrl+Alt+C") == (0x2 | 0x1 | 0x4000, ord("C"))
    assert parse_hotkey("Shift+Win+F9") == (0x4 | 0x8 | 0x4000, 0x78)
    assert parse_hotkey("Ctrl+Alt+7") == (0x2 | 0x1 | 0x4000, ord("7"))
    assert parse_hotkey("") is None
    assert parse_hotkey("C") is None             # needs a modifier
    assert parse_hotkey("Ctrl+Alt+Space") is None


class FakeUser32:
    def __init__(self, taken=()):
        self.taken = set(taken)
        self.registered = {}

    def RegisterHotKey(self, hwnd, hotkey_id, modifiers, key):
        if (modifiers, key) in self.taken:
            return 0
        self.registered[hotkey_id] = (modifiers, key)
        return 1

    def UnregisterHotKey(self, hwnd, hotkey_id):
        self.registered.pop(hotkey_id, None)
        return 1


def wm_hotkey(hotkey_id):
    msg = wintypes.MSG()
    msg.message = 0x0312
    msg.wParam = hotkey_id
    return msg


def test_registered_hotkey_calls_its_callback():
    user32 = FakeUser32()
    manager = HotkeyManager(hwnd=42, user32=user32)
    calls = []
    manager.register("pause", "Ctrl+Alt+P", lambda: calls.append("pause"))
    hotkey_id = next(iter(user32.registered))

    msg = wm_hotkey(hotkey_id)
    handled = manager.nativeEventFilter(b"windows_generic_MSG", ctypes.addressof(msg))

    assert handled == (True, 0) and calls == ["pause"]


def test_taken_hotkey_is_reported_and_others_still_register():
    user32 = FakeUser32(taken={parse_hotkey("Ctrl+Alt+C")})
    manager = HotkeyManager(hwnd=42, user32=user32)

    assert not manager.register("show_hide", "Ctrl+Alt+C", lambda: None)
    assert manager.register("pause", "Ctrl+Alt+P", lambda: None)
    assert manager.failed == ["show_hide"]


def test_other_messages_pass_through():
    manager = HotkeyManager(hwnd=42, user32=FakeUser32())
    msg = wintypes.MSG()
    msg.message = 0x0100   # WM_KEYDOWN

    assert manager.nativeEventFilter(b"windows_generic_MSG", ctypes.addressof(msg)) == (False, 0)


def test_unregister_all_releases_hotkeys():
    user32 = FakeUser32()
    manager = HotkeyManager(hwnd=42, user32=user32)
    manager.register("pause", "Ctrl+Alt+P", lambda: None)

    manager.unregister_all()

    assert user32.registered == {}

from echoline.ui.blur import ACCENT_DISABLED, ACCENT_ENABLE_ACRYLICBLURBEHIND, set_acrylic


class FakeUser32:
    def __init__(self):
        self.calls = []

    def SetWindowCompositionAttribute(self, hwnd, data_pointer):
        data = data_pointer._obj
        accent = data.Data.contents if hasattr(data.Data, "contents") else None
        self.calls.append((hwnd, data.Attribute, accent.AccentState))
        return 1


def test_enabling_requests_acrylic_blur():
    user32 = FakeUser32()

    assert set_acrylic(1234, True, user32=user32)
    assert user32.calls == [(1234, 19, ACCENT_ENABLE_ACRYLICBLURBEHIND)]


def test_disabling_turns_the_accent_off():
    user32 = FakeUser32()

    set_acrylic(1234, False, user32=user32)

    assert user32.calls[-1][2] == ACCENT_DISABLED


def test_missing_api_is_ignored():
    assert set_acrylic(1234, True, user32=object()) is False

from echoline.ui.blur import ACCENT_DISABLED, ACCENT_ENABLE_BLURBEHIND, set_blur


class FakeUser32:
    def __init__(self):
        self.accents = []
        self.regions = []

    def SetWindowCompositionAttribute(self, hwnd, data_pointer):
        data = data_pointer._obj
        self.accents.append((hwnd, data.Attribute, data.Data.contents.AccentState))
        return 1

    def SetWindowRgn(self, hwnd, region, redraw):
        self.regions.append((hwnd, region))
        return 1


class FakeGdi32:
    def __init__(self):
        self.created = []

    def CreateRoundRectRgn(self, left, top, right, bottom, width, height):
        self.created.append((left, top, right, bottom, width, height))
        return 777


def test_enabling_uses_plain_blur_with_rounded_corners():
    # Acrylic made dragging laggy on Windows 10 and blurred square corners.
    user32, gdi32 = FakeUser32(), FakeGdi32()

    assert set_blur(1234, True, size=(600, 120), radius=14, user32=user32, gdi32=gdi32)

    assert user32.accents == [(1234, 19, ACCENT_ENABLE_BLURBEHIND)]
    assert gdi32.created == [(0, 0, 601, 121, 28, 28)]
    assert user32.regions == [(1234, 777)]


def test_disabling_removes_blur_and_region():
    user32, gdi32 = FakeUser32(), FakeGdi32()

    set_blur(1234, False, size=(600, 120), radius=14, user32=user32, gdi32=gdi32)

    assert user32.accents[-1][2] == ACCENT_DISABLED
    assert user32.regions == [(1234, None)]


def test_missing_api_is_ignored():
    assert set_blur(1234, True, size=(600, 120), radius=14, user32=object(), gdi32=object()) is False

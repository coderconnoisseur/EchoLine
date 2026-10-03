import ctypes

ACCENT_DISABLED = 0
ACCENT_ENABLE_BLURBEHIND = 3
WCA_ACCENT_POLICY = 19


class AccentPolicy(ctypes.Structure):
    _fields_ = [("AccentState", ctypes.c_int), ("AccentFlags", ctypes.c_int),
                ("GradientColor", ctypes.c_uint), ("AnimationId", ctypes.c_int)]


class WindowCompositionAttributeData(ctypes.Structure):
    _fields_ = [("Attribute", ctypes.c_int), ("Data", ctypes.POINTER(AccentPolicy)),
                ("SizeOfData", ctypes.c_size_t)]


def set_blur(hwnd, enabled, size, radius, user32=None, gdi32=None):
    """Blur whatever is behind the overlay. Best effort: no-op where unsupported.

    Uses plain blur-behind rather than acrylic, which makes dragging laggy on
    Windows 10, and clips the window to a rounded region so the blur does not
    show square corners. `size` and `radius` are in physical pixels.
    """
    if user32 is None:
        user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
    set_attribute = getattr(user32, "SetWindowCompositionAttribute", None)
    set_region = getattr(user32, "SetWindowRgn", None)
    round_region = getattr(gdi32, "CreateRoundRectRgn", None)
    if set_attribute is None or set_region is None or round_region is None:
        return False
    accent = AccentPolicy(ACCENT_ENABLE_BLURBEHIND if enabled else ACCENT_DISABLED, 0, 0, 0)
    data = WindowCompositionAttributeData(WCA_ACCENT_POLICY, ctypes.pointer(accent), ctypes.sizeof(accent))
    ok = bool(set_attribute(hwnd, ctypes.byref(data)))
    if enabled:
        width, height = size
        # The window owns the region after SetWindowRgn, so it is not deleted here.
        set_region(hwnd, round_region(0, 0, width + 1, height + 1, 2 * radius, 2 * radius), True)
    else:
        set_region(hwnd, None, True)
    return ok

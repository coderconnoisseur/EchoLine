import ctypes
from ctypes import wintypes

ACCENT_DISABLED = 0
ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
WCA_ACCENT_POLICY = 19


class AccentPolicy(ctypes.Structure):
    _fields_ = [("AccentState", ctypes.c_int), ("AccentFlags", ctypes.c_int),
                ("GradientColor", ctypes.c_uint), ("AnimationId", ctypes.c_int)]


class WindowCompositionAttributeData(ctypes.Structure):
    _fields_ = [("Attribute", ctypes.c_int), ("Data", ctypes.POINTER(AccentPolicy)),
                ("SizeOfData", ctypes.c_size_t)]


def set_acrylic(hwnd, enabled, user32=None):
    """Blur whatever is behind the overlay (Windows 10 1803+). Best effort: no-op if unsupported."""
    if user32 is None:
        user32 = ctypes.windll.user32
    set_attribute = getattr(user32, "SetWindowCompositionAttribute", None)
    if set_attribute is None:
        return False
    accent = AccentPolicy(ACCENT_ENABLE_ACRYLICBLURBEHIND if enabled else ACCENT_DISABLED, 0,
                          0x01000000, 0)   # near-transparent tint; the panel draws the color
    data = WindowCompositionAttributeData(WCA_ACCENT_POLICY, ctypes.pointer(accent), ctypes.sizeof(accent))
    return bool(set_attribute(wintypes.HWND(hwnd).value or hwnd, ctypes.byref(data)))

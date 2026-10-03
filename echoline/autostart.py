import subprocess
import sys
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE = "EchoLine"


def launch_command():
    """Command Windows runs at sign-in: the packaged exe, or this checkout via pythonw (no console)."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    root = Path(__file__).resolve().parent.parent
    # A Run entry starts in an arbitrary folder, so put the checkout on the path explicitly.
    bootstrap = f"import sys, runpy; sys.path.insert(0, {str(root)!r}); runpy.run_module('echoline', run_name='__main__')"
    # list2cmdline quotes and escapes exactly the way Windows splits a command line.
    return subprocess.list2cmdline([str(pythonw), "-c", bootstrap])


def _registry(registry):
    if registry is None:
        import winreg as registry
    return registry


def set_start_with_windows(enabled, registry=None):
    reg = _registry(registry)
    with reg.OpenKey(reg.HKEY_CURRENT_USER, RUN_KEY, 0, reg.KEY_SET_VALUE) as key:
        if enabled:
            reg.SetValueEx(key, VALUE, 0, reg.REG_SZ, launch_command())
        else:
            try:
                reg.DeleteValue(key, VALUE)
            except FileNotFoundError:
                pass


def is_start_with_windows(registry=None):
    reg = _registry(registry)
    try:
        with reg.OpenKey(reg.HKEY_CURRENT_USER, RUN_KEY, 0, reg.KEY_READ) as key:
            reg.QueryValueEx(key, VALUE)
            return True
    except FileNotFoundError:
        return False

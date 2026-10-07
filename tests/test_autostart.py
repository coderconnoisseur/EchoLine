from echoline.autostart import RUN_KEY, VALUE, is_start_with_windows, launch_command, set_start_with_windows


class FakeRegistry:
    HKEY_CURRENT_USER = "HKCU"
    KEY_SET_VALUE = 2
    KEY_READ = 1
    REG_SZ = 1

    def __init__(self):
        self.values = {}

    def OpenKey(self, root, path, reserved=0, access=0):
        assert (root, path) == ("HKCU", RUN_KEY)
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def SetValueEx(self, key, name, reserved, kind, value):
        self.values[name] = value

    def DeleteValue(self, key, name):
        if name not in self.values:
            raise FileNotFoundError(name)
        del self.values[name]

    def QueryValueEx(self, key, name):
        if name not in self.values:
            raise FileNotFoundError(name)
        return self.values[name], 1


def test_enable_writes_the_launch_command():
    registry = FakeRegistry()

    set_start_with_windows(True, registry=registry)

    assert registry.values[VALUE] == launch_command()
    assert is_start_with_windows(registry=registry)


def test_disable_removes_it_and_is_safe_when_absent():
    registry = FakeRegistry()
    set_start_with_windows(True, registry=registry)

    set_start_with_windows(False, registry=registry)
    set_start_with_windows(False, registry=registry)

    assert not is_start_with_windows(registry=registry)


def test_launch_command_runs_the_checkout_without_a_console():
    from pathlib import Path

    import echoline

    command = launch_command()
    assert "pythonw" in command.lower()
    # The checkout path is embedded as a Python string literal, backslashes escaped.
    assert repr(str(Path(echoline.__file__).resolve().parent.parent)) in command
    assert "run_module('echoline'" in command


def windows_split(command):
    """Split a command line exactly as Windows does for a new process."""
    import ctypes
    from ctypes import wintypes

    shell32 = ctypes.windll.shell32
    shell32.CommandLineToArgvW.restype = ctypes.POINTER(wintypes.LPWSTR)
    count = ctypes.c_int()
    argv = shell32.CommandLineToArgvW(command, ctypes.byref(count))
    try:
        return [argv[i] for i in range(count.value)]
    finally:
        ctypes.windll.kernel32.LocalFree(argv)


def test_windows_passes_the_bootstrap_intact_for_awkward_paths(monkeypatch, tmp_path):
    import ast

    import echoline.autostart as autostart

    root = tmp_path / "O'Brien \"quoted\" dir" / "EchoLine"
    monkeypatch.setattr(autostart, "__file__", str(root / "echoline" / "autostart.py"))

    args = windows_split(launch_command())

    assert args[0].lower().endswith("pythonw.exe") and args[1] == "-c"
    ast.parse(args[2])
    assert str(root) in args[2] or repr(str(root)) in args[2]

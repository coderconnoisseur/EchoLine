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
    assert str(Path(echoline.__file__).resolve().parent.parent) in command
    assert "run_module('echoline'" in command

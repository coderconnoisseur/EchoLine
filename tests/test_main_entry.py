import os
import subprocess
import sys

from echoline.settings.model import Settings


def test_entry_point_creates_a_widgets_application():
    # The tray icon (QSystemTrayIcon) needs QApplication, not QGuiApplication.
    script = (
        "import sys, os\n"
        "os.environ['QT_QPA_PLATFORM'] = 'offscreen'\n"
        "import echoline.__main__ as m, echoline.app as a\n"
        "from PySide6.QtCore import QCoreApplication\n"
        "def stop(*args, **kwargs):\n"
        "    app = QCoreApplication.instance()\n"
        "    print(type(app).__name__, app.quitOnLastWindowClosed())\n"
        "    sys.exit(0)\n"
        "a.EchoLineApp = stop\n"
        "m.main([])\n"
    )
    out = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=60)

    assert out.stdout.strip() == "QApplication False", out.stderr[-400:]


def test_startup_mode():
    from echoline.__main__ import startup_mode

    have = lambda name: name == "tiny"                       # noqa: E731
    assert startup_mode(Settings(), "", have) == "setup"
    assert startup_mode(Settings(onboarded=False, model="tiny"), "tiny", have) == "setup"
    assert startup_mode(Settings(onboarded=True, model="tiny"), "tiny", have) == "run"
    assert startup_mode(Settings(onboarded=True, model="small"), "small", have) == "repair"   # files gone
    assert startup_mode(Settings(onboarded=True), "", have) == "setup"


def test_packaged_app_writes_output_to_a_log(tmp_path, monkeypatch):
    # A windowed exe has no console: stderr is None, so every traceback.print_exc()
    # in the app would itself raise. Output goes to a log people can send instead.
    import traceback

    from echoline.__main__ import log_to_file_when_frozen

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    log = log_to_file_when_frozen(tmp_path / "EchoLine" / "echoline.log")
    try:
        raise RuntimeError("engine hiccup")
    except RuntimeError:
        traceback.print_exc()
    print("still running")
    sys.stderr.close()

    text = log.read_text(encoding="utf-8")
    assert "engine hiccup" in text and "still running" in text


def test_source_runs_keep_the_console(monkeypatch):
    from echoline.__main__ import log_to_file_when_frozen

    monkeypatch.delattr(sys, "frozen", raising=False)
    assert log_to_file_when_frozen() is None


def test_packaged_log_starts_with_machine_details(tmp_path, monkeypatch):
    # A tester's crash log said only "access violation"; the log now records
    # what machine it came from so reports can be diagnosed without a back-and-forth.
    from echoline.__main__ import log_to_file_when_frozen

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    log = log_to_file_when_frozen(tmp_path / "EchoLine" / "echoline.log")
    sys.stderr.close()

    text = log.read_text(encoding="utf-8")
    for field in ("EchoLine", "Windows", "CPU", "Architecture", "Models"):
        assert field in text, field


def test_model_flag_does_not_decide_startup_mode(tmp_path):
    # An undownloaded --model used to look like a damaged install: repair fetched and saved it.
    script = """
import json, os, sys
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import echoline.__main__ as m, echoline.app as a, echoline.instance as i, echoline.models as models
from echoline.settings.model import default_settings_path
path = default_settings_path()
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps({'onboarded': True, 'model': 'tiny'}))
i.notify_running = lambda name: False
models.is_downloaded = lambda name: name == 'tiny'
class Fake:
    def __init__(self, *args, **kwargs): pass
    def run_setup(self, model=None): print('setup', model); sys.exit(0)
    def start(self): print('run'); sys.exit(0)
    def bring_to_front(self): pass
    def shutdown(self): pass
a.EchoLineApp = Fake
m.main(['--model', 'small'])
"""
    env = {**os.environ, "APPDATA": str(tmp_path)}
    out = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=60, env=env)

    assert out.stdout.strip().splitlines()[-1:] == ["run"], out.stderr[-400:]


def test_model_flag_only_applies_to_a_normal_run_with_the_files_present():
    # Otherwise repair saves it for good and setup downloads it with no progress.
    from echoline.__main__ import one_run_model

    have = lambda name: name == "tiny"                       # noqa: E731
    assert one_run_model("tiny", "run", have) == "tiny"
    assert one_run_model("small", "run", have) is None
    assert one_run_model("tiny", "repair", have) is None
    assert one_run_model("tiny", "setup", have) is None
    assert one_run_model(None, "run", have) is None

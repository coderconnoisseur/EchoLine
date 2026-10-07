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

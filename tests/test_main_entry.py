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

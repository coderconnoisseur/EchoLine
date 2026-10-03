import subprocess
import sys


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

import time
import uuid

from PySide6.QtGui import QGuiApplication

from echoline.instance import InstanceServer, notify_running, server_name

app = QGuiApplication.instance()


def test_server_name_is_per_user():
    assert server_name().startswith("EchoLine-") and len(server_name()) > len("EchoLine-")


def test_second_launch_reaches_the_first():
    name = f"EchoLine-test-{uuid.uuid4().hex}"
    assert notify_running(name) is False         # nobody there yet
    server = InstanceServer(name)
    shown = []
    server.shown.connect(lambda: shown.append(True))

    assert notify_running(name) is True
    deadline = time.monotonic() + 3
    while not shown and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    assert shown == [True]
    server.close()

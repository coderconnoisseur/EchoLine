import getpass

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket


def server_name():
    return f"EchoLine-{getpass.getuser()}"


def notify_running(name, timeout_ms=500) -> bool:
    """Ask an already-running EchoLine to show itself; False if none answered.

    Connecting is the whole message: the running copy has one thing to do.
    """
    socket = QLocalSocket()
    socket.connectToServer(name)
    if not socket.waitForConnected(timeout_ms):
        return False
    socket.disconnectFromServer()
    return True


class InstanceServer(QObject):
    """Listens for later launches; emits `shown` when one connects."""

    shown = Signal()

    def __init__(self, name, parent=None):
        super().__init__(parent)
        # ponytail: two launches in the same instant can both start; acceptable for a tray app.
        QLocalServer.removeServer(name)          # left behind by a crash
        self._server = QLocalServer(self)
        self._server.setSocketOptions(QLocalServer.UserAccessOption)
        self._server.newConnection.connect(self._accept)
        self._server.listen(name)

    def _accept(self):
        while self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            socket.disconnected.connect(socket.deleteLater)
            socket.disconnectFromServer()
            self.shown.emit()

    def close(self):
        self._server.close()

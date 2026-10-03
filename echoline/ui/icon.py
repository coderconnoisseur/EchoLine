from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap


def app_icon():
    """A rounded dark badge with 'CC', drawn so no image assets are needed."""
    icon = QIcon()
    for size in (16, 24, 32, 48, 256):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#1f1f1f"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(QRectF(0, 0, size, size), size * 0.22, size * 0.22)
        font = QFont("Segoe UI")
        font.setBold(True)
        font.setPixelSize(max(1, int(size * 0.5)))
        painter.setFont(font)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, "CC")
        painter.end()
        icon.addPixmap(pixmap)
    return icon

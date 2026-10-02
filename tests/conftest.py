import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

# Qt allows one application object per process, and its type decides what
# works: QApplication covers widgets, QML and plain Qt objects. Create it
# before any test module can create a narrower QCoreApplication.
APP = QApplication.instance() or QApplication([])

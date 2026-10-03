import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# moonshine.dll cannot initialise once Qt is loaded, so load it first.
from echoline.engine.moonshine_engine import preload_native_library

preload_native_library()

from PySide6.QtWidgets import QApplication  # noqa: E402

# Qt allows one application object per process, and its type decides what
# works: QApplication covers widgets, QML and plain Qt objects. Create it
# before any test module can create a narrower QCoreApplication.
APP = QApplication.instance() or QApplication([])

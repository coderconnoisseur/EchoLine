import os

# A small laptop screen (1366x768 at 125% scaling) so size limits are exercised.
# Qt splits platform arguments on ":", so the path must not contain a drive letter.
_SCREEN = os.path.relpath(os.path.join(os.path.dirname(__file__), "offscreen_screen.json")).replace("\\", "/")
os.environ.setdefault("QT_QPA_PLATFORM", f"offscreen:configfile={_SCREEN}")

# moonshine.dll cannot initialise once Qt is loaded, so load it first.
from echoline.engine.moonshine_engine import preload_native_library

preload_native_library()

from PySide6.QtWidgets import QApplication  # noqa: E402

# Qt allows one application object per process, and its type decides what
# works: QApplication covers widgets, QML and plain Qt objects. Create it
# before any test module can create a narrower QCoreApplication.
APP = QApplication.instance() or QApplication([])

# The controls style is fixed once any QML loads controls; use the app's style
# so every QML test runs under what users see.
from echoline.ui.style import use_fluent_style  # noqa: E402

use_fluent_style()

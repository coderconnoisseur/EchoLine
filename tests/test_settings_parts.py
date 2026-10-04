import time

import shiboken6
from PySide6.QtCore import QObject, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem

from echoline.ui.overlay import QML_DIR

app = QGuiApplication.instance()
PARTS = QML_DIR / "settings"


def settle(seconds=0.2):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)


def build(qml, context=None):
    """Instantiate QML that uses the settings parts; returns (engine, root item, warnings)."""
    engine = QQmlEngine()
    warnings = []
    engine.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))
    for name, value in (context or {}).items():
        engine.rootContext().setContextProperty(name, value)
    component = QQmlComponent(engine)
    component.setData(qml.encode(), QUrl.fromLocalFile(str(PARTS / "probe.qml")))
    created = component.create()
    assert created is not None, component.errors()
    engine.keep = (component, created)            # the item dies with these wrappers
    return engine, shiboken6.wrapInstance(shiboken6.getCppPointer(created)[0], QQuickItem), warnings


def test_card_rows_and_theme_tokens():
    engine, root, warnings = build("""
import QtQuick
import QtQuick.Controls
Item {
    width: 500; height: 400
    Theme { id: darkTheme; objectName: "darkTheme"; dark: true }
    Theme { id: lightTheme; objectName: "lightTheme"; dark: false }
    SettingsCard {
        objectName: "card"
        width: 480
        theme: darkTheme
        title: "Text"
        SettingRow { objectName: "plain"; theme: darkTheme; title: "Font" }
        SettingRow {
            objectName: "described"; theme: darkTheme
            title: "Blur behind"; description: "Frosted glass under the captions"
            Switch {}
        }
    }
}
""")
    settle()
    card = root.findChild(QObject, "card")
    plain, described = root.findChild(QObject, "plain"), root.findChild(QObject, "described")
    dividers = [o for o in card.findChildren(QObject) if o.objectName() == "divider" and o.property("visible")]
    assert len(dividers) == 1
    assert described.property("height") > plain.property("height")
    dark, light = root.findChild(QObject, "darkTheme"), root.findChild(QObject, "lightTheme")
    assert dark.property("card") != light.property("card")
    assert dark.property("text") != light.property("text")
    assert warnings == []

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


def visual(item, name):
    """Find an item by objectName through visual children (Repeater delegates are not QObject children)."""
    for child in item.childItems():
        if child.objectName() == name:
            return child
        found = visual(child, name)
        if found is not None:
            return found
    return None


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


def store_and_context(tmp_path, **settings):
    from echoline.settings.model import Settings
    from echoline.settings.store import SettingsStore
    from echoline.ui.motion import Motion
    from echoline.ui.sample import SampleCaptions

    store = SettingsStore(Settings(**settings), tmp_path / "s.json")
    sample = SampleCaptions(step_ms=20)
    motion = Motion(False)
    return store, sample, {"settingsStore": store, "sampleCaptions": sample, "motion": motion, "_keep": motion}


def test_theme_presets_are_exposed(tmp_path):
    from echoline.settings.themes import PRESETS

    store, _, _ = store_and_context(tmp_path)
    assert [p["name"] for p in store.property("themePresets")] == list(PRESETS)


def test_gallery_marks_active_theme_and_custom(tmp_path):
    store, _, context = store_and_context(tmp_path, theme="Minimal")
    engine, root, warnings = build("""
import QtQuick
Item {
    width: 600; height: 200
    Theme { id: t }
    ThemeGallery { width: 600; theme: t; s: settingsStore.values }
}
""", context)
    settle()

    def card(name):
        return visual(root, f"theme {name}")

    assert card("Minimal").property("selected") and not card("Netflix").property("selected")
    assert not root.findChild(QObject, "customBadge").property("visible")
    store.setValue("font_size", 40)
    settle()
    assert not any(card(n).property("selected") for n in ("Classic CC", "Netflix", "Minimal", "High contrast"))
    assert root.findChild(QObject, "customBadge").property("visible")
    card("Netflix").clicked.emit()
    assert store.settings.theme == "Netflix"
    assert warnings == []


def test_preview_follows_style_settings(tmp_path):
    store, sample, context = store_and_context(tmp_path)
    engine, root, warnings = build("""
import QtQuick
Item {
    width: 600; height: 200
    Theme { id: t }
    PreviewPane { width: 600; theme: t; s: settingsStore.values; sample: sampleCaptions }
}
""", context)
    sample.start()
    settle(0.3)
    box = root.findChild(QObject, "previewCaption")
    assert abs(box.property("color").alphaF() - store.settings.background_opacity) < 0.01
    line = box.findChild(QObject, "previewLine")
    before = line.property("lineHeight")
    store.setValue("font_size", 40)
    settle()
    assert line.property("lineHeight") > before
    assert line.property("text") != ""
    sample.stop()
    assert warnings == []


def test_caption_backdrop_stays_video_dark_in_light_mode():
    # Seen in light-mode screenshots: Netflix-style shadowed white text washed
    # out on a pale backdrop. Captions sit over video, so the backdrop stays dark.
    engine, root, _ = build("""
import QtQuick
Item {
    Theme { objectName: "darkTheme"; dark: true }
    Theme { objectName: "lightTheme"; dark: false }
}
""")
    dark, light = root.findChild(QObject, "darkTheme"), root.findChild(QObject, "lightTheme")
    for token in ("backdropTop", "backdropBottom"):
        assert light.property(token) == dark.property(token)


def test_preview_grows_to_fit_big_captions(tmp_path):
    from PySide6.QtCore import QPointF

    store, sample, context = store_and_context(tmp_path, font_size=64)
    engine, root, _ = build("""
import QtQuick
Item {
    width: 520; height: 600
    Theme { id: t }
    PreviewPane { width: 520; theme: t; s: settingsStore.values; sample: sampleCaptions }
}
""", context)
    for _ in range(len(sample.SCRIPT)):
        sample._step()                                # whole sentence, wrapped over several rows
    settle(0.5)
    pane = root.findChild(QObject, "previewPane")
    box = root.findChild(QObject, "previewCaption")
    assert box.mapToItem(pane, QPointF(0, 0)).y() >= 0, "caption box spills above the preview"

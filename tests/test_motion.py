from PySide6.QtGui import QGuiApplication

app = QGuiApplication.instance()

from echoline.ui import motion


def test_reads_the_windows_animation_setting(monkeypatch):
    class User32:
        def __init__(self, value):
            self.value = value

        def SystemParametersInfoW(self, action, param, out, flags):
            assert action == 0x1042                      # SPI_GETCLIENTAREAANIMATION
            out._obj.value = self.value
            return 1

    monkeypatch.setattr(motion, "_user32", lambda: User32(False))
    assert motion.animations_enabled() is False
    monkeypatch.setattr(motion, "_user32", lambda: User32(True))
    assert motion.animations_enabled() is True


def test_unreadable_setting_means_animate(monkeypatch):
    def broken():
        raise OSError("no user32")

    monkeypatch.setattr(motion, "_user32", broken)
    assert motion.animations_enabled() is True


def test_scale_is_zero_when_disabled():
    assert motion.Motion(False).property("scale") == 0.0
    assert motion.Motion(True).property("scale") == 1.0


def test_overlay_exposes_motion_to_qml(tmp_path):
    from PySide6.QtQml import QQmlApplicationEngine

    from echoline.captions.model import CaptionModel
    from echoline.settings.model import Settings
    from echoline.settings.store import SettingsStore
    from echoline.ui.overlay import OverlayStatus, load_overlay

    engine = QQmlApplicationEngine()
    keep = CaptionModel(), OverlayStatus(), SettingsStore(Settings(), tmp_path / "s.json")
    window = load_overlay(engine, *keep, motion=motion.Motion(False))
    try:
        assert engine.rootContext().contextProperty("motion").property("scale") == 0.0
    finally:
        window.close()
        engine.deleteLater()

import time

from PySide6.QtCore import QCoreApplication

from echoline.settings.model import Settings, load_settings
from echoline.settings.store import SettingsStore


def wait(ms):
    deadline = time.monotonic() + ms / 1000
    while time.monotonic() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.005)


def test_values_expose_settings_to_qml(tmp_path):
    store = SettingsStore(Settings(), tmp_path / "s.json")

    assert store.property("values")["font_size"] == 26


def test_set_value_validates_and_notifies(tmp_path):
    store = SettingsStore(Settings(), tmp_path / "s.json")
    changes = []
    store.valuesChanged.connect(lambda: changes.append(store.settings.font_size))

    store.setValue("font_size", 999)
    store.setValue("font_size", 64)          # unchanged -> no signal
    store.setValue("no_such_key", 1)

    assert changes == [64]


def test_editing_a_themed_value_switches_theme_to_custom(tmp_path):
    store = SettingsStore(Settings(), tmp_path / "s.json")

    store.setValue("text_color", "#00ff00")

    assert store.settings.theme == "Custom"


def test_apply_theme_updates_values(tmp_path):
    store = SettingsStore(Settings(), tmp_path / "s.json")

    store.applyTheme("Classic CC")

    assert (store.settings.theme, store.property("values")["font_family"]) == ("Classic CC", "Arial")


def test_rapid_changes_are_saved_once(tmp_path, monkeypatch):
    path = tmp_path / "s.json"
    store = SettingsStore(Settings(), path, save_delay_ms=50)
    writes = []
    monkeypatch.setattr("echoline.settings.store.save_settings", lambda s, p: writes.append(s.font_size))

    for size in range(20, 40):
        store.setValue("font_size", size)
    wait(200)

    assert writes == [39]


def test_save_now_flushes_a_pending_save(tmp_path):
    path = tmp_path / "s.json"
    store = SettingsStore(Settings(), path, save_delay_ms=10_000)

    store.setValue("line_count", 3)
    assert store.pending_save
    store.save_now()

    assert load_settings(path)[0].line_count == 3
    assert not store.pending_save

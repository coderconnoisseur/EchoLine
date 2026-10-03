import json

from echoline.settings.model import Settings, load_settings, save_settings, validate


def test_defaults_match_the_current_look():
    settings = Settings()

    assert (settings.font_family, settings.font_size, settings.background_opacity) == ("Segoe UI", 26, 0.72)
    assert settings.theme == "Minimal" and settings.caption_mode == "rolling"


def test_round_trip(tmp_path):
    path = tmp_path / "settings.json"
    save_settings(Settings(font_size=40, position=[10, 20], caption_mode="subtitle"), path)

    loaded, was_reset = load_settings(path)

    assert (loaded.font_size, loaded.position, loaded.caption_mode) == (40, [10, 20], "subtitle")
    assert not was_reset


def test_missing_file_gives_defaults(tmp_path):
    assert load_settings(tmp_path / "nope.json") == (Settings(), False)


def test_invalid_fields_fall_back_individually():
    settings = validate({
        "font_size": 500, "line_count": "two", "text_color": "red", "outline": "glow",
        "background_opacity": -1, "position": "left", "caption_mode": "subtitle", "bogus": 1,
    })

    assert settings.font_size == 64                     # clamped into range
    assert settings.line_count == 2                     # wrong type -> default
    assert settings.text_color == "#ffffff"
    assert settings.outline == "outline"
    assert settings.background_opacity == 0.0
    assert settings.position is None
    assert settings.caption_mode == "subtitle"          # valid values are kept


def test_unreadable_file_is_backed_up_and_defaults_load(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{ not json")

    settings, was_reset = load_settings(path)

    assert settings == Settings() and was_reset
    assert (tmp_path / "settings.json.bak").read_text() == "{ not json"
    assert not path.exists()


def test_save_writes_plain_json(tmp_path):
    path = tmp_path / "nested" / "settings.json"

    save_settings(Settings(theme="Netflix"), path)

    assert json.loads(path.read_text())["theme"] == "Netflix"


def test_non_finite_numbers_fall_back_to_defaults(tmp_path):
    # Python's json accepts NaN and turns 1e400 into inf; both crashed startup.
    path = tmp_path / "settings.json"
    path.write_text('{"font_size": NaN, "background_opacity": NaN, "position": [1e400, 0], "line_count": 3}')

    settings, was_reset = load_settings(path)

    assert (settings.font_size, settings.background_opacity, settings.position) == (26, 0.72, None)
    assert settings.line_count == 3 and not was_reset


def test_unsavable_backup_does_not_stop_startup(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    path.write_text("{ not json")

    def locked(*args):
        raise PermissionError("locked by another program")

    monkeypatch.setattr("echoline.settings.model.os.replace", locked)

    assert load_settings(path) == (Settings(), True)


def test_control_settings_have_defaults():
    s = Settings()

    assert (s.audio_source, s.auto_hide, s.click_through, s.start_with_windows) == ("system", False, False, False)
    assert (s.hotkey_show_hide, s.hotkey_pause, s.hotkey_click_through) == ("Ctrl+Alt+C", "Ctrl+Alt+P", "Ctrl+Alt+T")


def test_control_settings_are_validated():
    s = validate({"audio_source": "line-in", "auto_hide": "yes", "hotkey_pause": "Ctrl+Alt+<script>",
                  "hotkey_show_hide": "", "hotkey_click_through": "Ctrl+Shift+F9"})

    assert s.audio_source == "system"
    assert s.auto_hide is False
    assert s.hotkey_pause == "Ctrl+Alt+P"
    assert s.hotkey_show_hide == ""                      # disabled is allowed
    assert s.hotkey_click_through == "Ctrl+Shift+F9"

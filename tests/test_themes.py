from dataclasses import replace

from echoline.settings.model import Settings
from echoline.settings.themes import PRESETS, THEMED_KEYS, apply_theme, theme_name_for


def test_every_preset_defines_every_themed_value():
    assert set(PRESETS) == {"Classic CC", "Netflix", "Minimal", "High contrast"}
    for preset in PRESETS.values():
        assert set(preset) == set(THEMED_KEYS)


def test_default_settings_are_the_minimal_theme():
    assert theme_name_for(Settings()) == "Minimal"


def test_applying_a_theme_overwrites_themed_values_only():
    custom = Settings(font_size=50, line_count=3, position=[5, 5])

    themed = apply_theme(custom, "High contrast")

    assert (themed.theme, themed.text_color, themed.font_size) == ("High contrast", "#ffff00", 32)
    assert (themed.line_count, themed.position) == (3, [5, 5])


def test_editing_a_themed_value_makes_it_custom():
    assert theme_name_for(replace(apply_theme(Settings(), "Netflix"), font_size=40)) == "Custom"


def test_unknown_theme_is_ignored():
    settings = Settings()

    assert apply_theme(settings, "Neon") is settings

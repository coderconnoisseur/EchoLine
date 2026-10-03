from dataclasses import replace

THEMED_KEYS = ("font_family", "font_size", "font_weight", "text_color", "outline", "outline_color",
               "background_color", "background_opacity", "corner_radius")


def _preset(font_family, font_size, font_weight, text_color, outline, background_opacity, corner_radius):
    return {"font_family": font_family, "font_size": font_size, "font_weight": font_weight,
            "text_color": text_color, "outline": outline, "outline_color": "#000000",
            "background_color": "#000000", "background_opacity": background_opacity,
            "corner_radius": corner_radius}


PRESETS = {
    "Classic CC": _preset("Arial", 26, 500, "#ffffff", "none", 0.85, 0),
    "Netflix": _preset("Segoe UI", 28, 600, "#ffffff", "shadow", 0.0, 0),
    "Minimal": _preset("Segoe UI", 26, 500, "#ffffff", "outline", 0.72, 14),
    "High contrast": _preset("Verdana", 32, 700, "#ffff00", "outline", 1.0, 4),
}


def apply_theme(settings, name):
    if name not in PRESETS:
        return settings
    return replace(settings, theme=name, **PRESETS[name])


def theme_name_for(settings):
    for name, preset in PRESETS.items():
        if all(getattr(settings, key) == value for key, value in preset.items()):
            return name
    return "Custom"

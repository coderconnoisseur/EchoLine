import json
import math
import os
import re
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Optional

COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


@dataclass
class Settings:
    theme: str = "Minimal"
    font_family: str = "Segoe UI"
    font_size: int = 26
    font_weight: int = 500
    text_color: str = "#ffffff"
    outline: str = "outline"
    outline_color: str = "#000000"
    line_count: int = 2
    background_color: str = "#000000"
    background_opacity: float = 0.72
    corner_radius: int = 14
    width_percent: int = 35
    blur_behind: bool = False
    position: Optional[list] = None
    always_on_top: bool = True
    caption_mode: str = "rolling"
    audio_source: str = "system"
    auto_hide: bool = False
    click_through: bool = False
    start_with_windows: bool = False
    hotkey_show_hide: str = "Ctrl+Alt+C"
    hotkey_pause: str = "Ctrl+Alt+P"
    hotkey_click_through: str = "Ctrl+Alt+T"


RANGES = {"font_size": (14, 64), "line_count": (1, 3), "background_opacity": (0.0, 1.0),
          "corner_radius": (0, 32), "width_percent": (20, 90)}
CHOICES = {"font_weight": (400, 500, 600, 700), "outline": ("outline", "shadow", "none"),
           "caption_mode": ("rolling", "subtitle"), "audio_source": ("system", "microphone")}
COLORS = ("text_color", "outline_color", "background_color")


HOTKEY = re.compile(r"^((Ctrl|Alt|Shift|Win)\+){1,3}([A-Z0-9]|F([1-9]|1[0-2]))$")
HOTKEYS = ("hotkey_show_hide", "hotkey_pause", "hotkey_click_through")


def _valid(name, value, default):
    if name in HOTKEYS:
        return value if isinstance(value, str) and (value == "" or HOTKEY.match(value)) else default
    if name in RANGES:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            return default
        low, high = RANGES[name]
        value = min(max(value, low), high)
        return type(default)(value) if isinstance(default, int) else float(value)
    if name in CHOICES:
        return value if value in CHOICES[name] else default
    if name in COLORS:
        return value.lower() if isinstance(value, str) and COLOR.match(value) else default
    if name == "position":
        ok = isinstance(value, list) and len(value) == 2 and all(
            isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in value)
        return [int(v) for v in value] if ok else None
    if isinstance(default, bool):
        return value if isinstance(value, bool) else default
    if isinstance(default, str):
        return value if isinstance(value, str) and value.strip() else default
    return default


def validate(data: dict) -> Settings:
    defaults = Settings()
    values = {}
    for field in fields(Settings):
        default = getattr(defaults, field.name)
        values[field.name] = _valid(field.name, data[field.name], default) if field.name in data else default
    return Settings(**values)


def default_settings_path() -> Path:
    return Path(os.environ.get("APPDATA", Path.home())) / "EchoLine" / "settings.json"


def load_settings(path: Path):
    if not path.exists():
        return Settings(), False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("settings file is not a JSON object")
    except (OSError, ValueError):
        try:
            os.replace(path, path.with_name(path.name + ".bak"))
        except OSError:
            pass        # keep going with defaults even if the backup cannot be made
        return Settings(), True
    return validate(data), False


def save_settings(settings: Settings, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
    os.replace(temp, path)

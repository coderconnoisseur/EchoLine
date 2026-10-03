# M2: Caption Customization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Users can restyle and reposition the captions (text, background, position, theme presets) and switch between rolling and subtitle modes, with settings that persist and preview live.

**Architecture:** A pure-Python `Settings` dataclass (validated, JSON-persisted) wrapped by a `SettingsStore` QObject that exposes one `values` map to QML, applies theme presets, and saves with a debounce. The overlay binds every visual property to `settingsStore.values`. A Fluent-styled QML settings window edits the store; it opens from a right-click menu on the overlay or `Ctrl+,`.

**Tech Stack:** Python 3.11, PySide6 6.11.2 (QtQuick, QtQuick.Controls with the FluentWinUI3 style), pytest. Windows-only acrylic blur via `ctypes`.

**Spec:** `docs/superpowers/specs/2026-10-03-echoline-v1-design.md` (Customization, Caption experience, Supporting services → Settings/Themes, Error handling → corrupt settings, Milestone M2).

**Decisions made with the user for this plan (2026-10-03):** upgrade PySide6 to 6.11.2 and use the FluentWinUI3 style; settings open from a right-click menu and `Ctrl+,` until M3 adds the tray and hover bar; the font list shows curated caption fonts first, then all system fonts; editing any themed value switches the theme label to "Custom", and choosing a preset overwrites those values.

## Global Constraints

- Windows 10+; Python >= 3.10; `.venv/Scripts/python` for everything.
- `PySide6==6.11.2`. `moonshine.dll` must still load before Qt (`preload_native_library()` first in `echoline/__main__.py` and `tests/conftest.py`).
- Settings file: `%APPDATA%\EchoLine\settings.json`. Tests never touch the real file (use `tmp_path`).
- Corrupt settings file: back it up as `settings.json.bak`, load defaults, notify once (spec).
- Click-through, auto-hide, tray, hover bar and hotkeys are **M3**, not here. Audio/engine/hotkey settings pages are **M3/M4**.
- No new third-party dependencies beyond the PySide6 bump.
- Tests need no audio device or model; QML tests run on the offscreen platform and must report no QML warnings.
- Commits: imperative summary plus a short "why" body; never mention AI tools or co-authors; one logical change per commit; full suite green before each commit.

## Review Focus

1. **Corrupt or hand-edited settings file** (bad JSON, wrong types, out-of-range numbers): the app must start with sane values for every bad field, keep the good ones, and back up a file it cannot parse — pinned in Task 2 (`test_invalid_fields_fall_back_individually`, `test_unreadable_file_is_backed_up_and_defaults_load`).
2. **Saved position no longer on any screen** (monitor unplugged, resolution lowered): the overlay must reappear fully on the primary screen — pinned in Task 8 (`test_offscreen_position_is_pulled_back_on_screen`).
3. **Large font plus 3 lines on a small screen**: the overlay must not grow taller than 40% of the screen — pinned in Task 6 (`test_overlay_height_is_capped_on_small_screens`).
4. **Dragging a slider quickly**: the file must not be rewritten on every tick, and the last value must still be saved on quit — pinned in Task 4 (`test_rapid_changes_are_saved_once`) and Task 10 (`test_shutdown_saves_pending_settings`).
5. **Switching rolling/subtitle mode mid-utterance**: the current text must carry over, with no blank or duplicated caption — pinned in Task 7 (`test_switching_mode_keeps_current_text`).

---

## File Structure

```
echoline/
  settings/
    __init__.py
    model.py          # Settings dataclass, validation, load/save (Task 2)
    themes.py         # theme presets, apply/match (Task 3)
    store.py          # SettingsStore(QObject) for QML, debounced save (Task 4)
  ui/
    style.py          # use_fluent_style() (Task 1)
    placement.py      # snap_position(), clamp_to_screen() (Task 8)
    blur.py           # set_acrylic(hwnd, enabled) via user32 (Task 9)
    fonts.py          # caption_fonts() curated + system list (Task 10)
    overlay.py        # + settings/controller context properties (Tasks 6, 10)
    qml/
      Overlay.qml     # bound to settings; right-click menu; resize grip (Tasks 6, 7, 10)
      SubtitleView.qml  # subtitle mode (Task 7)
      Settings.qml    # Fluent settings window (Task 10)
  captions/model.py   # + latestId / latestText properties (Task 5)
  app.py              # wires store, controller, settings window (Task 10)
  __main__.py         # Fluent style, settings path (Tasks 1, 10)
tests/
  test_style.py, test_settings_model.py, test_themes.py, test_settings_store.py,
  test_caption_model.py (extended), test_overlay_qml.py (extended), test_placement.py,
  test_blur.py, test_fonts.py, test_settings_window.py, test_echoline_app.py (extended)
```

---

### Task 1: Upgrade PySide6 and use the Fluent style

**Files:**
- Create: `echoline/ui/style.py`
- Modify: `requirements.txt`, `echoline/__main__.py`
- Test: `tests/test_style.py`

**Interfaces:**
- Produces: `use_fluent_style() -> str` — sets the QtQuick.Controls style to `FluentWinUI3` and returns the active style name. Must run before any QML engine loads controls.

- [ ] **Step 1: Pin the new version**

In `requirements.txt` replace `PySide6==6.6.0` with `PySide6==6.11.2`, then run `.venv/Scripts/python -m pip install -r requirements.txt`.

- [ ] **Step 2: Write the failing test**

`tests/test_style.py`:
```python
from echoline.ui.style import use_fluent_style


def test_fluent_style_is_selected():
    assert use_fluent_style() == "FluentWinUI3"
```

- [ ] **Step 3: Run it to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_style.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'echoline.ui.style'`.

- [ ] **Step 4: Implement**

`echoline/ui/style.py`:
```python
from PySide6.QtQuickControls2 import QQuickStyle


def use_fluent_style():
    """Native-looking Windows 11 controls for the settings window."""
    QQuickStyle.setStyle("FluentWinUI3")
    return QQuickStyle.name()
```

In `echoline/__main__.py`, directly after `qt_app.setApplicationName("EchoLine")` add:
```python
    from .ui.style import use_fluent_style
    use_fluent_style()
```

- [ ] **Step 5: Verify and commit**

Run: `.venv/Scripts/python -m pytest -q` and `.venv/Scripts/python -m pytest -m model -q`
Expected: all pass.

```bash
git add requirements.txt echoline/ui/style.py echoline/__main__.py tests/test_style.py
git commit -m "Upgrade PySide6 to 6.11 and use the Fluent controls style" -m "6.8+ ships Qt's FluentWinUI3 style, which gives the settings window a native Windows 11 look."
```

---

### Task 2: Settings model with validation and persistence

**Files:**
- Create: `echoline/settings/__init__.py` (empty), `echoline/settings/model.py`
- Test: `tests/test_settings_model.py`

**Interfaces:**
- Produces:
  - `Settings` dataclass with these fields and defaults:
    `theme="Minimal"`, `font_family="Segoe UI"`, `font_size=26`, `font_weight=500`, `text_color="#ffffff"`, `outline="outline"`, `outline_color="#000000"`, `line_count=2`, `background_color="#000000"`, `background_opacity=0.72`, `corner_radius=14`, `width_percent=35`, `blur_behind=False`, `position=None` (`[x, y]` or `None`), `always_on_top=True`, `caption_mode="rolling"`.
  - `LIMITS`: `font_size` 14–64, `font_weight` one of 400/500/600/700, `line_count` 1–3, `background_opacity` 0.0–1.0, `corner_radius` 0–32, `width_percent` 20–90; `outline` one of `"outline"`, `"shadow"`, `"none"`; `caption_mode` one of `"rolling"`, `"subtitle"`; colors match `#rrggbb`.
  - `validate(data: dict) -> Settings` — every invalid or missing field falls back to its default on its own; unknown keys are ignored.
  - `load_settings(path: Path) -> tuple[Settings, bool]` — returns `(settings, was_reset)`; a missing file gives defaults and `False`; an unreadable file is renamed to `<name>.bak` and gives defaults and `True`.
  - `save_settings(settings: Settings, path: Path) -> None` — creates the folder, writes JSON atomically (temp file + `os.replace`).
  - `default_settings_path() -> Path` — `%APPDATA%\EchoLine\settings.json`.

- [ ] **Step 1: Write the failing tests**

`tests/test_settings_model.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_settings_model.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'echoline.settings'`.

- [ ] **Step 3: Implement**

`echoline/settings/model.py`:
```python
import json
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


RANGES = {"font_size": (14, 64), "line_count": (1, 3), "background_opacity": (0.0, 1.0),
          "corner_radius": (0, 32), "width_percent": (20, 90)}
CHOICES = {"font_weight": (400, 500, 600, 700), "outline": ("outline", "shadow", "none"),
           "caption_mode": ("rolling", "subtitle")}
COLORS = ("text_color", "outline_color", "background_color")


def _valid(name, value, default):
    if name in RANGES:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
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
            isinstance(v, (int, float)) and not isinstance(v, bool) for v in value)
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
        os.replace(path, path.with_name(path.name + ".bak"))
        return Settings(), True
    return validate(data), False


def save_settings(settings: Settings, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
    os.replace(temp, path)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_settings_model.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add echoline/settings tests/test_settings_model.py
git commit -m "Add validated, persisted caption settings" -m "Each invalid field falls back to its default on its own, and an unreadable file is backed up before defaults load, so a hand-edited or damaged settings file never stops the app from starting."
```

---

### Task 3: Theme presets

**Files:**
- Create: `echoline/settings/themes.py`
- Test: `tests/test_themes.py`

**Interfaces:**
- Consumes: `Settings`, `validate` (Task 2).
- Produces:
  - `THEMED_KEYS = ("font_family", "font_size", "font_weight", "text_color", "outline", "outline_color", "background_color", "background_opacity", "corner_radius")`
  - `PRESETS: dict[str, dict]` with exactly `"Classic CC"`, `"Netflix"`, `"Minimal"`, `"High contrast"`, each defining every key in `THEMED_KEYS`.
  - `apply_theme(settings: Settings, name: str) -> Settings` — returns a copy with the preset's values and `theme=name`; unknown names return `settings` unchanged.
  - `theme_name_for(settings: Settings) -> str` — the preset whose values all match, else `"Custom"`.

Preset values:

| Key | Classic CC | Netflix | Minimal | High contrast |
|---|---|---|---|---|
| font_family | Arial | Segoe UI | Segoe UI | Verdana |
| font_size | 26 | 28 | 26 | 32 |
| font_weight | 500 | 600 | 500 | 700 |
| text_color | #ffffff | #ffffff | #ffffff | #ffff00 |
| outline | none | shadow | outline | outline |
| outline_color | #000000 | #000000 | #000000 | #000000 |
| background_color | #000000 | #000000 | #000000 | #000000 |
| background_opacity | 0.85 | 0.0 | 0.72 | 1.0 |
| corner_radius | 0 | 0 | 14 | 4 |

- [ ] **Step 1: Write the failing tests**

`tests/test_themes.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_themes.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'echoline.settings.themes'`.

- [ ] **Step 3: Implement**

`echoline/settings/themes.py`:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_themes.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add echoline/settings/themes.py tests/test_themes.py
git commit -m "Add Classic CC, Netflix, Minimal and High contrast caption themes"
```

---

### Task 4: Settings store for QML

**Files:**
- Create: `echoline/settings/store.py`
- Test: `tests/test_settings_store.py`

**Interfaces:**
- Consumes: `Settings`, `validate`, `save_settings` (Task 2); `apply_theme`, `theme_name_for`, `PRESETS` (Task 3).
- Produces: `SettingsStore(settings: Settings, path: Path, save_delay_ms: int = 400, parent=None)` (QObject) with:
  - `values` — `Property("QVariantMap", notify=valuesChanged)`: the settings as a dict (QML reads `settingsStore.values.font_size`).
  - `themeNames` — `Property(list, constant=True)`: `["Classic CC", "Netflix", "Minimal", "High contrast"]`.
  - `@Slot(str, "QVariant") setValue(key, value)` — validates the single field; unknown keys are ignored; after any themed change sets `theme` to `theme_name_for(...)`; emits `valuesChanged` only if something changed; schedules a save.
  - `@Slot(str) applyTheme(name)`.
  - `settings` (Python attribute, current `Settings`), `save_now()` (writes immediately if a save is pending), `pending_save` (bool).

- [ ] **Step 1: Write the failing tests**

`tests/test_settings_store.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_settings_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'echoline.settings.store'`.

- [ ] **Step 3: Implement**

`echoline/settings/store.py`:
```python
from dataclasses import asdict, replace

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from .model import save_settings, validate
from .themes import PRESETS, THEMED_KEYS, apply_theme, theme_name_for


class SettingsStore(QObject):
    """Live settings shared by the overlay and the settings window; saves after edits settle."""

    valuesChanged = Signal()

    def __init__(self, settings, path, save_delay_ms=400, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.path = path
        self.pending_save = False
        self._timer = QTimer(self, singleShot=True, interval=save_delay_ms)
        self._timer.timeout.connect(self.save_now)

    def _get_values(self):
        return asdict(self.settings)

    values = Property("QVariantMap", _get_values, notify=valuesChanged)

    def _get_theme_names(self):
        return list(PRESETS)

    themeNames = Property(list, _get_theme_names, constant=True)

    def _update(self, settings):
        if settings == self.settings:
            return
        self.settings = settings
        self.valuesChanged.emit()
        self.pending_save = True
        self._timer.start()

    @Slot(str, "QVariant")
    def setValue(self, key, value):
        current = asdict(self.settings)
        if key not in current:
            return
        updated = validate({**current, key: value})
        if key in THEMED_KEYS:
            updated = replace(updated, theme=theme_name_for(updated))
        self._update(updated)

    @Slot(str)
    def applyTheme(self, name):
        self._update(apply_theme(self.settings, name))

    @Slot()
    def save_now(self):
        if self.pending_save:
            self._timer.stop()
            save_settings(self.settings, self.path)
            self.pending_save = False
```

Note: `validate` receives values from QML as Python types via `QVariant`; QML numbers arrive as `float`, which `_valid` converts back to `int` for integer fields.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_settings_store.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add echoline/settings/store.py tests/test_settings_store.py
git commit -m "Add settings store shared by the overlay and settings window" -m "Exposes settings to QML as one map, validates each edit, switches the theme label to Custom when a themed value changes, and saves once edits settle instead of on every slider tick."
```

---

### Task 5: Latest-utterance properties on the caption model

**Files:**
- Modify: `echoline/captions/model.py`
- Test: `tests/test_caption_model.py`

**Interfaces:**
- Produces: on `CaptionModel`, `latestText` (`Property(str, notify=latestChanged)`) and `latestId` (`Property(int, notify=latestChanged)`) — the text and id of the newest row; `""` and `-1` when empty. `latestChanged` is emitted whenever either changes.

- [ ] **Step 1: Write the failing test** (append to `tests/test_caption_model.py`)

```python
def test_latest_utterance_is_exposed_for_subtitle_mode():
    model = CaptionModel()
    seen = []
    model.latestChanged.connect(lambda: seen.append((model.property("latestId"), model.property("latestText"))))

    model.apply([Final(0, "one.")])
    model.apply([Partial(1, "tw")])
    model.apply([Partial(1, "two")])

    assert seen == [(0, "one."), (1, "tw"), (1, "two")]


def test_latest_is_empty_before_any_caption():
    model = CaptionModel()

    assert (model.property("latestId"), model.property("latestText")) == (-1, "")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_caption_model.py -v`
Expected: 2 FAIL (`AttributeError` on `latestChanged`).

- [ ] **Step 3: Implement**

In `echoline/captions/model.py`: import `Property` and `Signal` from `PySide6.QtCore`; add to the class:
```python
    latestChanged = Signal()

    def _latest(self):
        return self._rows[-1] if self._rows else (-1, "", False)

    def _get_latest_text(self):
        return self._latest()[1]

    def _get_latest_id(self):
        return self._latest()[0]

    latestText = Property(str, _get_latest_text, notify=latestChanged)
    latestId = Property(int, _get_latest_id, notify=latestChanged)
```
and change `apply` to:
```python
    def apply(self, events):
        before = tuple(self._latest()[:2])
        for event in events:
            self._apply_one(event.utterance_id, event.text, isinstance(event, Final))
        if tuple(self._latest()[:2]) != before:
            self.latestChanged.emit()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_caption_model.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add echoline/captions/model.py tests/test_caption_model.py
git commit -m "Expose the newest utterance for subtitle mode"
```

---

### Task 6: Overlay styled from settings

**Files:**
- Modify: `echoline/ui/overlay.py`, `echoline/ui/qml/Overlay.qml`
- Test: `tests/test_overlay_qml.py`

**Interfaces:**
- Consumes: `SettingsStore` (Task 4).
- Produces: `load_overlay(engine, captions, status, settings_store, controller=None)` — the `max_lines` parameter is removed (line count now comes from settings). Context properties: `captions`, `status`, `settingsStore`, `controller` (may be `None`). QML object names added: `"panel"` (background Rectangle). The overlay's height is capped at 40% of the screen height.

QML behavior:
- `panel.color` = `background_color` with `background_opacity` alpha; `panel.radius` = `corner_radius`.
- Caption text: `font.family`, `font.pixelSize`, `font.weight`, `color` from settings; `style` = `Text.Outline` / `Text.Raised` / `Text.Normal` for `outline` / `shadow` / `none`; `styleColor` = `outline_color`.
- ListView height = line height × `line_count`, where line height comes from a `FontMetrics` bound to the same font.
- Window width = `Screen.width * width_percent / 100`; window `flags` include `Qt.WindowStaysOnTopHint` only when `always_on_top`.
- Window height = `Math.min(panel.implicitHeight, Screen.height * 0.4)`.

- [ ] **Step 1: Update the test fixture and write failing tests**

In `tests/test_overlay_qml.py`, change the fixture to build a store and pass it:
```python
from echoline.settings.model import Settings
from echoline.settings.store import SettingsStore


@pytest.fixture
def overlay(tmp_path):
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))
    captions, status = CaptionModel(), OverlayStatus()
    store = SettingsStore(Settings(), tmp_path / "settings.json")
    window = load_overlay(engine, captions, status, store)
    window.store = store
    yield window, captions, status, warnings
    window.close()
    engine.deleteLater()
```
Append:
```python
def test_overlay_follows_style_settings(overlay):
    window, captions, _, warnings = overlay
    captions.apply([Final(0, "hello")])
    settle()
    view = window.findChild(QObject, "captionList")
    one_line_view = view.property("height")

    window.store.setValue("font_size", 52)
    window.store.setValue("corner_radius", 0)
    settle()

    assert view.property("height") > one_line_view * 1.5
    assert window.findChild(QObject, "panel").property("radius") == 0
    assert warnings == []


def test_line_count_sets_view_height(overlay):
    window, _, _, _ = overlay
    view = window.findChild(QObject, "captionList")
    two_lines = view.property("height")

    window.store.setValue("line_count", 1)
    settle()

    assert abs(view.property("height") - two_lines / 2) < 1


def test_width_follows_width_percent(overlay):
    window, _, _, _ = overlay

    window.store.setValue("width_percent", 50)
    settle()

    assert abs(window.width() - window.screen().geometry().width() * 0.5) <= 1


def test_overlay_height_is_capped_on_small_screens(overlay):
    window, _, _, _ = overlay

    window.store.setValue("font_size", 64)
    window.store.setValue("line_count", 3)
    settle()

    assert window.height() <= window.screen().geometry().height() * 0.4 + 1
```
Also replace `load_overlay(engine, captions, status, max_lines=2)` everywhere in tests (none remain after the fixture change).

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_overlay_qml.py -v`
Expected: FAIL (`load_overlay()` takes no `settings_store`, or style assertions fail).

- [ ] **Step 3: Implement**

`echoline/ui/overlay.py` — replace `load_overlay`:
```python
def load_overlay(engine, captions, status, settings_store, controller=None):
    context = engine.rootContext()
    context.setContextProperty("captions", captions)
    context.setContextProperty("status", status)
    context.setContextProperty("settingsStore", settings_store)
    context.setContextProperty("controller", controller)
    errors = []
    engine.warnings.connect(lambda items: errors.extend(w.toString() for w in items))
    engine.load(QUrl.fromLocalFile(str(QML_DIR / "Overlay.qml")))
    if not engine.rootObjects():
        raise RuntimeError("Could not load Overlay.qml:\n" + "\n".join(errors))
    # PySide types the QML root as a plain QWindow; rewrap it to reach QQuickWindow API.
    root = engine.rootObjects()[0]
    return shiboken6.wrapInstance(shiboken6.getCppPointer(root)[0], QQuickWindow)
```

`echoline/ui/qml/Overlay.qml` — full replacement:
```qml
import QtQuick
import QtQuick.Window

Window {
    id: overlay
    objectName: "overlay"
    readonly property var s: settingsStore.values
    flags: Qt.FramelessWindowHint | Qt.Tool | (s.always_on_top ? Qt.WindowStaysOnTopHint : 0)
    color: "transparent"
    visible: true
    width: Screen.width * s.width_percent / 100
    height: Math.min(panel.implicitHeight, Screen.height * 0.4)
    x: (Screen.width - width) / 2
    y: Screen.height * 0.85 - height / 2

    readonly property real lineHeight: metrics.height * 1.15

    FontMetrics {
        id: metrics
        font.family: overlay.s.font_family
        font.pixelSize: overlay.s.font_size
        font.weight: overlay.s.font_weight
    }

    Shortcut { sequences: ["Ctrl+Q", "Escape"]; onActivated: Qt.quit() }

    Rectangle {
        id: panel
        objectName: "panel"
        anchors.fill: parent
        implicitHeight: content.implicitHeight + 24
        radius: overlay.s.corner_radius
        color: Qt.alpha(overlay.s.background_color, overlay.s.background_opacity)

        DragHandler { target: null; onActiveChanged: if (active) overlay.startSystemMove() }

        Column {
            id: content
            anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 18 }
            spacing: 4

            Rectangle {
                id: statusPill
                objectName: "statusPill"
                visible: status.state !== "listening"
                radius: height / 2
                color: status.state === "no-device" || status.state === "model-error" ? "#b3261e" : "#5a5a5a"
                width: statusText.implicitWidth + 20
                height: statusText.implicitHeight + 6
                anchors.horizontalCenter: parent.horizontalCenter
                Text {
                    id: statusText
                    anchors.centerIn: parent
                    color: "white"
                    font.pixelSize: 13
                    text: ({ "loading": "Loading speech model…", "no-device": "No audio device",
                             "model-error": "Speech model unavailable — check your connection and restart",
                             "lagging": "Catching up…" })[status.state] || status.state
                }
            }

            ListView {
                id: captionList
                objectName: "captionList"
                width: parent.width
                height: overlay.lineHeight * overlay.s.line_count
                clip: true
                interactive: false
                model: captions
                spacing: 0

                onContentHeightChanged: scrollToEnd.restart()
                onCountChanged: scrollToEnd.restart()
                onHeightChanged: scrollToEnd.restart()
                Timer { id: scrollToEnd; interval: 0; onTriggered: captionList.positionViewAtEnd() }
                Behavior on contentY { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }

                delegate: CaptionText {
                    required property var model
                    width: captionList.width
                    text: model.text
                    opacity: model.final ? 1.0 : 0.85
                    Behavior on opacity { NumberAnimation { duration: 120 } }
                }

                add: Transition {
                    NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 160 }
                    NumberAnimation { property: "y"; from: captionList.height; duration: 180; easing.type: Easing.OutCubic }
                }
                remove: Transition { NumberAnimation { property: "opacity"; to: 0; duration: 160 } }
                displaced: Transition { NumberAnimation { property: "y"; duration: 180; easing.type: Easing.OutCubic } }
            }

            Text {
                visible: status.showLatency
                anchors.horizontalCenter: parent.horizontalCenter
                color: "#bbbbbb"
                font.pixelSize: 11
                text: status.latency
            }
        }
    }

    component CaptionText: Text {
        wrapMode: Text.Wrap
        horizontalAlignment: Text.AlignHCenter
        color: overlay.s.text_color
        font.family: overlay.s.font_family
        font.pixelSize: overlay.s.font_size
        font.weight: overlay.s.font_weight
        lineHeight: 1.15
        style: ({ "outline": Text.Outline, "shadow": Text.Raised, "none": Text.Normal })[overlay.s.outline]
        styleColor: overlay.s.outline_color
    }
}
```

In `echoline/app.py`, `EchoLineApp.__init__` gains a `settings_store` parameter (`EchoLineApp(source, engine_factory, settings_store, show_latency=False)`) and calls `load_overlay(self.qml, self.captions, self.status, settings_store)`. Update `tests/test_echoline_app.py` to pass `SettingsStore(Settings(), tmp_path / "settings.json")` (add `tmp_path` to the `running` fixture and to `test_failed_model_load_is_reported`), and `echoline/__main__.py` to build the store:
```python
    from .settings.model import default_settings_path, load_settings
    from .settings.store import SettingsStore
    settings, _ = load_settings(default_settings_path())
    store = SettingsStore(settings, default_settings_path())
```
and pass `store` to `EchoLineApp`. (Task 10 adds the reset notice and save-on-quit.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_overlay_qml.py tests/test_echoline_app.py -v`
Expected: all passed, no QML warnings.

- [ ] **Step 5: Commit**

```bash
git add echoline/ui/overlay.py echoline/ui/qml/Overlay.qml echoline/app.py echoline/__main__.py tests/test_overlay_qml.py tests/test_echoline_app.py
git commit -m "Style the overlay from settings" -m "Font, size, weight, colors, outline or shadow, background opacity, corner radius, width, line count and always-on-top now come from the settings store and update live. The overlay never grows taller than 40% of the screen."
```

---

### Task 7: Subtitle mode

**Files:**
- Create: `echoline/ui/qml/SubtitleView.qml`
- Modify: `echoline/ui/qml/Overlay.qml`
- Test: `tests/test_overlay_qml.py`

**Interfaces:**
- Consumes: `CaptionModel.latestText` / `latestId` (Task 5); settings `caption_mode` (Task 2).
- Produces: QML object `"subtitleView"`, visible only when `caption_mode == "subtitle"`; `"captionList"` visible only in `"rolling"`. Subtitle view shows the newest utterance as one centered block, at most `line_count` lines, keeping the end of a long utterance visible; when `latestId` changes it cross-fades from the previous block (150 ms out, 150 ms in).

- [ ] **Step 1: Write the failing tests** (append to `tests/test_overlay_qml.py`)

```python
def visible_text(item):
    return item.findChild(QObject, "subtitleText").property("text")


def test_subtitle_mode_shows_only_the_newest_utterance(overlay):
    window, captions, _, warnings = overlay
    window.store.setValue("caption_mode", "subtitle")
    captions.apply([Final(0, "first sentence."), Partial(1, "second")])
    settle()

    subtitle = window.findChild(QObject, "subtitleView")
    assert subtitle.property("visible")
    assert not window.findChild(QObject, "captionList").property("visible")
    assert visible_text(subtitle) == "second"
    assert warnings == []


def test_switching_mode_keeps_current_text(overlay):
    window, captions, _, _ = overlay
    captions.apply([Partial(0, "mid sentence")])
    settle()

    window.store.setValue("caption_mode", "subtitle")
    settle()
    assert visible_text(window.findChild(QObject, "subtitleView")) == "mid sentence"

    window.store.setValue("caption_mode", "rolling")
    settle()
    assert window.findChild(QObject, "captionList").property("count") == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_overlay_qml.py -k subtitle -v`
Expected: FAIL (`subtitleView` not found → `AttributeError: 'NoneType'`).

- [ ] **Step 3: Implement**

`echoline/ui/qml/SubtitleView.qml`:
```qml
import QtQuick

// Newest utterance as one block; cross-fades when a new utterance starts.
Item {
    id: root
    objectName: "subtitleView"
    required property var s
    required property real lineHeight
    property int shownId: -1
    implicitHeight: lineHeight * s.line_count
    clip: true

    Text {
        id: subtitleText
        objectName: "subtitleText"
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        wrapMode: Text.Wrap
        horizontalAlignment: Text.AlignHCenter
        color: root.s.text_color
        font.family: root.s.font_family
        font.pixelSize: root.s.font_size
        font.weight: root.s.font_weight
        lineHeight: 1.15
        style: ({ "outline": Text.Outline, "shadow": Text.Raised, "none": Text.Normal })[root.s.outline]
        styleColor: root.s.outline_color
        text: captions.latestText
    }

    SequentialAnimation {
        id: crossFade
        NumberAnimation { target: subtitleText; property: "opacity"; to: 0; duration: 150 }
        NumberAnimation { target: subtitleText; property: "opacity"; to: 1; duration: 150 }
    }

    Connections {
        target: captions
        function onLatestChanged() {
            if (captions.latestId !== root.shownId) {
                if (root.shownId !== -1)
                    crossFade.restart()
                root.shownId = captions.latestId
            }
        }
    }
}
```
Because the text sits anchored to the bottom of a clipped item of fixed height, a long utterance shows its last `line_count` lines.

In `Overlay.qml`: give `captionList` `visible: overlay.s.caption_mode === "rolling"` and set its `height` to `visible ? overlay.lineHeight * overlay.s.line_count : 0`; directly after the ListView add:
```qml
            SubtitleView {
                width: parent.width
                height: visible ? implicitHeight : 0
                visible: overlay.s.caption_mode === "subtitle"
                s: overlay.s
                lineHeight: overlay.lineHeight
            }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_overlay_qml.py -v`
Expected: all passed, no QML warnings.

- [ ] **Step 5: Commit**

```bash
git add echoline/ui/qml tests/test_overlay_qml.py
git commit -m "Add subtitle caption mode" -m "Shows only the newest utterance as one centered block that cross-fades to the next, for viewers who expect film-style subtitles."
```

---

### Task 8: Remembered position and snap presets

**Files:**
- Create: `echoline/ui/placement.py`
- Modify: `echoline/ui/qml/Overlay.qml`, `echoline/app.py`
- Test: `tests/test_placement.py`, `tests/test_echoline_app.py`

**Interfaces:**
- Produces:
  - `snap_position(screen: tuple[int,int,int,int], size: tuple[int,int], where: str, margin: int = 48) -> list[int]` — `screen` is `(x, y, width, height)` of the available geometry; `where` is `"top"`, `"center"` or `"bottom"`; horizontally centered.
  - `clamp_to_screen(position: list | None, size, screens: list[tuple]) -> list[int]` — returns `position` if the window would be at least 60% visible on some screen, otherwise the `"bottom"` snap position on the first (primary) screen. `None` also yields the bottom snap.
  - `Controller(QObject)` in `echoline/app.py` with `@Slot(str) snap(where)`; `EchoLineApp` places the window at `clamp_to_screen(settings.position, …)` on start and persists the position (`settingsStore.setValue("position", [x, y])`) 500 ms after the window stops moving.

- [ ] **Step 1: Write the failing tests**

`tests/test_placement.py`:
```python
from echoline.ui.placement import clamp_to_screen, snap_position

SCREEN = (0, 0, 1920, 1040)
SIZE = (670, 120)


def test_snap_positions_are_centered_with_margin():
    assert snap_position(SCREEN, SIZE, "bottom") == [625, 1040 - 120 - 48]
    assert snap_position(SCREEN, SIZE, "top") == [625, 48]
    assert snap_position(SCREEN, SIZE, "center") == [625, 460]


def test_visible_position_is_kept():
    assert clamp_to_screen([100, 200], SIZE, [SCREEN]) == [100, 200]


def test_offscreen_position_is_pulled_back_on_screen():
    # Saved on a second monitor that is no longer connected.
    assert clamp_to_screen([2500, 300], SIZE, [SCREEN]) == snap_position(SCREEN, SIZE, "bottom")


def test_position_on_a_secondary_screen_is_kept():
    second = (1920, 0, 1280, 1024)

    assert clamp_to_screen([2000, 300], SIZE, [SCREEN, second]) == [2000, 300]


def test_no_saved_position_snaps_to_bottom():
    assert clamp_to_screen(None, SIZE, [SCREEN]) == snap_position(SCREEN, SIZE, "bottom")
```
Append to `tests/test_echoline_app.py`:
```python
def test_snap_moves_window_and_remembers_position(running):
    echoline, _ = running

    echoline.controller.snap("top")

    # Startup placement may already have saved a position; wait for the snapped one.
    assert wait_until(lambda: echoline.settings_store.settings.position
                      == [echoline.window.x(), echoline.window.y()], timeout=2)
    assert echoline.window.y() < 100
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_placement.py tests/test_echoline_app.py -v`
Expected: FAIL (`ModuleNotFoundError: echoline.ui.placement`; `EchoLineApp` has no `controller`).

- [ ] **Step 3: Implement**

`echoline/ui/placement.py`:
```python
def snap_position(screen, size, where, margin=48):
    sx, sy, sw, sh = screen
    w, h = size
    x = sx + (sw - w) // 2
    y = {"top": sy + margin, "center": sy + (sh - h) // 2, "bottom": sy + sh - h - margin}[where]
    return [x, y]


def _visible_fraction(position, size, screen):
    x, y = position
    w, h = size
    sx, sy, sw, sh = screen
    overlap_w = max(0, min(x + w, sx + sw) - max(x, sx))
    overlap_h = max(0, min(y + h, sy + sh) - max(y, sy))
    return overlap_w * overlap_h / max(w * h, 1)


def clamp_to_screen(position, size, screens):
    if position and any(_visible_fraction(position, size, s) >= 0.6 for s in screens):
        return list(position)
    return snap_position(screens[0], size, "bottom")
```

`echoline/app.py`:
- add imports `from PySide6.QtCore import QTimer, Slot` and `from .ui.placement import clamp_to_screen, snap_position`.
- add, above `EchoLineApp`:
```python
class Controller(QObject):
    """Actions the QML UI can trigger."""

    def __init__(self, app):
        super().__init__()
        self._app = app

    @Slot(str)
    def snap(self, where):
        self._app.snap(where)
```
- in `EchoLineApp.__init__`: store `self.settings_store = settings_store`, create `self.controller = Controller(self)` before loading QML and pass it to `load_overlay(..., settings_store, self.controller)`. After loading:
```python
        self._save_position = QTimer(singleShot=True, interval=500)
        self._save_position.timeout.connect(
            lambda: self.settings_store.setValue("position", [self.window.x(), self.window.y()]))
        self._place_window()
        self.window.xChanged.connect(self._save_position.start)
        self.window.yChanged.connect(self._save_position.start)
```
- add methods:
```python
    def _screen_rects(self):
        from PySide6.QtGui import QGuiApplication
        screens = [QGuiApplication.primaryScreen()] + [
            s for s in QGuiApplication.screens() if s is not QGuiApplication.primaryScreen()]
        return [(g.x(), g.y(), g.width(), g.height()) for g in (s.availableGeometry() for s in screens)]

    def _place_window(self):
        size = (self.window.width(), self.window.height())
        x, y = clamp_to_screen(self.settings_store.settings.position, size, self._screen_rects())
        self.window.setPosition(x, y)

    def snap(self, where):
        size = (self.window.width(), self.window.height())
        x, y = snap_position(self._screen_rects()[0], size, where)
        self.window.setPosition(x, y)
```
- in `Overlay.qml` remove the `x:` and `y:` bindings (Python now places the window).

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_placement.py tests/test_echoline_app.py tests/test_overlay_qml.py -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add echoline/ui/placement.py echoline/ui/qml/Overlay.qml echoline/app.py tests/test_placement.py tests/test_echoline_app.py
git commit -m "Remember the overlay position and add snap presets" -m "The overlay returns where it was left, snaps to top, center or bottom on request, and comes back on the primary screen when its saved spot is no longer visible (for example after unplugging a monitor)."
```

---

### Task 9: Acrylic blur behind the captions

**Files:**
- Create: `echoline/ui/blur.py`
- Modify: `echoline/app.py`
- Test: `tests/test_blur.py`

**Interfaces:**
- Produces: `set_acrylic(hwnd: int, enabled: bool, user32=None) -> bool` — calls `user32.SetWindowCompositionAttribute` with `ACCENT_ENABLE_ACRYLICBLURBEHIND` (4) when enabled, `ACCENT_DISABLED` (0) otherwise; returns the call's truthiness; returns `False` (no exception) if the function is missing. `EchoLineApp` applies it to `int(self.window.winId())` at start and whenever `blur_behind` changes.

- [ ] **Step 1: Write the failing tests**

`tests/test_blur.py`:
```python
from echoline.ui.blur import ACCENT_DISABLED, ACCENT_ENABLE_ACRYLICBLURBEHIND, set_acrylic


class FakeUser32:
    def __init__(self):
        self.calls = []

    def SetWindowCompositionAttribute(self, hwnd, data_pointer):
        data = data_pointer._obj
        accent = data.Data.contents if hasattr(data.Data, "contents") else None
        self.calls.append((hwnd, data.Attribute, accent.AccentState))
        return 1


def test_enabling_requests_acrylic_blur():
    user32 = FakeUser32()

    assert set_acrylic(1234, True, user32=user32)
    assert user32.calls == [(1234, 19, ACCENT_ENABLE_ACRYLICBLURBEHIND)]


def test_disabling_turns_the_accent_off():
    user32 = FakeUser32()

    set_acrylic(1234, False, user32=user32)

    assert user32.calls[-1][2] == ACCENT_DISABLED


def test_missing_api_is_ignored():
    assert set_acrylic(1234, True, user32=object()) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_blur.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'echoline.ui.blur'`.

- [ ] **Step 3: Implement**

`echoline/ui/blur.py`:
```python
import ctypes
from ctypes import wintypes

ACCENT_DISABLED = 0
ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
WCA_ACCENT_POLICY = 19


class AccentPolicy(ctypes.Structure):
    _fields_ = [("AccentState", ctypes.c_int), ("AccentFlags", ctypes.c_int),
                ("GradientColor", ctypes.c_uint), ("AnimationId", ctypes.c_int)]


class WindowCompositionAttributeData(ctypes.Structure):
    _fields_ = [("Attribute", ctypes.c_int), ("Data", ctypes.POINTER(AccentPolicy)),
                ("SizeOfData", ctypes.c_size_t)]


def set_acrylic(hwnd, enabled, user32=None):
    """Blur whatever is behind the overlay (Windows 10 1803+). Best effort: no-op if unsupported."""
    if user32 is None:
        user32 = ctypes.windll.user32
    set_attribute = getattr(user32, "SetWindowCompositionAttribute", None)
    if set_attribute is None:
        return False
    accent = AccentPolicy(ACCENT_ENABLE_ACRYLICBLURBEHIND if enabled else ACCENT_DISABLED, 0,
                          0x01000000, 0)   # near-transparent tint; the panel draws the color
    data = WindowCompositionAttributeData(WCA_ACCENT_POLICY, ctypes.pointer(accent), ctypes.sizeof(accent))
    return bool(set_attribute(wintypes.HWND(hwnd).value or hwnd, ctypes.byref(data)))
```

In `echoline/app.py` add `from .ui.blur import set_acrylic`, and at the end of `EchoLineApp.__init__`:
```python
        self._apply_blur()
        settings_store.valuesChanged.connect(self._apply_blur)
```
with
```python
    def _apply_blur(self):
        enabled = self.settings_store.settings.blur_behind
        if enabled != getattr(self, "_blur_applied", None):
            self._blur_applied = enabled
            set_acrylic(int(self.window.winId()), enabled)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_blur.py tests/test_echoline_app.py -v`
Expected: all passed.

- [ ] **Step 5: Manual visual check**

Run: `.venv/Scripts/python -c "from echoline.engine.moonshine_engine import preload_native_library; preload_native_library(); import json, os, pathlib; p=pathlib.Path(os.environ['APPDATA'])/'EchoLine'/'settings.json'; p.parent.mkdir(parents=True, exist_ok=True); d=json.loads(p.read_text()) if p.exists() else {}; d.update(blur_behind=True, background_opacity=0.3); p.write_text(json.dumps(d)); print('blur on')"` then `.venv/Scripts/python -m echoline` over a busy window (the human partner looks: background behind the captions should be blurred). If acrylic draws an unrounded rectangle that looks wrong, set `corner_radius` 0 when blur is on and record it as a ruling. Restore the setting afterwards.

- [ ] **Step 6: Commit**

```bash
git add echoline/ui/blur.py echoline/app.py tests/test_blur.py
git commit -m "Add optional acrylic blur behind the captions" -m "Uses the Windows accent policy so busy video behind a translucent caption box stays readable; silently does nothing where unsupported."
```

---

### Task 10: Settings window, right-click menu and Ctrl+,

**Files:**
- Create: `echoline/ui/fonts.py`, `echoline/ui/qml/Settings.qml`
- Modify: `echoline/ui/qml/Overlay.qml`, `echoline/app.py`, `echoline/__main__.py`
- Test: `tests/test_fonts.py`, `tests/test_settings_window.py`, `tests/test_echoline_app.py`

**Interfaces:**
- Consumes: `SettingsStore` (4), `Controller` (8), `PRESETS` via `settingsStore.themeNames`.
- Produces:
  - `caption_fonts(system_families: list[str]) -> list[str]` — curated `["Segoe UI", "Arial", "Verdana", "Tahoma", "Calibri", "Consolas", "Georgia"]` (only those installed) first, then the remaining system families alphabetically, without duplicates or `@`-prefixed vertical fonts.
  - `Controller` gains `@Slot() openSettings()` and `@Slot() quit()`, and `fonts` (`Property(list, constant=True)`).
  - `EchoLineApp.open_settings()` loads `Settings.qml` once (lazily) into the same QML engine and shows/raises it; the window `objectName` is `"settingsWindow"`.
  - `EchoLineApp.shutdown()` calls `settings_store.save_now()`.
  - `EchoLineApp(..., settings_reset=False)`: when `True`, the overlay status shows `"settings-reset"` ("Settings were damaged and have been reset") for 6 s after start, then returns to the source state.
  - Overlay: right-click opens a `Menu` with "Settings…" (`controller.openSettings()`) and "Quit" (`controller.quit()`); `Shortcut { sequence: "Ctrl+," }` opens settings.

Settings window layout (FluentWinUI3, 520×600, `title: "EchoLine settings"`), a `TabBar` with three pages:
- **Appearance:** Theme `ComboBox` (`objectName: "themeBox"`, model = `settingsStore.themeNames` plus "Custom" shown as the current label when custom); Font `ComboBox` (`"fontBox"`, model `controller.fonts`); Size `Slider` (`"sizeSlider"`, 14–64, step 1); Weight `ComboBox` (Regular 400 / Medium 500 / Semibold 600 / Bold 700); Text color and Background color as rows of 6 swatch buttons (white, yellow, cyan, green, black, grey); Effect `ComboBox` (Outline / Shadow / None); Background opacity `Slider` (`"opacitySlider"`, 0–1, step 0.05); Corner radius `Slider` (0–32); Blur `Switch`.
- **Layout:** Caption style `ComboBox` (Rolling / Subtitle, `"modeBox"`); Lines `SpinBox` (1–3); Width `Slider` (20–90 %); Snap buttons Top / Center / Bottom (`controller.snap(...)`); Always on top `Switch`.
- **About:** app name, version `0.2.0`, "Live captions run entirely on this PC", link to the GitHub repository.

Every control reads its value from `settingsStore.values.<key>` and calls `settingsStore.setValue("<key>", value)` on `moved`/`activated`/`toggled`, so the overlay previews changes live.

- [ ] **Step 1: Write the failing tests**

`tests/test_fonts.py`:
```python
from echoline.ui.fonts import caption_fonts


def test_curated_fonts_come_first_then_the_rest_alphabetically():
    system = ["Wingdings", "Arial", "Segoe UI", "@Malgun Gothic", "Comic Sans MS", "Arial"]

    assert caption_fonts(system) == ["Segoe UI", "Arial", "Comic Sans MS", "Wingdings"]
```

`tests/test_settings_window.py`:
```python
import time

import pytest
from PySide6.QtCore import QObject
from PySide6.QtGui import QGuiApplication

from echoline.app import EchoLineApp
from echoline.engine.base import Partial
from echoline.settings.model import Settings
from echoline.settings.store import SettingsStore

app = QGuiApplication.instance()


class FakeSource:
    def start(self, on_audio, on_status):
        on_status("listening")

    def stop(self):
        pass


class EchoEngine:
    def feed(self, samples):
        return [Partial(0, "hi")]

    def flush(self):
        return []


def wait_until(condition, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    return False


@pytest.fixture
def settings_window(tmp_path):
    store = SettingsStore(Settings(), tmp_path / "settings.json")
    echoline = EchoLineApp(FakeSource(), EchoEngine, store)
    warnings = []
    echoline.qml.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))
    window = echoline.open_settings()
    yield echoline, window, store, warnings
    echoline.shutdown()


def test_settings_window_opens_without_qml_warnings(settings_window):
    _, window, _, warnings = settings_window
    wait_until(lambda: False, timeout=0.3)

    assert window.objectName() == "settingsWindow"
    assert window.isVisible()
    assert warnings == []


def test_moving_the_size_slider_updates_the_store(settings_window):
    _, window, store, _ = settings_window
    slider = window.findChild(QObject, "sizeSlider")

    slider.setProperty("value", 40)
    slider.moved.emit()

    assert store.settings.font_size == 40


def test_choosing_a_theme_applies_it(settings_window):
    _, window, store, _ = settings_window
    box = window.findChild(QObject, "themeBox")

    box.activated.emit(box.property("model").index("High contrast"))

    assert store.settings.theme == "High contrast"


def test_opening_twice_reuses_the_window(settings_window):
    echoline, window, _, _ = settings_window

    assert echoline.open_settings() is window
```
Append to `tests/test_echoline_app.py`:
```python
def test_shutdown_saves_pending_settings(tmp_path):
    from echoline.settings.model import Settings, load_settings
    from echoline.settings.store import SettingsStore

    path = tmp_path / "settings.json"
    store = SettingsStore(Settings(), path, save_delay_ms=60_000)
    echoline = EchoLineApp(FakeSource(), EchoEngine, store)
    store.setValue("font_size", 33)

    echoline.shutdown()

    assert load_settings(path)[0].font_size == 33


def test_reset_settings_are_announced(tmp_path):
    from echoline.settings.model import Settings
    from echoline.settings.store import SettingsStore

    echoline = EchoLineApp(FakeSource(), EchoEngine, SettingsStore(Settings(), tmp_path / "s.json"),
                           settings_reset=True)
    echoline.start()
    try:
        assert wait_until(lambda: echoline.status.property("state") == "settings-reset")
    finally:
        echoline.shutdown()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_fonts.py tests/test_settings_window.py tests/test_echoline_app.py -v`
Expected: FAIL (`ModuleNotFoundError: echoline.ui.fonts`; `EchoLineApp` has no `open_settings`).

- [ ] **Step 3: Implement**

`echoline/ui/fonts.py`:
```python
CURATED = ["Segoe UI", "Arial", "Verdana", "Tahoma", "Calibri", "Consolas", "Georgia"]


def caption_fonts(system_families):
    available = {f for f in system_families if not f.startswith("@")}
    curated = [f for f in CURATED if f in available]
    return curated + sorted(available - set(curated), key=str.lower)
```

`echoline/app.py` changes:
- `Controller` gains:
```python
    @Slot()
    def openSettings(self):
        self._app.open_settings()

    @Slot()
    def quit(self):
        from PySide6.QtCore import QCoreApplication
        QCoreApplication.quit()

    def _get_fonts(self):
        from PySide6.QtGui import QFontDatabase
        from .ui.fonts import caption_fonts
        return caption_fonts(QFontDatabase.families())

    fonts = Property(list, _get_fonts, constant=True)
```
  (import `Property` from `PySide6.QtCore`).
- `EchoLineApp.__init__(self, source, engine_factory, settings_store, show_latency=False, settings_reset=False)`; keep `self._settings_reset = settings_reset` and `self.settings_window = None`.
- `start()`: after `self.status.set_state("loading")`, if `self._settings_reset`: set `self._notice_active = True`, `self.status.set_state("settings-reset")`, and `QTimer.singleShot(6000, self._end_notice)`. `_on_status` keeps recording `self._source_state` but does not change the displayed state while `_notice_active` is true (otherwise the first "listening" would hide the notice at once). `_end_notice()` clears the flag and shows `self._source_state if self.worker else "loading"`.
- add:
```python
    def open_settings(self):
        if self.settings_window is None:
            from PySide6.QtCore import QUrl
            from .ui.overlay import QML_DIR
            before = len(self.qml.rootObjects())
            self.qml.load(QUrl.fromLocalFile(str(QML_DIR / "Settings.qml")))
            root = self.qml.rootObjects()[before]
            self.settings_window = shiboken6.wrapInstance(shiboken6.getCppPointer(root)[0], QQuickWindow)
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.requestActivate()
        return self.settings_window
```
  (import `shiboken6` and `QQuickWindow`).
- `shutdown()`: add `self.settings_store.save_now()` before closing windows, and close `self.settings_window` if open.

`echoline/__main__.py`: `settings, was_reset = load_settings(path)`; pass `settings_reset=was_reset` to `EchoLineApp`.

`echoline/ui/qml/Overlay.qml`: inside `panel`, add
```qml
        TapHandler {
            acceptedButtons: Qt.RightButton
            onTapped: contextMenu.popup()
        }
        Menu {
            id: contextMenu
            MenuItem { text: "Settings…"; onTriggered: controller.openSettings() }
            MenuItem { text: "Quit"; onTriggered: controller.quit() }
        }
```
add `import QtQuick.Controls` at the top, a `Shortcut { sequence: "Ctrl+,"; onActivated: controller.openSettings() }`, and the status text mapping `"settings-reset": "Settings were damaged and have been reset"`.

`echoline/ui/qml/Settings.qml`:
```qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: win
    objectName: "settingsWindow"
    title: "EchoLine settings"
    width: 520
    height: 600
    visible: false
    readonly property var s: settingsStore.values

    component Row2: RowLayout {
        property alias label: name.text
        Layout.fillWidth: true
        spacing: 12
        Label { id: name; Layout.preferredWidth: 150 }
    }

    component Swatches: Row {
        property string key
        spacing: 6
        Repeater {
            model: ["#ffffff", "#ffff00", "#00ffff", "#00ff00", "#000000", "#808080"]
            delegate: Rectangle {
                required property string modelData
                width: 28; height: 28; radius: 14
                color: modelData
                border.width: win.s[parent.key] === modelData ? 3 : 1
                border.color: palette.highlight
                TapHandler { onTapped: settingsStore.setValue(parent.parent.key, parent.modelData) }
            }
        }
    }

    header: TabBar {
        id: tabs
        TabButton { text: "Appearance" }
        TabButton { text: "Layout" }
        TabButton { text: "About" }
    }

    StackLayout {
        anchors.fill: parent
        anchors.margins: 20
        currentIndex: tabs.currentIndex

        ColumnLayout {
            spacing: 14
            Row2 {
                label: "Theme"
                ComboBox {
                    objectName: "themeBox"
                    Layout.fillWidth: true
                    model: settingsStore.themeNames
                    displayText: win.s.theme
                    onActivated: (index) => settingsStore.applyTheme(model[index])
                }
            }
            Row2 {
                label: "Font"
                ComboBox {
                    objectName: "fontBox"
                    Layout.fillWidth: true
                    model: controller.fonts
                    currentIndex: model.indexOf(win.s.font_family)
                    onActivated: (index) => settingsStore.setValue("font_family", model[index])
                }
            }
            Row2 {
                label: "Size"
                Slider {
                    objectName: "sizeSlider"
                    Layout.fillWidth: true
                    from: 14; to: 64; stepSize: 1
                    value: win.s.font_size
                    onMoved: settingsStore.setValue("font_size", value)
                }
            }
            Row2 {
                label: "Weight"
                ComboBox {
                    Layout.fillWidth: true
                    textRole: "text"; valueRole: "value"
                    model: [{ text: "Regular", value: 400 }, { text: "Medium", value: 500 },
                            { text: "Semibold", value: 600 }, { text: "Bold", value: 700 }]
                    currentIndex: indexOfValue(win.s.font_weight)
                    onActivated: settingsStore.setValue("font_weight", currentValue)
                }
            }
            Row2 { label: "Text color"; Swatches { key: "text_color" } }
            Row2 {
                label: "Text effect"
                ComboBox {
                    Layout.fillWidth: true
                    textRole: "text"; valueRole: "value"
                    model: [{ text: "Outline", value: "outline" }, { text: "Shadow", value: "shadow" },
                            { text: "None", value: "none" }]
                    currentIndex: indexOfValue(win.s.outline)
                    onActivated: settingsStore.setValue("outline", currentValue)
                }
            }
            Row2 { label: "Background"; Swatches { key: "background_color" } }
            Row2 {
                label: "Background opacity"
                Slider {
                    objectName: "opacitySlider"
                    Layout.fillWidth: true
                    from: 0; to: 1; stepSize: 0.05
                    value: win.s.background_opacity
                    onMoved: settingsStore.setValue("background_opacity", value)
                }
            }
            Row2 {
                label: "Corner radius"
                Slider {
                    Layout.fillWidth: true
                    from: 0; to: 32; stepSize: 1
                    value: win.s.corner_radius
                    onMoved: settingsStore.setValue("corner_radius", value)
                }
            }
            Row2 {
                label: "Blur behind"
                Switch { checked: win.s.blur_behind; onToggled: settingsStore.setValue("blur_behind", checked) }
            }
            Item { Layout.fillHeight: true }
        }

        ColumnLayout {
            spacing: 14
            Row2 {
                label: "Caption style"
                ComboBox {
                    objectName: "modeBox"
                    Layout.fillWidth: true
                    textRole: "text"; valueRole: "value"
                    model: [{ text: "Rolling lines", value: "rolling" }, { text: "Subtitle blocks", value: "subtitle" }]
                    currentIndex: indexOfValue(win.s.caption_mode)
                    onActivated: settingsStore.setValue("caption_mode", currentValue)
                }
            }
            Row2 {
                label: "Lines"
                SpinBox {
                    from: 1; to: 3
                    value: win.s.line_count
                    onValueModified: settingsStore.setValue("line_count", value)
                }
            }
            Row2 {
                label: "Width"
                Slider {
                    Layout.fillWidth: true
                    from: 20; to: 90; stepSize: 1
                    value: win.s.width_percent
                    onMoved: settingsStore.setValue("width_percent", value)
                }
            }
            Row2 {
                label: "Position"
                Button { text: "Top"; onClicked: controller.snap("top") }
                Button { text: "Center"; onClicked: controller.snap("center") }
                Button { text: "Bottom"; onClicked: controller.snap("bottom") }
            }
            Row2 {
                label: "Always on top"
                Switch { checked: win.s.always_on_top; onToggled: settingsStore.setValue("always_on_top", checked) }
            }
            Item { Layout.fillHeight: true }
        }

        ColumnLayout {
            spacing: 10
            Label { text: "EchoLine"; font.pixelSize: 24; font.weight: Font.DemiBold }
            Label { text: "Version 0.2.0" }
            Label { text: "Live captions run entirely on this PC; nothing you hear leaves it."; wrapMode: Text.Wrap; Layout.fillWidth: true }
            Label {
                text: "<a href='https://github.com/coderconnoisseur/EchoLine'>github.com/coderconnoisseur/EchoLine</a>"
                onLinkActivated: (link) => Qt.openUrlExternally(link)
            }
            Item { Layout.fillHeight: true }
        }
    }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest -q`
Expected: all passed; the settings window test reports no QML warnings. Fix any QML warning before continuing.

- [ ] **Step 5: Manual check**

Run `.venv/Scripts/python -m echoline`, right-click the overlay → Settings…, and check: each control previews live on the overlay; choosing "High contrast" then moving the size slider shows "Custom"; Layout → Subtitle switches modes; Top/Center/Bottom move the overlay; restart keeps all changes and the position. Capture `grabWindow()` screenshots of the settings window and of each theme for the review.

- [ ] **Step 6: Commit**

```bash
git add echoline/ui/fonts.py echoline/ui/qml/Settings.qml echoline/ui/qml/Overlay.qml echoline/app.py echoline/__main__.py tests/test_fonts.py tests/test_settings_window.py tests/test_echoline_app.py
git commit -m "Add the settings window" -m "Fluent-styled window with Appearance, Layout and About pages; every change previews live on the overlay. Opens from a right-click menu on the overlay or Ctrl+,. Settings are saved on quit, and a damaged settings file is announced after it is reset."
```

---

### Task 11: Document customization

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update the README**

Under Features add: "Four caption themes (Classic CC, Netflix, Minimal, High contrast) and full control over font, size, colors, outline, background, width and line count", "Rolling lines or subtitle blocks", "Remembers where you put it". Add a "Customizing" section: right-click the captions (or press `Ctrl+,`) to open settings; settings are stored in `%APPDATA%\EchoLine\settings.json`. Update the Requirements line for PySide6 if mentioned.

- [ ] **Step 2: Verify and commit**

Run: `.venv/Scripts/python -m pytest -q` → all passed.

```bash
git add README.md
git commit -m "Document caption customization"
```

---

## Spec coverage (self-review)

| Spec item (M2) | Task |
|---|---|
| Settings persistence, `%APPDATA%\EchoLine\settings.json`, invalid values → defaults | 2 |
| Corrupt file → back up, defaults, notify once | 2, 10 |
| Themes: Classic CC, Netflix, Minimal, High-contrast | 3 |
| Text style: font, size, weight, color, outline/shadow, 1–3 lines | 6, 10 |
| Background: color, opacity, radius, width, blur-behind | 6, 9, 10 |
| Position & behavior: drag, snap presets, always-on-top | 8, 10 (click-through and auto-hide are M3) |
| Resize | width slider in settings (Task 10); edge-drag resize deferred to M3 with the hover bar |
| Subtitle mode with cross-fade | 5, 7 |
| Settings window with live preview | 10 |
| Fluent look (user decision) | 1, 10 |

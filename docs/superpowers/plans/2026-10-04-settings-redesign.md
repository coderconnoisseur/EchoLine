# Settings Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the tabbed settings form with a sidebar ("Studio") window: six pages, grouped cards with descriptions, a live looping caption preview, theme gallery, following Windows' light/dark theme and accent colour.

**Architecture:** `Settings.qml` becomes a shell (sidebar + `StackLayout` of six page items). Shared pieces live in `echoline/ui/qml/settings/` (`Theme`, `SettingsCard`, `SettingRow`, `PreviewPane`, `ThemeGallery`). A Python `SampleCaptions` replays a scripted sentence into its own `CaptionModel` while the window is visible; the preview renders it with the real `CaptionLine`.

**Tech Stack:** PySide6 6.11 QML (FluentWinUI3 style), pytest offscreen.

**Spec:** `docs/superpowers/specs/2026-10-04-settings-redesign-design.md`

## Global Constraints

- Window 880×620, min 760×520; sidebar 176 px; page padding 24 px; content max width 640 px; card radius 8 px.
- Every existing setting stays reachable; keep these `objectName`s on their controls: `fontBox`, `sizeSlider`, `weightBox`, `effectBox`, `opacitySlider`, `modeBox`, `onTopSwitch`, `sourceBox`, `autoHideSwitch`, `clickThroughSwitch`, `autostartSwitch`, `modelBox`, `modelProgress`, `hotkeyShowHide`, `hotkeyPause`, `hotkeyClickThrough`. New: `sidebar`, page items `page appearance|position|behavior|speech|shortcuts|about`, theme cards `theme <name>`, `previewPane`, window property `page` (string).
- No Loaders for pages (tests reach controls on hidden pages).
- No QML warnings, in dark and light.
- Commits: "why" bodies, never mention Claude/AI.

## Review Focus

1. Light mode → every custom surface readable (text on cards, sidebar selection) (Task 4 `test_window_loads_in_light_and_dark` + Task 5 screenshots).
2. Keyboard-only use → sidebar Up/Down changes pages; Tab reaches page controls (Task 4 `test_arrow_keys_move_through_pages`).
3. Hotkey recording on the Shortcuts page still receives keys (Task 4 updates `test_pressing_keys_records_a_new_hotkey` to open the page first).
4. Preview CPU → the sample timer stops when the window hides (Task 1 + Task 4 `test_sample_runs_only_while_visible`).
5. Theme tweak → gallery shows "Custom" rather than a wrong preset (Task 3 `test_gallery_marks_active_theme_and_custom`).

---

### Task 1: SampleCaptions

**Files:** Create `echoline/ui/sample.py`; Test `tests/test_sample.py`

**Produces:** `SampleCaptions(step_ms=350, parent=None)` QObject; attribute `captions` (CaptionModel) and Qt property `captions`; `start()`, `stop()`, `running` (bool); class attr `SCRIPT` (list of event lists).

- [ ] **Step 1: Failing tests**

```python
import time

from PySide6.QtCore import QCoreApplication

from echoline.ui.sample import SampleCaptions

app = QCoreApplication.instance() or QCoreApplication([])


def run_for(seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)


def test_sample_plays_the_script_and_loops():
    sample = SampleCaptions(step_ms=5)
    seen = set()
    sample.captions.latestChanged.connect(lambda: seen.add(sample.captions.property("latestText")))
    sample.start()
    run_for(0.3 + len(SampleCaptions.SCRIPT) * 0.005 * 3)
    sample.stop()
    finals = [events[-1].text for events in SampleCaptions.SCRIPT if type(events[-1]).__name__ == "Final"]
    assert finals and finals[0] in seen
    assert sample.loops >= 1


def test_stop_halts_the_sample():
    sample = SampleCaptions(step_ms=5)
    sample.start()
    run_for(0.05)
    sample.stop()
    assert not sample.running
    text = sample.captions.property("latestText")
    run_for(0.1)
    assert sample.captions.property("latestText") == text
```

- [ ] **Step 2:** run → FAIL (no module).
- [ ] **Step 3: Implement**

```python
from PySide6.QtCore import Property, QObject, QTimer

from ..captions.model import CaptionModel
from ..engine.base import Final, Partial


class SampleCaptions(QObject):
    """A short scripted sentence for the settings preview, replayed in a loop."""

    # One entry per step: words arriving, a correction, a final, then a pause.
    SCRIPT = [
        [Partial(0, "It was")], [Partial(0, "It was the best")], [Partial(0, "It was the beast of")],
        [Partial(0, "It was the best of times,")], [Partial(0, "It was the best of times, it was")],
        [Partial(0, "It was the best of times, it was the worst of times")],
        [Final(0, "It was the best of times, it was the worst of times.")], [], [], [], [],
    ]

    def __init__(self, step_ms=350, parent=None):
        super().__init__(parent)
        self._model = CaptionModel(max_utterances=2, settle_after_ms=500, parent=self)
        self._timer = QTimer(self, interval=step_ms)
        self._timer.timeout.connect(self._step)
        self._index = 0
        self._utterance = 0
        self.loops = 0

    captions = Property(QObject, lambda self: self._model, constant=True)

    @property
    def running(self):
        return self._timer.isActive()

    def start(self):
        self._timer.start()

    def stop(self):
        self._timer.stop()

    def _step(self):
        events = self.SCRIPT[self._index]
        # A fresh utterance id per loop so the preview shows a new line each time.
        self._model.apply([type(e)(self._utterance, e.text) for e in events])
        self._index += 1
        if self._index == len(self.SCRIPT):
            self._index = 0
            self._utterance += 1
            self.loops += 1
```

Note: tests read `sample.captions` as the Python attribute too — the Qt `Property` getter returns the model, and PySide exposes it as an attribute.

- [ ] **Step 4:** run → PASS. **Commit** — "Add a looping sample caption for the settings preview".

---

### Task 2: Settings building blocks

**Files:** Create `echoline/ui/qml/settings/Theme.qml`, `SettingsCard.qml`, `SettingRow.qml`; Test `tests/test_settings_parts.py`

**Produces:**
- `Theme { dark: bool; accent: color; window; sidebar; sidebarSelected; card; cardBorder; divider; text; subtext; backdropTop; backdropBottom }` — `dark` defaults to `Application.styleHints.colorScheme === Qt.Dark`; `accent` defaults to `palette.accent`.
- `SettingsCard { title: string; default property alias rows }` — title label above a rounded card; children laid out in a ColumnLayout with 1 px dividers between them.
- `SettingRow { title: string; description: string; default property alias control }` — 56 px min height (44 without description), title + description on the left, control on the right.

- [ ] **Step 1: Failing test** — load a small QML snippet (via `QQmlComponent.setData` with `QUrl.fromLocalFile(str(QML_DIR / "settings" / "probe.qml"))` as base URL) that imports `"."` and builds `Theme`, a `SettingsCard` holding two `SettingRow`s (one with a `Switch`), assert: no errors/warnings; card has 2 rows and 1 divider (`objectName: "divider"`); row with description is taller than without; Theme light/dark colours differ.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3: Implement** the three files (tokens — dark: window `#202020`, sidebar `#1b1b1b`, sidebarSelected `#2d2d2d`, card `#2b2b2b`, cardBorder `#353535`, divider `#3a3a3a`, text `#f3f3f3`, subtext `#a6a6a6`, backdrop `#33415e`→`#15161b`; light: window `#f3f3f3`, sidebar `#ebebeb`, sidebarSelected `#ffffff`, card `#fbfbfb`, cardBorder `#e2e2e2`, divider `#e8e8e8`, text `#1b1b1b`, subtext `#616161`, backdrop `#c7d3ea`→`#8b97ad`).
- [ ] **Step 4:** PASS. **Commit** — "Add settings cards, rows and colour tokens".

---

### Task 3: Preview pane and theme gallery

**Files:** Create `echoline/ui/qml/settings/PreviewPane.qml`, `ThemeGallery.qml`; Modify `echoline/settings/themes.py` (export `PRESETS` to QML via `SettingsStore.themePresets` property: list of `{name, ...preset}`); Test `tests/test_settings_parts.py`

**Produces:** `PreviewPane { required property var s; required property var sample }` (objectName `previewPane`, caption box objectName `previewCaption`); `ThemeGallery { required property var s }` with cards objectName `theme <name>` and a `customBadge` visible when `s.theme === "Custom"`; `SettingsStore.themePresets`.

- [ ] **Step 1: Failing tests**
  - `test_gallery_marks_active_theme_and_custom`: store with theme Minimal → card `theme Minimal` has `selected == true`, others false, `customBadge` invisible; `store.setValue("font_size", 40)` → no card selected, `customBadge` visible; clicking `theme Netflix` (`clicked.emit()`) → `store.settings.theme == "Netflix"`.
  - `test_preview_follows_style_settings`: preview's `previewCaption` background opacity equals `background_opacity`; after `setValue("font_size", 40)` the CaptionLine inside has `lineHeight` larger than before.
  - `test_theme_presets_are_exposed`: `store.property("themePresets")` names == `list(PRESETS)`.
- [ ] **Step 2:** FAIL.
- [ ] **Step 3: Implement**
  - `SettingsStore.themePresets = Property(list, lambda self: [{"name": n, **p} for n, p in PRESETS.items()], constant=True)`.
  - `PreviewPane`: Rectangle radius 10, gradient backdrop (theme tokens), caption box Rectangle anchored bottom-center 14 px up, width = min(parent width − 48, implicit), color `s.background_color` with `opacity` applied via `Qt.rgba`, radius `s.corner_radius`, padding 10/16, holding `CaptionLine { words: sample.captions.latestWords; s: pane.s }`.
  - `ThemeGallery`: `GridLayout` 4 columns; each card 76 px tall: backdrop gradient + a mini caption "Aa captions" styled by that preset (font, weight, colour, outline, background opacity/radius at scale 0.6), name label under it; `selected: s.theme === modelData.name` draws a 2 px accent border; `TapHandler`/`MouseArea` → `settingsStore.applyTheme(name)`; expose `signal clicked()` per card for tests. A "Custom" pill next to the "Theme" heading when `s.theme === "Custom"`.
- [ ] **Step 4:** PASS. **Commit** — "Add the live caption preview and theme gallery".

---

### Task 4: The Studio window

**Files:** Rewrite `echoline/ui/qml/Settings.qml`; Modify `echoline/app.py` (context property `sampleCaptions`, start/stop with the window's `visible`); Test `tests/test_settings_window.py`

**Consumes:** Tasks 1–3.

- [ ] **Step 1: Tests first**
  - Remove `test_choosing_a_theme_applies_it` (themeBox) — replaced by gallery test in Task 3; change `test_choice_boxes_show_the_current_values` to keep weight/effect/mode; `test_pressing_keys_records_a_new_hotkey` first sets `window.setProperty("page", "shortcuts")` and waits 0.2 s.
  - Add:
    ```python
    PAGES = ["appearance", "position", "behavior", "speech", "shortcuts", "about"]

    def test_sidebar_switches_pages(settings_window):
        _, window, _, warnings = settings_window
        for name in PAGES:
            window.setProperty("page", name)
            wait_until(lambda: False, timeout=0.05)
            assert find(window, f"page {name}").property("visible")
            assert all(not find(window, f"page {o}").property("visible") for o in PAGES if o != name)
        assert warnings == []

    def test_arrow_keys_move_through_pages(settings_window):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        _, window, _, _ = settings_window
        find(window, "sidebar").forceActiveFocus()
        QTest.keyClick(window, Qt.Key_Down)
        QTest.keyClick(window, Qt.Key_Down)
        assert window.property("page") == "behavior"

    def test_window_loads_in_light_and_dark(tmp_path):
        from PySide6.QtCore import Qt
        hints = QGuiApplication.styleHints()
        for scheme in (Qt.ColorScheme.Light, Qt.ColorScheme.Dark):
            hints.setColorScheme(scheme)
            store = SettingsStore(Settings(model="tiny", onboarded=True), tmp_path / f"{scheme.name}.json")
            echoline = EchoLineApp(lambda kind: FakeSource(), EchoEngine, store)
            warnings = []
            echoline.qml.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))
            window = echoline.open_settings()
            wait_until(lambda: False, timeout=0.2)
            assert warnings == [], (scheme, warnings)
            echoline.shutdown()
        hints.unsetColorScheme()

    def test_sample_runs_only_while_visible(settings_window):
        echoline, window, _, _ = settings_window
        assert echoline.sample.running
        window.close()
        wait_until(lambda: not echoline.sample.running, timeout=1)
        assert not echoline.sample.running
    ```
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3: Implement**
  - `app.py`: `self.sample = SampleCaptions(parent=None)`; `self.qml.rootContext().setContextProperty("sampleCaptions", self.sample)` in `__init__`; in `open_settings` after creating the window connect `visibleChanged` → `self.sample.start() if visible else self.sample.stop()` and start it when presenting; `shutdown` stops it.
  - `Settings.qml`: `ApplicationWindow` (title "EchoLine Settings", 880×620, min 760×520, `color: theme.window`), `property string page: "appearance"`, `Theme { id: theme }`. Row: sidebar `ListView` (objectName `sidebar`, `keyNavigationEnabled`, `currentIndex` bound both ways to `page`) with delegates (icon glyph + label, selected background + 3 px accent bar); `StackLayout` with `currentIndex: pages.indexOf(page)`; each page a `ScrollView` → `ColumnLayout` (max width 640, centered) with title + cards.
  - Port each control from the old file into `SettingRow`s, keeping objectNames and handlers exactly (font/size/weight/text colour swatches/effect; background swatches/opacity/radius/blur; mode/lines/width/snap buttons/on top; source/auto-hide/click-through/autostart; model combo + progress + current-model line; three HotkeyButtons with the same Keys handling; About: name, version `0.3.0`, privacy text, "MIT License", GitHub link).
  - Descriptions (secondary line): Size "How big caption text is"; Effect "Keeps text readable over bright video"; Opacity "How solid the caption box is"; Blur behind "Frosted glass under the captions"; Caption style "Rolling lines scroll up; subtitle blocks replace each phrase"; Lines "How many lines stay on screen"; Width "Share of the screen width"; Always on top "Keep captions above other windows"; Audio source "What EchoLine listens to"; Hide after silence "Fade out after 5 seconds without speech"; Click-through "Clicks pass through captions to the window below"; Start with Windows "Open EchoLine when you sign in"; model rows "Tiny — fastest, works on any PC" / "Small — more accurate, needs a faster CPU".
- [ ] **Step 4:** run `tests/test_settings_window.py tests/test_settings_parts.py tests/test_echoline_app.py tests/test_tray.py` → PASS. **Commit** — "Redesign settings as a sidebar window with live preview".

---

### Task 5: Real-display review, docs, full suite

- [ ] Script: open the real settings window (Windows platform), grab every page in dark and light (`styleHints().setColorScheme`), save PNGs; review each; fix real issues with failing-first tests where testable.
- [ ] README "Customizing": describe the new Settings (sidebar pages, live preview, follows Windows theme).
- [ ] Full `pytest -q` → green except the known worktree-only autostart failure; `graphify update .`.
- [ ] Commit — "Document the new settings window".

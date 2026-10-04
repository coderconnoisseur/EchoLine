# Settings Redesign — Design

Polish phase, part 2 of 3 (text flow → **Settings redesign** → cleanup + CPU).

## Goal

Replace the flat tabbed form with a modern, calm settings window that feels
native on Windows 11 (and fine on Windows 10): clear structure, a live preview
of the captions, and short explanations under settings.

## Decisions (agreed 2026-10-04)

| Topic | Decision |
|---|---|
| Direction | **A · Studio**: icon sidebar on the left, pages on the right |
| Light/dark | Follow the Windows app theme |
| Accent | The Windows accent colour |
| Preview | A looping sample sentence with the real word-by-word motion |
| Pages | Appearance · Position · Behavior · Speech · Shortcuts · About |

## Layout

Window 880 × 620 (minimum 760 × 520), native title bar "EchoLine Settings".

- **Sidebar** (176 px): six entries, each an icon (Segoe Fluent Icons, falling
  back to Segoe MDL2 Assets) plus a label. The selected entry has a filled
  background and a 3 px accent bar on its left. Keyboard: Up/Down move the
  selection, the sidebar takes focus first.
- **Page** (rest): a scrollable column, 24 px padding, max content width 640 px.
  A page title (20 px, semibold), then the content.

## Shared components (`echoline/ui/qml/settings/`)

- `Theme.qml` — a singleton-like object (instantiated once in the window) with
  colour tokens for dark and light: window, sidebar, card, card border,
  divider, primary/secondary text, preview backdrop. `dark` follows
  `Application.styleHints.colorScheme`; `accent` comes from the style palette.
- `SettingsCard.qml` — rounded (8 px) card with border; rows separated by a
  1 px divider.
- `SettingRow.qml` — title, optional one-line description in secondary text,
  and a control slot on the right.
- `PreviewPane.qml` — 132 px tall rounded backdrop (a soft gradient that hints
  at video), with a caption box styled exactly like the overlay (font, size,
  weight, colours, outline, background colour/opacity, corner radius) holding a
  `CaptionLine` that shows the sample.
- `ThemeGallery.qml` — four thumbnails (Classic CC, Netflix, Minimal, High
  contrast), each a mini preview of that preset's look; the active one has an
  accent outline. A "Custom" badge shows when the settings no longer match a
  preset.

## Pages and contents

| Page | Contents |
|---|---|
| Appearance | Preview · Theme gallery · **Text** card: font, size, weight, text colour, effect · **Background** card: colour, opacity, corner radius, blur behind |
| Position | Preview · **Layout** card: caption style (rolling/subtitle), lines, width · **Placement** card: snap top/center/bottom, always on top |
| Behavior | **Audio** card: source · **Visibility** card: hide after silence, click-through · **Startup** card: start with Windows |
| Speech | **Model** card: Tiny/Small with a description, download progress inline, which model is in use |
| Shortcuts | One card with the three shortcuts; same recording behaviour as today (click, press keys, Esc cancels, Backspace clears) |
| About | App name and version, the privacy promise, MIT license, GitHub link |

Every existing setting stays reachable; nothing is added or removed.

## Sample captions (`echoline/ui/sample.py`)

`SampleCaptions` owns a `CaptionModel` and a `QTimer` that replays a short
scripted sequence (words arriving, one correction, settling, a final, a pause,
repeat) — the same kind of script used for the recorded GIF. It runs only while
the Settings window is visible (`start()` / `stop()`), so it costs nothing
otherwise. Exposed to QML as `sampleCaptions`.

## Behaviour kept from today

Changes apply live (the overlay updates as you edit); `SettingsStore`
validation and saving are unchanged; the model combo still drives
`setup.chooseModel` and shows download progress; hotkey recording is unchanged;
the window is reused across opens.

## Testing

- The window loads with no QML warnings in light and dark.
- Selecting each sidebar entry shows its page; Up/Down keys move the selection.
- Every setting's control still updates the store (existing tests keep their
  `objectName`s where the control remains; the theme combo becomes gallery
  cards `theme <name>`).
- The theme gallery marks the active preset and shows "Custom" after a tweak.
- `SampleCaptions` replays its script, loops, and stops when told.
- The preview's caption box follows style settings (e.g. font size, background
  opacity).
- Real display: screenshots of every page in dark and light for review.

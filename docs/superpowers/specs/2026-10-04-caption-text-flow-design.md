# Caption Text Flow — Design

Polish phase, part 1 of 3 (text flow → Settings redesign → cleanup + CPU).

## Goal

Captions should move like Apple's Live Captions: new words arrive softly,
corrections change a word in place without a jolt, and words glide when a
line re-wraps. Today each line is one `Text` whose content is replaced on every
guess, so every update snaps.

## Decisions (agreed 2026-10-04)

| Topic | Decision |
|---|---|
| Motion | **Soft focus**: a new word fades in from a slight blur with a small upward drift; a corrected word cross-fades in place; words glide on re-wrap; lines leaving the top fade out |
| Still-changing words | **Dimmed** won the A/B. The `unsettled_words` setting and the "Hidden until settled" mode are removed |
| Reduced motion | Follow Windows "Show animations in Windows": when off, every duration is 0 |

## Architecture

### `WordModel` (Python, `echoline/captions/words.py`)

A `QAbstractListModel` of one caption line's words, roles `text` (str) and
`settled` (bool).

`update(words: list[str], settled_count: int)` compares the current words with
the new ones using `difflib.SequenceMatcher` (stdlib) and turns the opcodes
into minimal model changes:

- `equal` → nothing;
- `replace` → `dataChanged` for the overlapping span (same word item, new
  text → cross-fade), then insert or remove the length difference;
- `insert` → `beginInsertRows` (new items fade in; later words glide);
- `delete` → `beginRemoveRows`.

Opcodes are applied from the end of the list backwards so earlier indices stay
valid. Afterwards `settled` is `index < settled_count`; only rows whose flag
changed emit `dataChanged`.

`CaptionModel` keeps one `WordModel` per row (exposed through a new `words`
role and a `latestWords` property for subtitle mode). The settled count is the
number of words in the row's settled prefix. Text is still whitespace
normalised; `text`, `settled`, `latestText` and `latestSettled` stay for
onboarding's echo label and tests. Word models of dropped rows are deleted with
their row.

### `CaptionLine.qml`

A reusable item that lays out a `WordModel`:

- One delegate per word: a `Text` styled from settings (font, size, weight,
  color, outline/shadow), plus a second `Text` used only to cross-fade the
  previous text when the word changes.
- **Layout**: a JS function breaks words into rows that fit the width
  (greedy, space = font metrics width of " "), centers each row, and assigns
  each delegate a target `x`/`y`. It runs when words are inserted, removed or
  change width, or the width or font changes. `implicitHeight` = rows × line
  height. (Qt's `Flow` cannot center rows, hence the custom layout.)
- **Entry**: opacity 0 → target, `y` drifts up 6 px, and a `MultiEffect` blur
  goes 0.6 → 0, over 180 ms (`Easing.OutCubic`). The layer and effect are
  enabled only while the entry runs, so idle captions cost no extra GPU work.
- **Correction**: the old text cross-fades out while the new text fades in,
  over 160 ms.
- **Glide**: `Behavior` on `x`/`y` (220 ms, `OutCubic`), skipped for a word's
  first placement.
- **Settling**: opacity animates from 0.55 (unsettled) to 1.0 (settled) over
  200 ms.
- **Exit**: a removed word disappears at once (`Repeater` has no delayed
  removal) and only the surrounding glide is animated. Removals are rare;
  most changes arrive as corrections, which cross-fade.

### Overlay

- **Rolling mode**: the existing column of lines, each line a `CaptionLine`.
  Lines keep their `move` glide. A line partly above the top edge of the
  caption area fades out with its position instead of being cut off.
- **Subtitle mode**: `SubtitleView` shows the newest row's `CaptionLine` and
  keeps its 200 ms cross-fade between phrases (the outgoing phrase is frozen as
  plain text).
- `captions.js`, the `StyledText` markup and the "Words still changing" combo
  are removed.

### Reduced motion

`echoline/ui/motion.py`: `animations_enabled()` reads
`SystemParametersInfoW(SPI_GETCLIENTAREAANIMATION)`; it is exposed to QML as a
context property `motion` with `enabled` (bool) and `scale` (1 or 0). Every
duration in caption QML is multiplied by `motion.scale`. It is read at startup
(no live tracking; the setting rarely changes).

## Trade-offs

- A new word reaches full opacity 180 ms after it first renders. The latency
  measurement still stamps the first frame that shows the change.
- Many small items instead of one `Text`: about 40 words visible at most, so
  the cost is small; animations run on the render thread.

## Error handling

Layout tolerates empty lines (height 0, so no blank row), words wider than the
whole line (placed on their own row and clipped), and font changes mid-line
(re-layout without animation glitches: positions animate to the new layout).

## Testing

- **Unit**: `WordModel.update` — append, correction in place (same row,
  `dataChanged`), insertion in the middle, deletion, a full rewrite, and
  settled flags; signal counts are asserted so animations get the right events.
- **QML (offscreen)**: rows fit the width and are centered, words do not
  overlap, a correction keeps the same delegate item, settled words end at full
  opacity, an empty line has height 0, motion off means words appear at their
  final state immediately, and no QML warnings.
- **Real display**: record frames of a scripted sequence (append, correct,
  re-wrap, settle) and assemble a GIF to review the motion before the PR.

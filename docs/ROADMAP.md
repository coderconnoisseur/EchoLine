# EchoLine Roadmap

v1 scope and design: [specs/2026-10-03-echoline-v1-design.md](superpowers/specs/2026-10-03-echoline-v1-design.md).

## Next: after v1 ships

- **Download website** — single page with a demo clip, download buttons
  (installer and zip), a two-minute setup guide, SmartScreen explanation and
  checksums. Separate spec.

## Deferred features

Not prioritized yet; pick from this list after v1.

### Languages and text
- More languages: Moonshine multilingual streaming models where quality allows,
  Vosk models (~20 languages) as a fallback, with a language picker.
- Translation of captions into another language.
- Transliteration (e.g. Hindi speech shown in Latin script).
- Punctuation and casing improvements if the engine output needs them.

### Transcripts
- Live transcript panel with scrollable history and timestamps.
- Export transcripts (TXT, SRT, Markdown) and search past sessions.
- Speaker labels (diarization).

### Audio
- Per-app capture (only Zoom, only Chrome) via WASAPI process loopback
  (Windows 10 2004+); needs a small native helper.
- Mixing system audio and microphone (both sides of a call).

### Platform and distribution
- Code signing (e.g. Azure Trusted Signing) to remove the SmartScreen warning.
- Auto-update.
- macOS and Linux builds.

### Integrations
- Streamer / OBS mode: capture-friendly window or browser-source output.

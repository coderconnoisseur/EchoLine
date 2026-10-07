# EchoLine Roadmap

v1 scope and design: [specs/2026-10-03-echoline-v1-design.md](superpowers/specs/2026-10-03-echoline-v1-design.md).

## Next: after v1 ships

- **Download website** — single page with a demo clip, download buttons
  (installer and zip), a two-minute setup guide, SmartScreen explanation and
  checksums. Separate spec.

## Product direction (discussed 2026-10-07, not scheduled)

Goal: as many happy users as possible (free, portfolio project; launch on
Product Hunt, X, Reddit, Show HN). Plain live captions compete with Windows 11's
free built-in Live Captions, so the launch needs a hook beyond "captions".

Strongest candidates, in the order we'd explore them:

1. **Live translation into English** — e.g. a Spanish video or call with
   English subtitles, offline, on any Windows 10/11 PC (Windows only offers
   live translation on Copilot+ PCs). Moonshine already has streaming models
   for Spanish, German, Japanese, Chinese, Arabic, Vietnamese and Tagalog
   (non-commercial Moonshine Community License — fine while EchoLine is free);
   translate each finished sentence with Opus-MT via CTranslate2 (~75 MB per
   language pair, tens of ms per sentence on CPU). Show the original dimmed
   with the English line under it ("dual subtitles"). Start with a throwaway
   spike measuring delay, quality and CPU on a mid-range laptop. A demo GIF of
   this is the launch asset.
2. **Private meeting transcripts** — capture microphone and system audio
   together: mic = "You", system = "Them" gives who-said-what for any call app
   with no bot joining. Then Moonshine's built-in speaker identification
   (8 MB, `identify_speakers`) splits "Them" into speakers. Save TXT / Markdown
   / SRT with timestamps.
3. Audiences to speak to at launch: language learners (r/languagelearning,
   r/LearnJapanese), deaf and hard-of-hearing communities, people whose work
   bans cloud note-takers.

Kept out on purpose for now: AI summaries (need a cloud service or a large
local model, which breaks the private/offline promise) and macOS.

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

### Performance
- GPU acceleration (DirectML on Windows). Moonshine 0.1.5 only maps `cpu`,
  `coreml` and `nnapi` execution providers and ships a CPU-only ONNX Runtime;
  needs upstream support or a fork with a `dml` provider and a DirectML
  ONNX Runtime build. Would make the Small/Medium models usable live.

### Platform and distribution
- Code signing (e.g. Azure Trusted Signing) to remove the SmartScreen warning.
- Auto-update.
- macOS and Linux builds.

### Integrations
- Streamer / OBS mode: capture-friendly window or browser-source output.

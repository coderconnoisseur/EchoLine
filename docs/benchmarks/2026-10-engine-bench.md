# Engine benchmark — 2026-10-03

## Setup

- **Machine:** AMD Ryzen 5 3550H (4 cores / 8 threads), 14 GB RAM, Windows 10
- **Clips:** 73 LibriSpeech clean utterances, 481 s of read English speech
  (`python -m scripts.fetch_bench_clips`)
- **Method:** `python -m echoline.bench`; each clip streamed through a fresh engine
  in 50 ms chunks, Moonshine update interval 0.15 s
- **Caveat:** short test runs shared the CPU during part of the run, so speed
  figures may be slightly pessimistic

## Results

| Engine | WER | RTF | p95 per-chunk time | Worst clip RTF |
|---|---|---|---|---|
| Moonshine Tiny (streaming) | 0.130 | 0.47 | 271 ms | 0.75 |
| Moonshine Small (streaming) | 0.080 | 0.88 | 530 ms | 1.43 |
| Moonshine Medium (streaming) | 0.062 | 1.20 | 521 ms | 3.01 |
| Vosk small en-us 0.15 | 0.151 | 0.28 | 145 ms | 0.63 |

WER = word error rate (lower is better). RTF = processing time ÷ audio duration
(below 1.0 keeps up with real time). Time to first text was 1.15 s for every
engine: it reflects the leading silence in the clips, not engine speed, so it is
left out of the decision.

## Decision

- **Moonshine beats Vosk on accuracy** at every size: Tiny is 14% fewer errors,
  Small is 47% fewer, Medium 59% fewer. The engine choice stands.
- **Default model for M1: Tiny.** The plan's rule picks the most accurate model
  with RTF < 0.5 and p95 chunk time < 150 ms. No model meets the p95 bound, and
  only Tiny meets the RTF bound, so the rule falls back to Tiny. Small is
  usable (RTF 0.88) but leaves almost no headroom on this CPU and its worst clip
  ran behind real time.
- **Medium cannot run live on this class of CPU** (RTF 1.20).
- **Hardware check for M4:** time the bundled clip with Small; choose Small
  when its RTF is below **0.5**, otherwise Tiny. On this machine that selects Tiny.

## Live pipeline check (Tiny, real loopback audio)

End-to-end sound-to-screen latency measured by `--show-latency` while playing
44 s of speech through the speakers:

| Condition | p50 | p95 |
|---|---|---|
| Idle machine | **266 ms** | **438 ms** |
| Benchmark running concurrently | 300–420 ms | 550–610 ms |

On an idle machine both spec targets are met (p50 < 300 ms, p95 < 600 ms).

## Streaming lag investigation (2026-10-03)

Reported symptom: after the speaker pauses for about 2 s, captions "catch up";
during long continuous speech they fall behind the speaker.

Reproduced by streaming LibriSpeech speech in real time through `EngineWorker`
and Moonshine Tiny, logging engine time per 10 s of audio.

| Finding | Evidence |
|---|---|
| Engine time grew with **session length**, not line length | Per 10 s window: 3.9 s → 10.5 s over 70 s of continuous speech, even with lines capped at 5 s |
| Cause: every update returned all past lines with their audio (`return_audio_data` defaults to true) | With it off, engine time stays flat at 3–5 s per 10 s for 5 minutes |
| The worker then dropped speech, not just delayed it | 2 s pauses, 110 s of audio: 6.0 s dropped, p95 delay 1.45 s |
| Capping line length hurts accuracy | `vad_max_segment_duration` 5 s: WER 0.286 vs 0.132 at the default 15 s |
| One slow pass could exceed the 1 s backlog limit | Single passes of 1–2.5 s caused drops although the average is ~45% of real time |

Changes: `return_audio_data=false`, update interval 0.25 s, backlog limit 3 s,
line length left at the default.

| Speech with 2 s pauses, Tiny | Audio dropped | Delay p50 / p95 |
|---|---|---|
| Before | 6.0 s of 110 s | 359 / 1453 ms |
| After | 0 | 203 / 390–550 ms |

"Delay" is from capture of the newest audio block to the engine emitting text;
words spoken just after an update also wait for the next update (up to 0.25 s).

## Update cadence (2026-10-03)

Word lag = time from a word ending in the audio (Vosk word timestamps) to that
word appearing in the captions, measured on ~60 s of speech streamed in real
time through `EngineWorker` + Moonshine Tiny. Two runs each.

| Python / native interval | Updates per second | Word lag p90 | Lagging events |
|---|---|---|---|
| 0.25 s / 0.5 s (native default) | 1.4 | 600–660 ms | 0 |
| 0.25 s / 0.25 s | 2.5 | 360–580 ms | 0 |
| 0.15 s / 0.15 s | 3.2 | 330 ms | 0 |
| **0.1 s / 0.1 s** | **3.3** | **270–290 ms** | **0** |

The median word lag is slightly negative: Moonshine's partial text often shows
a word before it has finished being spoken.

The native `transcription_interval` was the real limit. At 0.1 s, WER stays
0.131 and the engine uses 0.77x real time (vs 0.41x), so slower CPUs have less
headroom; the worker's backlog protection and the M4 hardware check cover that.

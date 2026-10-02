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
speech through the speakers: **p50 ≈ 300–420 ms, p95 ≈ 550–610 ms**, with the
benchmark running concurrently. The p50 target (< 300 ms) is borderline on this
machine; re-measure on an idle machine before tuning the update interval.

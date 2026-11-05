# CPU usage (November 2026)

Where EchoLine's CPU goes on current code, and which levers are worth pulling.

**Setup:** Ryzen 5 3550H (4 cores, 8 threads), Windows 10, Tiny model.
`two_cities.wav` replayed in real time through the real `EngineWorker`. CPU % is
the process's share of the whole machine (100 % = all 8 threads busy).

**Caveat:** this is one PC with other work running (a WSL/Docker VM took about
21 % of the machine), so treat differences of a few points as noise. Repeating
the baseline at the start and end of the grid gave 44.0 % and 44.3 %.

## Results

**Whole app** (real overlay on screen, 45 s of speech):

| `transcription_interval` | Animations on | Animations off |
|---|---|---|
| 0.1 s (current) | 47.0 % (3.76 cores) | 43.7 % |
| 0.2 s | 41.2 % (3.29 cores) | 40.3 % |

**Engine only, batch size against interval** (30 s each). Lag is measured from
the oldest sample in the batch, so larger batches are shown at their worst case:

| Feed every | Interval | CPU | Lag p50 | Lag p95 | Updates/s |
|---|---|---|---|---|---|
| 30 ms (current) | 0.1 s | 44.0 % | 265 ms | 515 ms | 3.0 |
| 30 ms (current, repeat) | 0.1 s | 44.3 % | 233 ms | 389 ms | 3.4 |
| 100 ms | 0.1 s | 38.3 % | 334 ms | 522 ms | 2.7 |
| 200 ms | 0.1 s | 36.1 % | 419 ms | 719 ms | 2.0 |
| 300 ms | 0.1 s | 33.7 % | 518 ms | 712 ms | 2.4 |
| **30 ms** | **0.2 s** | **37.7 %** | **233 ms** | **374 ms** | **2.8** |
| 100 ms | 0.2 s | 38.2 % | 303 ms | 428 ms | 2.9 |
| 200 ms | 0.2 s | 35.4 % | 466 ms | 684 ms | 2.4 |
| 300 ms | 0.2 s | 34.4 % | 581 ms | 2272 ms | 1.3 |

**Accuracy** (first 25 clips of the engine benchmark set):

| Feed every | Interval | WER | First text |
|---|---|---|---|
| 30 ms | 0.1 s | 0.122 | 0.84 s |
| 30 ms | 0.2 s | 0.118 | 0.96 s |
| 100 ms | 0.1 s | 0.126 | 0.90 s |
| 200 ms | 0.2 s | 0.116 | 0.80 s |
| 300 ms | 0.3 s | 0.122 | 0.90 s |

**Other measurements:**

- **Silence:** 0.3 % of the machine, so skipping decoding during silence saves nothing.
- **Pinning to fewer cores:** with process affinity set to 2 logical CPUs, CPU fell
  to about 20 % but lag p50 rose above 1 s. On 1 CPU it was 11 % and about 2 s.
- **Threads:** at 3.76 cores, the engine worker used 0.68, three threads 0.58 each and
  three more 0.20 each.

## Conclusions

1. **The engine dominates.** Animations cost about 3 points at the current interval.
2. **`transcription_interval` 0.2 is the best cheap lever:** about 14 % less CPU
   in the grid (12 % in the whole app) with no measurable lag or accuracy cost.
   Updates per second drop slightly and first text came about 0.1 s later.
3. **Larger batches aren't worth it.** They trade 70–250 ms of lag for little
   extra CPU, and the 300 ms feed at 0.2 s started to fall behind.
4. **CPU has a floor of about 34 % during speech** on this PC, whatever these
   settings are. The speech worker itself is busy for about 0.7 of a core, so the
   rest looks like ONNX Runtime's thread pool. Moonshine exposes no thread or
   spinning option, so going lower needs an upstream change or our own build.
   That the pool is spin-waiting is a hypothesis, not yet confirmed.

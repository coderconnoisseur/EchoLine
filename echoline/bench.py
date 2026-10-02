"""Compare speech engines on reference clips: accuracy (WER) and speed.

Usage:
    python -m echoline.bench --clips bench_clips \
        --engines moonshine-tiny moonshine-small moonshine-medium vosk \
        --vosk-model PATH_TO_VOSK_MODEL --out bench_results.json
"""
import argparse
import json
import statistics
import time
import wave
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import numpy as np

from metrics.accuracy_evaluator import TranscriptionEvaluator

from .engine.base import SAMPLE_RATE, Final


@dataclass
class ClipResult:
    clip: str
    hypothesis: str
    wer: float
    rtf: float
    p95_feed_ms: float
    first_text_s: Optional[float]
    ref_words: int = 0
    audio_s: float = 0.0
    process_s: float = 0.0


def run_clip(engine, samples, reference, clip, chunk_ms=50) -> ClipResult:
    chunk = SAMPLE_RATE * chunk_ms // 1000
    feed_times, finals, first_text_s = [], [], None
    for index, start in enumerate(range(0, len(samples), chunk)):
        began = time.perf_counter()
        events = engine.feed(samples[start:start + chunk])
        feed_times.append(time.perf_counter() - began)
        if first_text_s is None and any(event.text for event in events):
            first_text_s = (index + 1) * chunk / SAMPLE_RATE
        finals += [event.text for event in events if isinstance(event, Final)]
    began = time.perf_counter()
    finals += [event.text for event in engine.flush()]
    process_s = sum(feed_times) + time.perf_counter() - began

    hypothesis = " ".join(text for text in finals if text)
    metrics = TranscriptionEvaluator().evaluate_transcription(reference, hypothesis)
    audio_s = len(samples) / SAMPLE_RATE
    p95 = float(np.percentile(feed_times, 95)) * 1000 if feed_times else 0.0
    return ClipResult(clip, hypothesis, metrics.word_error_rate, process_s / max(audio_s, 1e-9),
                      p95, first_text_s, metrics.total_words, audio_s, process_s)


def summarize(results) -> dict:
    ref_words = sum(r.ref_words for r in results)
    first_texts = [r.first_text_s for r in results if r.first_text_s is not None]
    return {
        "wer": sum(r.wer * r.ref_words for r in results) / max(ref_words, 1),
        "rtf": sum(r.process_s for r in results) / max(sum(r.audio_s for r in results), 1e-9),
        "p95_feed_ms": max((r.p95_feed_ms for r in results), default=0.0),
        "first_text_s": statistics.median(first_texts) if first_texts else None,
    }


def load_clip(wav_path: Path) -> np.ndarray:
    with wave.open(str(wav_path)) as wav:
        pcm = np.frombuffer(wav.readframes(wav.getnframes()), dtype=np.int16)
    return pcm.astype(np.float32) / 32768


def make_engine(name, vosk_model):
    if name == "vosk":
        from .engine.vosk_engine import VoskEngine
        return VoskEngine.load(vosk_model)
    from moonshine_voice import ModelArch
    from .engine.moonshine_engine import MoonshineEngine
    arch = {"moonshine-tiny": ModelArch.TINY_STREAMING,
            "moonshine-small": ModelArch.SMALL_STREAMING,
            "moonshine-medium": ModelArch.MEDIUM_STREAMING}[name]
    return MoonshineEngine.load(arch)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--clips", type=Path, default=Path("bench_clips"))
    parser.add_argument("--engines", nargs="+", default=["moonshine-tiny", "moonshine-small"])
    parser.add_argument("--vosk-model", default=None)
    parser.add_argument("--out", type=Path, default=Path("bench_results.json"))
    args = parser.parse_args()

    clips = sorted(args.clips.glob("*.wav"))
    report = {}
    print(f"{'engine':<18}{'WER':>8}{'RTF':>8}{'p95 feed ms':>13}{'first text s':>14}")
    for name in args.engines:
        results = []
        for wav_path in clips:
            engine = make_engine(name, args.vosk_model)   # fresh engine: no state between clips
            reference = wav_path.with_suffix(".txt").read_text()
            results.append(run_clip(engine, load_clip(wav_path), reference, wav_path.stem))
        summary = summarize(results)
        report[name] = {"summary": summary, "clips": [asdict(r) for r in results]}
        first = summary["first_text_s"]
        print(f"{name:<18}{summary['wer']:>8.3f}{summary['rtf']:>8.3f}"
              f"{summary['p95_feed_ms']:>13.1f}{(first if first is not None else float('nan')):>14.2f}")
    args.out.write_text(json.dumps(report, indent=2))
    print(f"Full results: {args.out}")


if __name__ == "__main__":
    main()

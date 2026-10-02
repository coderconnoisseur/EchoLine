import numpy as np
import pytest

from echoline.bench import ClipResult, run_clip, summarize
from echoline.engine.base import Final, Partial


class ScriptedEngine:
    """Emits a partial after the 2nd chunk and a final on flush."""

    def __init__(self, text):
        self.text = text
        self.calls = 0

    def feed(self, samples):
        self.calls += 1
        return [Partial(0, self.text.split()[0])] if self.calls == 2 else []

    def flush(self):
        return [Final(0, self.text)]


def test_run_clip_scores_hypothesis_against_reference():
    samples = np.zeros(16000, dtype=np.float32)   # 1 s of audio, 20 chunks of 50 ms

    result = run_clip(ScriptedEngine("hello there world"), samples, "hello big world", clip="c1")

    assert result.clip == "c1"
    assert result.hypothesis == "hello there world"
    assert result.wer == pytest.approx(1 / 3)
    assert result.first_text_s == pytest.approx(0.1)
    assert result.rtf >= 0


def test_no_output_means_no_first_text_and_full_error():
    class Silent:
        def feed(self, samples):
            return []

        def flush(self):
            return []

    result = run_clip(Silent(), np.zeros(1600, np.float32), "two words", clip="c2")

    assert result.first_text_s is None
    assert result.wer == 1.0


def test_summary_weights_wer_by_reference_length():
    results = [
        ClipResult("a", "", wer=1.0, rtf=0.2, p95_feed_ms=10, first_text_s=0.5, ref_words=1, audio_s=1, process_s=0.2),
        ClipResult("b", "", wer=0.0, rtf=0.4, p95_feed_ms=30, first_text_s=None, ref_words=3, audio_s=3, process_s=1.2),
    ]

    summary = summarize(results)

    assert summary["wer"] == pytest.approx(0.25)
    assert summary["rtf"] == pytest.approx(1.4 / 4)
    assert summary["p95_feed_ms"] == 30
    assert summary["first_text_s"] == pytest.approx(0.5)


def test_each_engine_is_closed_after_its_clip(tmp_path):
    # Loading a fresh model per clip without closing it leaked ~5 GB of native memory.
    import wave

    from echoline.bench import bench_engine

    for name in ("a", "b"):
        with wave.open(str(tmp_path / f"{name}.wav"), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(np.zeros(1600, np.int16).tobytes())
        (tmp_path / f"{name}.txt").write_text("hello")

    engines = []

    class ClosableEngine(ScriptedEngine):
        closed = False

        def close(self):
            self.closed = True

    def make():
        engines.append(ClosableEngine("hello"))
        return engines[-1]

    results = bench_engine(make, sorted(tmp_path.glob("*.wav")))

    assert [r.clip for r in results] == ["a", "b"]
    assert all(engine.closed for engine in engines)

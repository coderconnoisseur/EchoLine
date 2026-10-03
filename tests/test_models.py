import time

import moonshine_voice
import numpy as np

from echoline import models
from echoline.engine.base import SAMPLE_RATE


def test_models_live_under_local_appdata(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert models.models_dir() == tmp_path / "EchoLine" / "models"


def test_is_downloaded_needs_every_file_at_full_size(tmp_path):
    files = models._files("tiny", tmp_path)
    assert files and not models.is_downloaded("tiny", tmp_path)
    for path, size in files:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.truncate(size)            # sparse: instant even for 40 MB
    assert models.is_downloaded("tiny", tmp_path)

    path, size = files[0]
    with open(path, "wb") as f:
        f.truncate(size - 1)            # a cut-off download
    assert not models.is_downloaded("tiny", tmp_path)


def test_download_uses_our_folder_and_reports_progress(monkeypatch, tmp_path):
    calls = []

    def fake(language, model_arch, cache_root=None, on_progress=None):
        calls.append((language, model_arch, cache_root))
        on_progress(0.5, "encoder.ort")
        return "model-path", model_arch

    monkeypatch.setattr(moonshine_voice, "get_model_for_language", fake)
    seen = []
    assert models.download("small", seen.append, root=tmp_path) == "model-path"
    assert calls == [("en", models.arch("small"), tmp_path)]
    assert seen == [0.5]


def test_choose_model_takes_small_only_when_tiny_has_lots_of_headroom():
    assert models.choose_model(0.20) == "small"
    assert models.choose_model(0.25) == "small"
    assert models.choose_model(0.26) == "tiny"
    assert models.choose_model(0.77) == "tiny"     # this Ryzen 5 3550H


class SlowEngine:
    def __init__(self, per_chunk_s):
        self.per_chunk_s, self.fed, self.flushed, self.closed = per_chunk_s, 0, False, False

    def feed(self, samples):
        self.fed += len(samples)
        time.sleep(self.per_chunk_s)
        return []

    def flush(self):
        self.flushed = True
        return []

    def close(self):
        self.closed = True


def test_measure_rtf_feeds_everything_and_times_it():
    engine = SlowEngine(0.01)                      # 10 ms per 50 ms chunk ~ 0.2
    samples = np.zeros(SAMPLE_RATE, np.float32)    # 1 s -> 20 chunks
    rtf = models.measure_rtf(engine, samples)
    assert engine.fed == SAMPLE_RATE and engine.flushed
    assert 0.18 <= rtf < 0.5


def test_check_clip_is_15_seconds_of_16khz_audio():
    clip = models.check_clip()
    assert clip.dtype == np.float32 and len(clip) == 15 * SAMPLE_RATE
    assert np.abs(clip).max() > 0.05               # real speech, not padding


def test_check_hardware_closes_the_engine(monkeypatch):
    engine = SlowEngine(0)
    monkeypatch.setattr(models, "check_clip", lambda seconds=15: np.zeros(1600, np.float32))
    assert models.check_hardware(load=lambda: engine) == "small"
    assert engine.closed

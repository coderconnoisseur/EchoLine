import time
from pathlib import Path

import moonshine_voice
import numpy as np
import pytest

from echoline import models
from echoline.engine.base import SAMPLE_RATE


def test_models_live_under_local_appdata(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert models.models_dir() == tmp_path / "EchoLine" / "models"


def fill_with_zeros(name, root):
    """Every file at its full size but zero-filled, as a crash mid-write can leave it."""
    for path, size, _ in models._files(name, root):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.truncate(size)


def test_missing_or_damaged_files_are_not_downloaded(tmp_path):
    assert not models.is_downloaded("tiny", tmp_path)
    fill_with_zeros("tiny", tmp_path)                 # right sizes, wrong contents
    assert not models.is_downloaded("tiny", tmp_path)


def test_a_real_model_counts_as_downloaded():
    from moonshine_voice.download_file import get_cache_dir

    if not (Path(get_cache_dir()) / "download.moonshine.ai" / "model" / "tiny-streaming-en").exists():
        pytest.skip("Tiny is not in moonshine's own cache on this machine")
    assert models.is_downloaded("tiny", get_cache_dir())


def test_download_replaces_damaged_files(monkeypatch, tmp_path):
    # moonshine skips a file of the right size without checking it, so a damaged
    # file would never be fetched again and the model would never load.
    fill_with_zeros("tiny", tmp_path)
    seen = []

    def fake(language, model_arch, cache_root=None, on_progress=None):
        seen.extend(path.exists() for path, _, _ in models._files("tiny", cache_root))
        return "model-path", model_arch

    monkeypatch.setattr(moonshine_voice, "get_model_for_language", fake)
    models.download("tiny", root=tmp_path)
    assert seen and not any(seen)


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


def test_models_dir_is_ascii_even_for_non_english_user_names(monkeypatch, tmp_path):
    # Moonshine's native loader cannot open paths with non-ASCII characters, so a
    # user named José got "Speech model unavailable" on every launch.
    profile = tmp_path / "José" / "AppData" / "Local"
    monkeypatch.setenv("LOCALAPPDATA", str(profile))
    monkeypatch.setenv("PROGRAMDATA", str(tmp_path / "ProgramData"))
    path = models.models_dir()
    assert str(path).isascii(), path
    path.mkdir(parents=True, exist_ok=True)
    assert path.is_dir()

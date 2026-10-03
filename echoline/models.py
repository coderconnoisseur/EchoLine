"""Speech model files: where they live, whether they are complete, fetching them.

moonshine-voice already downloads with resume, size + CRC32C checks and atomic
rename; this module only points it at EchoLine's folder and adapts progress.
"""
import os
import time
from pathlib import Path

import numpy as np


def models_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "EchoLine" / "models"


def arch(name):
    from moonshine_voice import ModelArch

    return {"tiny": ModelArch.TINY_STREAMING, "small": ModelArch.SMALL_STREAMING,
            "medium": ModelArch.MEDIUM_STREAMING}[name]


def _files(name, root):
    """(path, expected size) for each file of the model, from the native manifest (offline)."""
    from moonshine_voice.download import _primary_stt_group, find_model_info

    group = _primary_stt_group(find_model_info("en", arch(name)))
    base = Path(root) / group["base_url"].replace("https://", "")
    return [(base / f["name"], f.get("size")) for f in group["files"]]


def is_downloaded(name, root=None) -> bool:
    return all(path.is_file() and (size is None or path.stat().st_size == size)
               for path, size in _files(name, root or models_dir()))


def download(name, on_progress=None, root=None) -> str:
    """Fetch (or resume) the model; blocks, so call it off the GUI thread."""
    import moonshine_voice

    progress = (lambda fraction, _file: on_progress(fraction)) if on_progress else None
    path, _ = moonshine_voice.get_model_for_language(
        "en", arch(name), cache_root=root or models_dir(), on_progress=progress)
    return path


# Small costs ~1.9x Tiny (M0 bench: RTF 0.88 vs 0.47), so Tiny at <= 0.25 keeps Small under 0.5.
# ponytail: calibrated on one Ryzen 5 3550H; retune from real-world reports.
SMALL_IF_TINY_RTF_AT_MOST = 0.25


def choose_model(tiny_rtf) -> str:
    return "small" if tiny_rtf <= SMALL_IF_TINY_RTF_AT_MOST else "tiny"


def check_clip(seconds=15):
    """The first `seconds` of moonshine's bundled speech clip, as 16 kHz mono float32."""
    from moonshine_voice import get_assets_path, load_wav_file

    from .audio.convert import TARGET_RATE, StreamConverter

    audio, rate = load_wav_file(os.path.join(get_assets_path(), "two_cities.wav"))
    converter = StreamConverter(rate, 1)
    # The trailing second of silence pushes the resampler's delayed tail out.
    samples = np.concatenate([converter.process(np.asarray(audio[: seconds * rate], np.float32)),
                              converter.process(np.zeros(rate, np.float32))])
    return samples[: seconds * TARGET_RATE]


def measure_rtf(engine, samples) -> float:
    """Processing time / audio time, feeding 50 ms chunks as fast as the engine takes them."""
    from .engine.base import SAMPLE_RATE

    chunk = SAMPLE_RATE // 20
    start = time.perf_counter()
    for i in range(0, len(samples), chunk):
        engine.feed(samples[i:i + chunk])
    engine.flush()
    return (time.perf_counter() - start) / (len(samples) / SAMPLE_RATE)


def check_hardware(load=None) -> str:
    """Time Tiny on the bundled clip and pick the model this PC can keep up with."""
    if load is None:
        from .engine.moonshine_engine import MoonshineEngine

        def load():
            return MoonshineEngine.load(arch("tiny"), cache_root=models_dir())
    engine = load()
    try:
        return choose_model(measure_rtf(engine, check_clip()))
    finally:
        engine.close()

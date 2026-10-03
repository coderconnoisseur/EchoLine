"""Speech model files: where they live, whether they are complete, fetching them.

moonshine-voice already downloads with resume, size + CRC32C checks and atomic
rename; this module only points it at EchoLine's folder and adapts progress.
"""
import os
from pathlib import Path


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

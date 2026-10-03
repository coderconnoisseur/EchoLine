import moonshine_voice

from echoline import models


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

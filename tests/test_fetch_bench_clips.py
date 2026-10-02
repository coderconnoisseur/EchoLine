import io
import wave

import numpy as np
import soundfile as sf

from scripts.fetch_bench_clips import write_clips


def flac_bytes(samples, rate):
    buffer = io.BytesIO()
    sf.write(buffer, samples, rate, format="FLAC")
    return buffer.getvalue()


def test_clips_are_written_as_16khz_wav_with_lowercase_text(tmp_path):
    tone = (0.3 * np.sin(np.linspace(0, 200, 8000))).astype(np.float32)
    rows = [{"id": "1272-128104-0000", "text": "MISTER QUILTER IS", "audio_bytes": flac_bytes(tone, 8000)}]

    count = write_clips(rows, tmp_path)

    assert count == 1
    assert (tmp_path / "1272-128104-0000.txt").read_text() == "mister quilter is"
    with wave.open(str(tmp_path / "1272-128104-0000.wav")) as wav:
        assert wav.getframerate() == 16000
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert abs(wav.getnframes() - 16000) <= 1

"""Download LibriSpeech sample clips (73 utterances, ~9 MB) for the engine benchmark.

Usage: python -m scripts.fetch_bench_clips [--out bench_clips]
"""
import argparse
import io
import wave
from pathlib import Path

import librosa
import numpy as np

PARQUET_URL = (
    "https://huggingface.co/api/datasets/hf-internal-testing/"
    "librispeech_asr_dummy/parquet/clean/validation/0.parquet"
)


def write_clips(rows, out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for row in rows:
        samples, _ = librosa.load(io.BytesIO(row["audio_bytes"]), sr=16000, mono=True)
        pcm = np.clip(np.round(samples * 32768), -32768, 32767).astype(np.int16)
        with wave.open(str(out_dir / f"{row['id']}.wav"), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(pcm.tobytes())
        (out_dir / f"{row['id']}.txt").write_text(row["text"].lower())
        count += 1
    return count


def download_rows():
    import pyarrow.parquet as pq
    import requests

    response = requests.get(PARQUET_URL, timeout=120)
    response.raise_for_status()
    table = pq.read_table(io.BytesIO(response.content), columns=["id", "text", "audio"])
    for record in table.to_pylist():
        yield {"id": record["id"], "text": record["text"], "audio_bytes": record["audio"]["bytes"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="bench_clips", type=Path)
    args = parser.parse_args()
    print(f"Wrote {write_clips(download_rows(), args.out)} clips to {args.out}")


if __name__ == "__main__":
    main()

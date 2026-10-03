import numpy as np
import soxr

TARGET_RATE = 16000


class StreamConverter:
    """Turns device audio (any rate, any channel count) into 16 kHz mono float32."""

    def __init__(self, in_rate: int, channels: int):
        self.channels = channels
        self._resampler = None if in_rate == TARGET_RATE else soxr.ResampleStream(
            in_rate, TARGET_RATE, 1, dtype="float32", quality="HQ")

    def process(self, block: np.ndarray) -> np.ndarray:
        samples = block.astype(np.float32) / 32768 if block.dtype == np.int16 else block.astype(np.float32, copy=False)
        if self.channels > 1:
            samples = samples.reshape(-1, self.channels).mean(axis=1)
        else:
            samples = samples.reshape(-1)
        if self._resampler is None:
            return samples
        return self._resampler.resample_chunk(samples)

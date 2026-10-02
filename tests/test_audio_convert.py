import numpy as np
import pytest

from echoline.audio.convert import StreamConverter


def stereo_sine(rate, seconds, freq=440, amplitude=0.5):
    t = np.arange(int(rate * seconds)) / rate
    mono = amplitude * np.sin(2 * np.pi * freq * t)
    return np.stack([mono, mono], axis=1).astype(np.float32)


def test_48k_stereo_float_becomes_16k_mono():
    converter = StreamConverter(in_rate=48000, channels=2)

    out = np.concatenate([converter.process(block) for block in np.array_split(stereo_sine(48000, 1.0), 50)])

    assert out.dtype == np.float32
    assert abs(len(out) - 16000) < 400            # streaming resampler holds back a few ms
    assert np.max(np.abs(out[2000:-2000])) == pytest.approx(0.5, abs=0.02)


def test_int16_input_is_scaled_to_unit_range():
    converter = StreamConverter(in_rate=16000, channels=1)
    block = np.full(1600, 16384, dtype=np.int16)

    out = converter.process(block)

    assert out.dtype == np.float32
    assert np.allclose(out, 0.5, atol=1e-3)


def test_16k_mono_passes_through_unchanged():
    converter = StreamConverter(in_rate=16000, channels=1)
    block = np.linspace(-1, 1, 800, dtype=np.float32)

    assert np.array_equal(converter.process(block), block)


def test_flat_interleaved_input_is_accepted():
    converter = StreamConverter(in_rate=16000, channels=2)
    interleaved = np.array([0.2, 0.4, 0.6, 0.8], dtype=np.float32)   # two stereo frames

    assert np.allclose(converter.process(interleaved), [0.3, 0.7])

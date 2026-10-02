import threading
import time

import numpy as np

from .base import AudioCallback, StatusCallback
from .convert import StreamConverter


class LoopbackSource:
    """Captures whatever plays on the default output device via WASAPI loopback."""

    name = "System audio"

    def __init__(self, pyaudio_module=None, poll_interval=2.0, block_ms=30):
        if pyaudio_module is None:
            import pyaudiowpatch as pyaudio_module
        self._pyaudio = pyaudio_module
        self._poll_interval = poll_interval
        self._block_ms = block_ms
        self._audio = None
        self._stream = None
        self._device_index = None
        self.last_audio_at = time.monotonic()
        self._stopping = threading.Event()
        self._lock = threading.Lock()

    def start(self, on_audio: AudioCallback, on_status: StatusCallback) -> None:
        self._on_audio, self._on_status = on_audio, on_status
        self._audio = self._pyaudio.PyAudio()
        self._stopping.clear()
        self.check_device()
        if self._poll_interval:
            threading.Thread(target=self._poll, daemon=True).start()
            threading.Thread(target=self._fill_silence_loop, daemon=True).start()

    def _poll(self):
        while not self._stopping.wait(self._poll_interval):
            self.check_device()

    def _fill_silence_loop(self):
        while not self._stopping.wait(self._block_ms / 1000):
            self.fill_silence()

    def fill_silence(self, now=None):
        """Emit a block of zeros when the device has gone quiet.

        WASAPI loopback delivers nothing while nothing plays, but engines need
        to hear silence to decide a sentence has ended.
        """
        now = time.monotonic() if now is None else now
        if self._stream is None or now - self.last_audio_at < 2 * self._block_ms / 1000:
            return
        self.last_audio_at = now
        self._on_audio(np.zeros(16 * self._block_ms, dtype=np.float32), now)

    def check_device(self):
        """Open the default loopback device, reopening if it changed."""
        try:
            device = self._audio.get_default_wasapi_loopback()
        except OSError:
            device = None
        with self._lock:
            if device is None:
                if self._device_index is not None or self._stream is None:
                    self._close_stream()
                    self._device_index = None
                    self._on_status("no-device")
                return
            if device["index"] == self._device_index:
                return
            self._close_stream()
            self._open(device)

    def _open(self, device):
        rate = int(device["defaultSampleRate"])
        channels = int(device["maxInputChannels"])
        converter = StreamConverter(rate, channels)

        def callback(data, frame_count, time_info, status):
            captured_at = self.last_audio_at = time.monotonic()
            samples = converter.process(np.frombuffer(data, dtype=np.int16))
            if len(samples):
                self._on_audio(samples, captured_at)
            return (None, self._pyaudio.paContinue)

        self._stream = self._audio.open(
            format=self._pyaudio.paInt16, channels=channels, rate=rate, input=True,
            input_device_index=device["index"], frames_per_buffer=rate * self._block_ms // 1000,
            stream_callback=callback)
        self._stream.start_stream()
        self._device_index = device["index"]
        self._on_status("listening")

    def _close_stream(self):
        if self._stream is not None:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None

    def stop(self) -> None:
        self._stopping.set()
        with self._lock:
            self._close_stream()
            self._device_index = None
        if self._audio is not None:
            self._audio.terminate()
            self._audio = None

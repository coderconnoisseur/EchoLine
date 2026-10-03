import threading
import time
import traceback

import numpy as np

from .base import AudioCallback, StatusCallback
from .convert import StreamConverter


def windows_default_output_id():
    """Id of the current default playback endpoint, or None when there is none.

    PortAudio snapshots the device list when it initialises, so it cannot tell
    us when the default changes; Windows Core Audio can.
    """
    import comtypes
    from pycaw.pycaw import AudioUtilities

    comtypes.CoInitialize()
    try:
        return AudioUtilities.GetSpeakers().id
    except Exception:
        return None
    finally:
        comtypes.CoUninitialize()


class LoopbackSource:
    """Captures whatever plays on the default output device via WASAPI loopback."""

    name = "System audio"

    def __init__(self, pyaudio_module=None, default_device_id=None, poll_interval=2.0,
                 block_ms=30, silence_gap_ms=150):
        if pyaudio_module is None:
            import pyaudiowpatch as pyaudio_module
        self._pyaudio = pyaudio_module
        self._default_device_id = default_device_id or windows_default_output_id
        self._poll_interval = poll_interval
        self._block_ms = block_ms
        self._silence_gap = silence_gap_ms / 1000
        self._audio = None
        self._stream = None
        self._device_id = None
        self._status = None
        self.last_audio_at = time.monotonic()
        self._stopping = threading.Event()
        self._lock = threading.Lock()

    def start(self, on_audio: AudioCallback, on_status: StatusCallback) -> None:
        self._on_audio, self._on_status = on_audio, on_status
        self._stopping.clear()
        self.check_device()
        if self._poll_interval:
            threading.Thread(target=self._poll, name="loopback-poll", daemon=True).start()
            threading.Thread(target=self._fill_silence_loop, name="loopback-silence", daemon=True).start()

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
        if self._stream is None or now - self.last_audio_at < self._silence_gap:
            return
        self.last_audio_at = now - self._silence_gap + self._block_ms / 1000
        self._on_audio(np.zeros(16 * self._block_ms, dtype=np.float32), now)

    def _set_status(self, status):
        if status != self._status:
            self._status = status
            self._on_status(status)

    def check_device(self):
        """(Re)open the default device's loopback stream when it changed or stopped."""
        with self._lock:
            if self._stopping.is_set():
                return
            try:
                device_id = self._default_device_id()
            except Exception:
                device_id = None
            if device_id is None:
                self._close()
                self._device_id = None
                self._set_status("no-device")
                return
            if device_id == self._device_id and self._stream is not None and self._stream.is_active():
                return
            self._close()
            try:
                # A fresh PortAudio instance is the only way it sees device changes.
                self._audio = self._pyaudio.PyAudio()
                self._open(self._audio.get_default_wasapi_loopback())
            except Exception:
                traceback.print_exc()
                self._close()
                self._device_id = None
                self._set_status("no-device")
                return
            self._device_id = device_id
            self._set_status("listening")

    def _open(self, device):
        rate = int(device["defaultSampleRate"])
        channels = int(device["maxInputChannels"])
        converter = StreamConverter(rate, channels)

        def callback(data, frame_count, time_info, status):
            try:
                captured_at = self.last_audio_at = time.monotonic()
                samples = converter.process(np.frombuffer(data, dtype=np.int16))
                if len(samples):
                    self._on_audio(samples, captured_at)
            except Exception:
                traceback.print_exc()     # returning normally keeps the stream alive
            return (None, self._pyaudio.paContinue)

        self._stream = self._audio.open(
            format=self._pyaudio.paInt16, channels=channels, rate=rate, input=True,
            input_device_index=device["index"], frames_per_buffer=rate * self._block_ms // 1000,
            stream_callback=callback)
        self._stream.start_stream()

    def _close(self):
        if self._stream is not None:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                traceback.print_exc()
            self._stream = None
        if self._audio is not None:
            self._audio.terminate()
            self._audio = None

    def stop(self) -> None:
        with self._lock:
            self._stopping.set()
            self._close()
            self._device_id = None

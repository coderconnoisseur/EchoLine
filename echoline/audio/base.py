from typing import Callable, Protocol

import numpy as np

AudioCallback = Callable[[np.ndarray, float], None]   # (16 kHz mono float32, time.monotonic() at capture)
StatusCallback = Callable[[str], None]                 # "listening" | "no-device"


class AudioSource(Protocol):
    name: str

    def start(self, on_audio: AudioCallback, on_status: StatusCallback) -> None: ...

    def stop(self) -> None: ...

import threading

import numpy as np

from audio.capture import AudioCapture


def test_captured_audio_is_delivered_to_callback_as_bytes():
    received = []
    delivered = threading.Event()

    def on_audio(data):
        received.append(data)
        delivered.set()

    capture = AudioCapture(callback=on_audio)
    capture.is_capturing = True
    worker = threading.Thread(target=capture.process_audio_queue, daemon=True)
    worker.start()

    capture.audio_callback(np.array([[1], [2]], dtype=np.int16), 2, None, None)

    assert delivered.wait(timeout=2)
    assert received == [np.array([1, 2], dtype=np.int16).tobytes()]
    capture.stop()
    worker.join(timeout=2)
    assert not worker.is_alive()


def test_stop_without_start_is_safe():
    assert AudioCapture().stop() is True

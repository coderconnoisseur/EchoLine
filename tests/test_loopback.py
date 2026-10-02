import numpy as np

from echoline.audio.loopback import LoopbackSource


class FakeStream:
    def __init__(self, callback):
        self.callback = callback
        self.closed = False

    def start_stream(self):
        pass

    def stop_stream(self):
        pass

    def close(self):
        self.closed = True


class FakePyAudio:
    paContinue = 0
    paInt16 = 8

    def __init__(self, devices):
        self.devices = devices            # list of device dicts; first is default, [] = none
        self.streams = []

    def PyAudio(self):
        return self

    def get_default_wasapi_loopback(self):
        if not self.devices:
            raise OSError("no loopback device")
        return self.devices[0]

    def open(self, **kwargs):
        stream = FakeStream(kwargs["stream_callback"])
        stream.kwargs = kwargs
        self.streams.append(stream)
        return stream

    def terminate(self):
        pass


SPEAKERS = {"index": 24, "name": "Speakers [Loopback]", "maxInputChannels": 2, "defaultSampleRate": 48000.0}
HEADPHONES = {"index": 31, "name": "Headphones [Loopback]", "maxInputChannels": 2, "defaultSampleRate": 44100.0}


def start(source):
    received, statuses = [], []
    source.start(lambda samples, captured_at: received.append(samples), statuses.append)
    return received, statuses


def test_opens_default_loopback_and_delivers_16khz_mono():
    fake = FakePyAudio([SPEAKERS])
    source = LoopbackSource(pyaudio_module=fake, poll_interval=None)
    received, statuses = start(source)

    stream = fake.streams[0]
    assert stream.kwargs["input_device_index"] == 24
    assert stream.kwargs["rate"] == 48000 and stream.kwargs["channels"] == 2
    frames = np.full((4800, 2), 8192, dtype=np.int16)              # 100 ms of stereo
    stream.callback(frames.tobytes(), 4800, None, 0)
    assert statuses == ["listening"]
    total = sum(len(chunk) for chunk in received)
    assert 1200 <= total <= 1600                                    # ~100 ms at 16 kHz
    assert np.allclose(np.concatenate(received)[-200:], 0.25, atol=0.02)


def test_reopens_when_default_device_changes():
    fake = FakePyAudio([SPEAKERS])
    source = LoopbackSource(pyaudio_module=fake, poll_interval=None)
    start(source)

    fake.devices = [HEADPHONES]
    source.check_device()

    assert fake.streams[0].closed
    assert fake.streams[1].kwargs["input_device_index"] == 31
    assert fake.streams[1].kwargs["rate"] == 44100


def test_reports_missing_device_and_retries():
    fake = FakePyAudio([])
    source = LoopbackSource(pyaudio_module=fake, poll_interval=None)
    _, statuses = start(source)

    assert statuses == ["no-device"]
    fake.devices = [SPEAKERS]
    source.check_device()
    assert statuses == ["no-device", "listening"]
    assert len(fake.streams) == 1


def test_stop_closes_the_stream():
    fake = FakePyAudio([SPEAKERS])
    source = LoopbackSource(pyaudio_module=fake, poll_interval=None)
    start(source)

    source.stop()

    assert fake.streams[0].closed


def test_fills_silence_when_device_sends_nothing():
    # WASAPI loopback delivers no packets while nothing plays; engines need
    # silence to notice a sentence ended, so the source supplies it.
    fake = FakePyAudio([SPEAKERS])
    source = LoopbackSource(pyaudio_module=fake, poll_interval=None, block_ms=30)
    received, _ = start(source)

    source.fill_silence(now=source.last_audio_at + 0.1)

    assert len(received) == 1
    assert len(received[0]) == 480 and not received[0].any()


def test_no_silence_is_added_while_audio_is_flowing():
    fake = FakePyAudio([SPEAKERS])
    source = LoopbackSource(pyaudio_module=fake, poll_interval=None, block_ms=30)
    received, _ = start(source)

    source.fill_silence(now=source.last_audio_at + 0.01)

    assert received == []


def test_no_silence_without_an_open_device():
    fake = FakePyAudio([])
    source = LoopbackSource(pyaudio_module=fake, poll_interval=None)
    received, _ = start(source)

    source.fill_silence(now=1e9)

    assert received == []

import numpy as np

from echoline.audio.loopback import LoopbackSource


class FakeStream:
    def __init__(self, callback):
        self.callback = callback
        self.closed = False
        self.active = True

    def start_stream(self):
        pass

    def stop_stream(self):
        pass

    def is_active(self):
        return self.active and not self.closed

    def close(self):
        self.closed = True


class FakePyAudio:
    """Stands in for pyaudiowpatch. Like PortAudio, each PyAudio() snapshots the default device."""
    paContinue = 0
    paInt16 = 8

    def __init__(self, devices):
        self.devices = devices            # list of device dicts; first is default, [] = none
        self.streams = []
        self.instances = 0
        self.terminated = 0
        self.open_error = None

    def PyAudio(self):
        self.instances += 1
        return FakeInstance(self, list(self.devices))


class FakeInstance:
    def __init__(self, module, devices):
        self.module = module
        self.devices = devices

    def get_default_wasapi_loopback(self):
        if not self.devices:
            raise LookupError("no loopback device")
        return self.devices[0]

    def open(self, **kwargs):
        if self.module.open_error:
            raise self.module.open_error
        stream = FakeStream(kwargs["stream_callback"])
        stream.kwargs = kwargs
        self.module.streams.append(stream)
        return stream

    def terminate(self):
        self.module.terminated += 1


SPEAKERS = {"index": 24, "name": "Speakers [Loopback]", "maxInputChannels": 2, "defaultSampleRate": 48000.0}
HEADPHONES = {"index": 31, "name": "Headphones [Loopback]", "maxInputChannels": 2, "defaultSampleRate": 44100.0}


class Default:
    """The Windows default output endpoint id, as the OS reports it right now."""

    def __init__(self, endpoint):
        self.endpoint = endpoint

    def __call__(self):
        return self.endpoint


def make(devices, endpoint="speakers", **kwargs):
    fake, default = FakePyAudio(devices), Default(endpoint)
    source = LoopbackSource(pyaudio_module=fake, default_device_id=default, poll_interval=None, **kwargs)
    return source, fake, default


def start(source):
    received, statuses = [], []
    source.start(lambda samples, captured_at: received.append(samples), statuses.append)
    return received, statuses


def test_opens_default_loopback_and_delivers_16khz_mono():
    source, fake, _ = make([SPEAKERS])
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
    source, fake, default = make([SPEAKERS])
    start(source)

    fake.devices, default.endpoint = [HEADPHONES], "headphones"
    source.check_device()

    assert fake.streams[0].closed
    assert fake.terminated == 1 and fake.instances == 2         # PortAudio re-initialised to see the new device
    assert fake.streams[1].kwargs["input_device_index"] == 31
    assert fake.streams[1].kwargs["rate"] == 44100


def test_unchanged_device_is_left_alone():
    source, fake, _ = make([SPEAKERS])
    start(source)

    source.check_device()

    assert len(fake.streams) == 1 and fake.instances == 1


def test_reports_missing_device_and_retries():
    source, fake, default = make([], endpoint=None)
    _, statuses = start(source)

    assert statuses == ["no-device"]
    source.check_device()
    assert statuses == ["no-device"]                            # reported once, not every poll
    fake.devices, default.endpoint = [SPEAKERS], "speakers"
    source.check_device()
    assert statuses == ["no-device", "listening"]
    assert len(fake.streams) == 1


def test_open_failure_reports_no_device_and_keeps_retrying():
    source, fake, _ = make([SPEAKERS])
    fake.open_error = OSError("device in exclusive use")
    _, statuses = start(source)

    assert statuses == ["no-device"]
    fake.open_error = None
    source.check_device()
    assert statuses == ["no-device", "listening"]


def test_stream_that_stopped_on_its_own_is_reopened():
    source, fake, _ = make([SPEAKERS])
    start(source)

    fake.streams[0].active = False                              # e.g. the device was reset
    source.check_device()

    assert len(fake.streams) == 2 and not fake.streams[1].closed


def test_callback_errors_do_not_stop_the_stream():
    source, fake, _ = make([SPEAKERS])

    def broken(samples, captured_at):
        raise RuntimeError("consumer bug")

    source.start(broken, lambda status: None)

    result = fake.streams[0].callback(np.zeros(960, np.int16).tobytes(), 480, None, 0)

    assert result == (None, fake.paContinue)


def test_stop_closes_the_stream_and_ignores_later_polls():
    source, fake, _ = make([SPEAKERS])
    start(source)

    source.stop()
    source.check_device()

    assert fake.streams[0].closed
    assert len(fake.streams) == 1


def test_fills_silence_when_device_sends_nothing():
    # WASAPI loopback delivers no packets while nothing plays; engines need
    # silence to notice a sentence ended, so the source supplies it.
    source, _, _ = make([SPEAKERS], block_ms=30)
    received, _ = start(source)

    source.fill_silence(now=source.last_audio_at + 0.2)

    assert len(received) == 1
    assert len(received[0]) == 480 and not received[0].any()


def test_no_silence_is_added_for_a_briefly_late_packet():
    source, _, _ = make([SPEAKERS], block_ms=30)
    received, _ = start(source)

    source.fill_silence(now=source.last_audio_at + 0.1)

    assert received == []


def test_no_silence_without_an_open_device():
    source, _, _ = make([], endpoint=None)
    received, _ = start(source)

    source.fill_silence(now=1e9)

    assert received == []

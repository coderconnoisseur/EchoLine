import numpy as np

from echoline.audio.microphone import MicrophoneSource

MIC = {"index": 3, "name": "Microphone (Realtek)", "maxInputChannels": 2, "defaultSampleRate": 48000.0}


class FakeStream:
    def __init__(self, callback):
        self.callback, self.closed = callback, False

    def start_stream(self):
        pass

    def stop_stream(self):
        pass

    def is_active(self):
        return not self.closed

    def close(self):
        self.closed = True


class FakePyAudio:
    paContinue, paInt16, paWASAPI = 0, 8, 13

    def __init__(self, mic):
        self.mic, self.streams = mic, []

    def PyAudio(self):
        return self

    def get_host_api_info_by_type(self, api):
        return {"defaultInputDevice": self.mic["index"] if self.mic else -1}

    def get_device_info_by_index(self, index):
        if not self.mic or index != self.mic["index"]:
            raise OSError("no such device")
        return self.mic

    def open(self, **kwargs):
        stream = FakeStream(kwargs["stream_callback"])
        stream.kwargs = kwargs
        self.streams.append(stream)
        return stream

    def terminate(self):
        pass


def test_microphone_opens_default_input_and_delivers_audio():
    fake = FakePyAudio(MIC)
    source = MicrophoneSource(pyaudio_module=fake, default_device_id=lambda: "mic", poll_interval=None)
    received, statuses = [], []
    source.start(lambda samples, at: received.append(samples), statuses.append)

    fake.streams[0].callback(np.full((4800, 2), 8192, np.int16).tobytes(), 4800, None, 0)

    assert statuses == ["listening"]
    assert fake.streams[0].kwargs["input_device_index"] == 3
    assert sum(len(r) for r in received) > 1000


def test_missing_microphone_reports_no_device():
    source = MicrophoneSource(pyaudio_module=FakePyAudio(None), default_device_id=lambda: None, poll_interval=None)
    statuses = []

    source.start(lambda samples, at: None, statuses.append)

    assert statuses == ["no-microphone"]


def test_microphone_does_not_fill_silence():
    fake = FakePyAudio(MIC)
    source = MicrophoneSource(pyaudio_module=fake, default_device_id=lambda: "mic", poll_interval=None)
    received = []
    source.start(lambda samples, at: received.append(samples), lambda s: None)

    source.fill_silence(now=source.last_audio_at + 10)

    assert received == []

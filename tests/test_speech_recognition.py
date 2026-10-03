import numpy as np

from echoline.engine.vosk_recognizer import SpeechRecognizer


class RecordingKaldi:
    def __init__(self):
        self.waveforms = []

    def AcceptWaveform(self, data):
        self.waveforms.append(data)
        return True

    def Result(self):
        return '{"text": "hi"}'


def make_recognizer():
    recognizer = SpeechRecognizer.__new__(SpeechRecognizer)
    recognizer.recognizer = RecordingKaldi()
    return recognizer


def test_bytes_and_arrays_reach_vosk_as_identical_bytes():
    recognizer = make_recognizer()
    samples = np.array([1, -2, 3], dtype=np.int16)

    assert recognizer.process_audio_data(samples.tobytes()) == ("hi", False)
    assert recognizer.process_audio_data(samples) == ("hi", False)

    assert recognizer.recognizer.waveforms == [samples.tobytes(), samples.tobytes()]


def test_no_model_means_no_text():
    recognizer = SpeechRecognizer.__new__(SpeechRecognizer)
    recognizer.recognizer = None

    assert recognizer.process_audio_data(b"\x00\x00") == (None, False)

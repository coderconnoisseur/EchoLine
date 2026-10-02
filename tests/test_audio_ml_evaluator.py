import pytest

import metrics.audio_ml_evaluator as audio_ml_evaluator


class StubRecognizer:
    model = object()
    recognizer = None


@pytest.fixture
def evaluator(monkeypatch):
    monkeypatch.setattr(audio_ml_evaluator, 'SpeechRecognizer', StubRecognizer)
    return audio_ml_evaluator.AudioEvaluator(verbose=False)


def test_evaluation_feeds_per_word_accuracy_to_confusion_analyzer(evaluator):
    evaluator.evaluate_transcription("the cat sat", "the bat sat")

    accuracies = evaluator.confusion_analyzer.calculate_word_accuracies()
    assert accuracies['the'] == 1.0
    assert accuracies['cat'] == 0.0
    assert evaluator.confusion_analyzer.get_most_confused_pairs() == [('cat', 'bat', 1)]


def write_sine_wav(path, sample_rate, amplitude, seconds=0.5):
    import wave
    import numpy as np

    t = np.arange(int(sample_rate * seconds)) / sample_rate
    samples = (amplitude * np.sin(2 * np.pi * 440 * t)).astype(np.int16)
    with wave.open(str(path), 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(samples.tobytes())


def test_resampled_wav_keeps_its_amplitude(evaluator, tmp_path):
    path = tmp_path / "tone.wav"
    write_sine_wav(path, sample_rate=22050, amplitude=10000)

    audio, sample_rate, _ = evaluator.load_audio_file(str(path))

    assert sample_rate == 16000
    assert audio.dtype.name == 'int16'
    assert abs(int(audio.max()) - 10000) < 500


class FakeKaldiRecognizer:
    """Returns Vosk-shaped JSON: one finalized utterance, then the final flush."""

    def __init__(self):
        self.words_enabled = False
        self.results = ['{"text": "hello world", "result": ['
                        '{"word": "hello", "conf": 0.8}, {"word": "world", "conf": 0.6}]}']

    def SetWords(self, enabled):
        self.words_enabled = enabled

    def AcceptWaveform(self, data):
        return bool(self.results)

    def Result(self):
        return self.results.pop()

    def PartialResult(self):
        return '{"partial": ""}'

    def FinalResult(self):
        if not self.words_enabled:
            return '{"text": "bye"}'
        return '{"text": "bye", "result": [{"word": "bye", "conf": 1.0}]}'


@pytest.fixture
def evaluator_with_fake_vosk(monkeypatch):
    from transcription.speech_recognition import SpeechRecognizer

    recognizer = SpeechRecognizer.__new__(SpeechRecognizer)
    recognizer.model = object()
    recognizer.recognizer = FakeKaldiRecognizer()
    monkeypatch.setattr(audio_ml_evaluator, 'SpeechRecognizer', lambda: recognizer)
    return audio_ml_evaluator.AudioEvaluator(verbose=False)


def test_transcription_reports_mean_word_confidence(evaluator_with_fake_vosk):
    import numpy as np

    text, _, confidence = evaluator_with_fake_vosk.transcribe_audio(np.zeros(8000, dtype=np.int16))

    assert text == "hello world bye"
    assert confidence == pytest.approx(0.8)


def test_transcription_counts_recognized_words(evaluator_with_fake_vosk):
    import numpy as np

    evaluator_with_fake_vosk.transcribe_audio(np.zeros(8000, dtype=np.int16))

    assert evaluator_with_fake_vosk.performance_monitor.total_words == 3

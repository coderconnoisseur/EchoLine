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

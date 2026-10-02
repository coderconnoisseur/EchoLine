import pytest

from metrics.accuracy_evaluator import TranscriptionEvaluator


def test_f1_is_harmonic_mean_when_precision_and_recall_are_low():
    # 3 of 10 reference words matched, hypothesis also 10 words -> p = r = 0.3
    reference = "a b c d e f g h i j"
    hypothesis = "a b c x x x x x x x"

    metrics = TranscriptionEvaluator().evaluate_transcription(reference, hypothesis)

    assert metrics.word_precision == pytest.approx(0.3)
    assert metrics.word_recall == pytest.approx(0.3)
    assert metrics.word_f1_score == pytest.approx(0.3)


def test_f1_is_zero_when_nothing_matches():
    metrics = TranscriptionEvaluator().evaluate_transcription("hello world", "foo bar")

    assert metrics.word_f1_score == 0.0

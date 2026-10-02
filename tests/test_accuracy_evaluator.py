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


def test_confusion_matrix_does_not_leak_between_evaluations():
    evaluator = TranscriptionEvaluator()
    evaluator.evaluate_transcription("cat", "bat")

    metrics = evaluator.evaluate_transcription("dog", "dog")

    assert metrics.most_confused_words == []


def test_multiple_samples_aggregate_confusions_across_samples():
    evaluator = TranscriptionEvaluator()

    metrics = evaluator.evaluate_multiple_samples([("cat", "bat"), ("cat sat", "bat sat")])

    assert metrics.most_confused_words == [("cat", "bat", 2)]


def test_character_substitution_counts_as_one_error():
    metrics = TranscriptionEvaluator().evaluate_transcription("cat", "bat")

    assert metrics.char_error_rate == pytest.approx(1 / 3)


def test_character_error_rate_counts_insertions_and_deletions():
    evaluator = TranscriptionEvaluator()

    assert evaluator.evaluate_transcription("cat", "cats").char_error_rate == pytest.approx(1 / 3)
    assert evaluator.evaluate_transcription("cats", "cat").char_error_rate == pytest.approx(1 / 4)

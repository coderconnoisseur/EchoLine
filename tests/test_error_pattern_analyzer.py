from metrics.error_pattern_analyzer import ConfusionMatrixAnalyzer


def test_operation_list_records_confused_pairs():
    analyzer = ConfusionMatrixAnalyzer()

    analyzer.add_operation_list([
        ('match', 'the', 'the'),
        ('substitute', 'cat', 'bat'),
    ])

    assert analyzer.get_most_confused_pairs() == [('cat', 'bat', 1)]

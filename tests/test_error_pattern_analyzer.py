from metrics.error_pattern_analyzer import ConfusionMatrixAnalyzer


def test_operation_list_records_confused_pairs():
    analyzer = ConfusionMatrixAnalyzer()

    analyzer.add_operation_list([
        ('match', 'the', 'the'),
        ('substitute', 'cat', 'bat'),
    ])

    assert analyzer.get_most_confused_pairs() == [('cat', 'bat', 1)]


def test_error_patterns_classify_substitutions():
    analyzer = ConfusionMatrixAnalyzer()

    analyzer.add_confusion_data({
        'Hello': {'hello': 1},          # case only
        'color': {'colour': 2},         # phonetically close
        'a': {'elephant': 1},           # very different length
        'cat': {'dog': 1},              # unrelated
    })

    assert analyzer.analyze_error_patterns() == {
        'phonetic_errors': 2,
        'length_errors': 1,
        'capitalization_errors': 1,
        'semantic_errors': 1,
    }


def test_phonetic_similarity_uses_edit_distance():
    analyzer = ConfusionMatrixAnalyzer()

    assert analyzer._calculate_phonetic_similarity('color', 'colour') == 1 - 1 / 6
    assert analyzer._is_phonetically_similar('phone', 'fone')
    assert not analyzer._is_phonetically_similar('cat', 'dog')


def test_most_confused_pairs_are_sorted_by_count():
    analyzer = ConfusionMatrixAnalyzer()

    analyzer.add_confusion_data({'a': {'b': 1, 'c': 3}, 'd': {'e': 2}})

    assert analyzer.get_most_confused_pairs(top_k=2) == [('a', 'c', 3), ('d', 'e', 2)]


def test_report_lists_word_accuracy_from_alignment():
    analyzer = ConfusionMatrixAnalyzer()
    analyzer.add_operation_list([
        ('match', 'the', 'the'), ('match', 'the', 'the'), ('substitute', 'cat', 'bat'),
    ])

    report = analyzer.generate_detailed_report()

    assert "'cat' → 'bat' (1 times)" in report
    assert "'the' - 1.000 accuracy (2 occurrences)" in report

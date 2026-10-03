from echoline.ui.fonts import caption_fonts


def test_curated_fonts_come_first_then_the_rest_alphabetically():
    system = ["Wingdings", "Arial", "Segoe UI", "@Malgun Gothic", "Comic Sans MS", "Arial"]

    assert caption_fonts(system) == ["Segoe UI", "Arial", "Comic Sans MS", "Wingdings"]

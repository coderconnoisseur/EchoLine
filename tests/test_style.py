from echoline.ui.style import use_fluent_style


def test_fluent_style_is_selected():
    assert use_fluent_style() == "FluentWinUI3"

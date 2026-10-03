from ui.caption_buffer import CaptionBuffer


def test_final_results_accumulate():
    buffer = CaptionBuffer()

    buffer.add_final("hello there")
    buffer.add_final("general kenobi")

    assert buffer.text == "hello there general kenobi"


def test_partial_is_shown_after_committed_text_and_replaced_by_next_partial():
    buffer = CaptionBuffer()
    buffer.add_final("hello")

    buffer.add_partial("wor")
    buffer.add_partial("world")

    assert buffer.text == "hello world"


def test_final_result_replaces_pending_partial():
    buffer = CaptionBuffer()
    buffer.add_partial("helo wrld")

    buffer.add_final("hello world")

    assert buffer.text == "hello world"


def test_repeated_final_result_is_ignored():
    buffer = CaptionBuffer()

    buffer.add_final("hello")
    buffer.add_final("hello")

    assert buffer.text == "hello"


def test_text_keeps_only_the_most_recent_words():
    buffer = CaptionBuffer(max_words=4)

    buffer.add_final("one two three")
    buffer.add_final("four five six")
    buffer.add_partial("seven")

    assert buffer.text == "four five six seven"


def test_long_sessions_stay_bounded():
    buffer = CaptionBuffer(max_words=4)

    for i in range(1000):
        buffer.add_final(f"word{i}")

    assert buffer.text == "word996 word997 word998 word999"
    assert len(buffer.text.split()) == 4

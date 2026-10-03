from echoline.ui.placement import clamp_to_screen, snap_position

SCREEN = (0, 0, 1920, 1040)
SIZE = (670, 120)


def test_snap_positions_are_centered_with_margin():
    assert snap_position(SCREEN, SIZE, "bottom") == [625, 1040 - 120 - 48]
    assert snap_position(SCREEN, SIZE, "top") == [625, 48]
    assert snap_position(SCREEN, SIZE, "center") == [625, 460]


def test_visible_position_is_kept():
    assert clamp_to_screen([100, 200], SIZE, [SCREEN]) == [100, 200]


def test_offscreen_position_is_pulled_back_on_screen():
    # Saved on a second monitor that is no longer connected.
    assert clamp_to_screen([2500, 300], SIZE, [SCREEN]) == snap_position(SCREEN, SIZE, "bottom")


def test_partly_offscreen_position_is_moved_fully_on_screen():
    # e.g. the resolution was lowered: the overlay hangs 40% off the right edge.
    assert clamp_to_screen([1520, 900], SIZE, [SCREEN]) == [1920 - 670, 900]


def test_position_on_a_secondary_screen_is_kept():
    second = (1920, 0, 1280, 1024)

    assert clamp_to_screen([2000, 300], SIZE, [SCREEN, second]) == [2000, 300]


def test_no_saved_position_snaps_to_bottom():
    assert clamp_to_screen(None, SIZE, [SCREEN]) == snap_position(SCREEN, SIZE, "bottom")

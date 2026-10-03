def snap_position(screen, size, where, margin=48):
    sx, sy, sw, sh = screen
    w, h = size
    x = sx + (sw - w) // 2
    y = {"top": sy + margin, "center": sy + (sh - h) // 2, "bottom": sy + sh - h - margin}[where]
    return [x, y]


def _visible_fraction(position, size, screen):
    x, y = position
    w, h = size
    sx, sy, sw, sh = screen
    overlap_w = max(0, min(x + w, sx + sw) - max(x, sx))
    overlap_h = max(0, min(y + h, sy + sh) - max(y, sy))
    return overlap_w * overlap_h / max(w * h, 1)


def clamp_to_screen(position, size, screens):
    """Keep a saved position on the screen showing most of the overlay, moved fully inside it.

    Falls back to the bottom of the primary screen when no screen shows enough of it.
    """
    if position:
        best = max(screens, key=lambda s: _visible_fraction(position, size, s))
        if _visible_fraction(position, size, best) >= 0.5:
            sx, sy, sw, sh = best
            w, h = size
            x = min(max(position[0], sx), sx + sw - w)
            y = min(max(position[1], sy), sy + sh - h)
            return [x, y]
    return snap_position(screens[0], size, "bottom")

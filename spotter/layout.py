"""Pure layout numbers: frequency to vertical position, tick values, label spreading."""


def freq_to_y(freq: float, lo: float, hi: float, top: float, bottom: float) -> float:
    """Higher frequency at the top; linear. lo maps to bottom, hi to top."""
    return bottom - (freq - lo) / (hi - lo) * (bottom - top)


def ticks(lo: float, hi: float, n: int = 5) -> list[float]:
    """n intervals across the span: n + 1 tick frequencies, lo to hi."""
    return [lo + (hi - lo) * i / n for i in range(n + 1)]


def spread_labels(ys: list[float], min_gap: float, top: float, bottom: float) -> list[float]:
    """Label y for each true y (same order): at least min_gap apart, clamped to [top, bottom].

    If more labels are crowded than fit, they overlap at the clamp (known limitation 1).
    """
    order = sorted(range(len(ys)), key=lambda i: ys[i])
    pos = [min(max(ys[i], top), bottom) for i in order]
    for j in range(1, len(pos)):  # push down
        pos[j] = max(pos[j], pos[j - 1] + min_gap)
    for j in range(len(pos) - 1, -1, -1):  # pull back up from the bottom edge
        limit = bottom if j == len(pos) - 1 else pos[j + 1] - min_gap
        pos[j] = min(pos[j], limit)
    pos = [max(p, top) for p in pos]  # crowded beyond fit: overlap at the top
    out = [0.0] * len(ys)
    for j, i in enumerate(order):
        out[i] = pos[j]
    return out

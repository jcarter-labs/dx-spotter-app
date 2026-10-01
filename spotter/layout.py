"""Pure layout numbers: frequency to vertical position, tick values, label spreading."""


def freq_to_y(freq: float, lo: float, hi: float, top: float, bottom: float) -> float:
    """Higher frequency at the top; linear. lo maps to bottom, hi to top."""
    return bottom - (freq - lo) / (hi - lo) * (bottom - top)


def ticks(lo: float, hi: float, n: int = 5) -> list[float]:
    """n intervals across the span: n + 1 tick frequencies, lo to hi."""
    return [lo + (hi - lo) * i / n for i in range(n + 1)]


def spread_labels(ys: list[float], min_gap: float, top: float, bottom: float) -> list[float]:
    """Label y for each true y (same order): at least min_gap apart, clamped to [top, bottom].

    Crowded labels form blocks centred on their true positions (a block of n labels starts at
    the mean of y_i - i*gap, clamped inside the canvas). If more labels are crowded than fit,
    the block is pinned to the top edge, labels past the bottom edge are clamped there, and they overlap (known limitation 1).
    """
    order = sorted(range(len(ys)), key=lambda i: ys[i])
    blocks = []  # each: [start, count, sum_of(y_i - k*gap)]

    def start(b):
        lo = top
        hi = max(top, bottom - (b[1] - 1) * min_gap)
        return min(max(b[2] / b[1], lo), hi)

    for i in order:
        blocks.append([0.0, 1, ys[i]])
        blocks[-1][0] = start(blocks[-1])
        while len(blocks) > 1:
            prev, cur = blocks[-2], blocks[-1]
            if prev[0] + prev[1] * min_gap <= cur[0] + 1e-9:
                break
            # merge: labels of cur follow prev's, so their offsets shift by prev's count
            merged = [0.0, prev[1] + cur[1], prev[2] + cur[2] - cur[1] * prev[1] * min_gap]
            merged[0] = start(merged)
            blocks[-2:] = [merged]
    out = [0.0] * len(ys)
    j = 0
    for b in blocks:
        for k in range(b[1]):
            out[order[j]] = min(b[0] + k * min_gap, bottom)
            j += 1
    return out

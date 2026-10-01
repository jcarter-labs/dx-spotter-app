import ast
from pathlib import Path

import pytest

from spotter.layout import freq_to_y, spread_labels, ticks


def test_linear_and_higher_on_top():
    assert freq_to_y(14.070, 14.020, 14.070, 100, 1100) == 100
    assert freq_to_y(14.020, 14.020, 14.070, 100, 1100) == 1100
    assert freq_to_y(14.045, 14.020, 14.070, 100, 1100) == pytest.approx(600)
    a, b, c = (freq_to_y(f, 14.02, 14.07, 0, 500) for f in (14.03, 14.04, 14.05))
    assert (a - b) == pytest.approx(b - c)


def test_ticks_five_intervals():
    t = ticks(14.020, 14.070)
    assert len(t) == 6 and t[1] - t[0] == pytest.approx(0.010) and t[-1] == pytest.approx(14.070)
    t = ticks(14.040, 14.050)
    assert t[1] - t[0] == pytest.approx(0.002)       # bandwidth 10 kHz -> 2 kHz steps


def test_spread_keeps_far_labels_in_place():
    assert spread_labels([100, 300, 500], 14, 0, 600) == [100, 300, 500]


def test_spread_min_gap_and_order_preserved():
    ys = [200, 201, 202, 203, 50]
    out = spread_labels(ys, 14, 0, 600)
    s = sorted(out)
    assert all(b - a >= 14 - 1e-9 for a, b in zip(s, s[1:]))
    assert out[4] == 50                                    # untouched label stays
    assert out[0] < out[1] < out[2] < out[3]               # same order as the true frequencies


def test_spread_clamped_inside_canvas_at_edges():
    out = spread_labels([598, 599, 600], 14, 0, 600)
    assert all(0 <= y <= 600 for y in out) and sorted(out) == [572, 586, 600]
    out = spread_labels([0, 1, 2], 14, 0, 600)
    assert out == [0, 14, 28]


def test_crowded_more_than_fit_overlaps_inside_canvas():
    out = spread_labels([float(i) for i in range(100)], 14, 0, 600)   # 100 * 14 > 600
    assert all(0 <= y <= 600 for y in out)
    s = sorted(out)
    assert min(b - a for a, b in zip(s, s[1:])) < 14       # known limitation 1: overlap allowed


def test_no_tk_import():
    src = (Path(__file__).resolve().parent.parent / "spotter" / "layout.py").read_text()
    names = {n.names[0].name for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Import)}
    froms = {n.module for n in ast.walk(ast.parse(src)) if isinstance(n, ast.ImportFrom)}
    assert not any("tk" in str(x).lower() for x in names | froms)

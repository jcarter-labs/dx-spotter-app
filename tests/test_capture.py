"""G1 proof: the region capture lands on the window and rectangles are where they were drawn."""
import sys
import tkinter as tk
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from capture_window import run_and_capture  # noqa: E402


def bbox_of(im, pred):
    xs, ys = zip(*[(x, y) for y in range(im.height) for x in range(im.width) if pred(im.getpixel((x, y)))])
    return min(xs), min(ys), max(xs), max(ys)


def test_capture_matches_drawn_geometry(tmp_path):
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display")
    root.geometry("300x200+120+120")
    c = tk.Canvas(root, width=300, height=200, highlightthickness=0, bg="white")
    c.pack(fill="both", expand=True)
    c.create_rectangle(40, 30, 140, 90, fill="#ff0000", outline="")      # x 40-139, y 30-89
    c.create_rectangle(200, 120, 280, 180, fill="#0000ff", outline="")   # x 200-279, y 120-179
    im = run_and_capture(root, str(tmp_path / "g1.png"))
    assert im.size == (300, 200)
    red = bbox_of(im, lambda p: p[0] > 180 and p[1] < 100 and p[2] < 100)
    blue = bbox_of(im, lambda p: p[2] > 180 and p[0] < 100 and p[1] < 100)
    assert red == pytest.approx((40, 30, 139, 89), abs=1), "blank capture? check Screen Recording permission"
    assert blue == pytest.approx((200, 120, 279, 179), abs=1)

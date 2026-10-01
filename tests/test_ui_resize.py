"""5.2 resize: minimum 400 x 700, layout follows, panel and status lines stay fully visible."""
import queue
import sys
from pathlib import Path

import pytest
from PIL import Image

from spotter.app import App
from spotter.settings import Settings
from spotter.ui import HEADER_H, MARGIN, PANEL_W, SpotterUI
from tests.test_ui_guards import line, new_root, run_loop

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from capture_window import capture  # noqa: E402


def mk(root):
    q = queue.Queue()
    app = App(q, Settings())
    ui = SpotterUI(root, app, tick_ms=100)
    for i in range(12):
        q.put(line(f"K{i}ABC", 14030.0 + i * 0.3))
    return q, app, ui


def panel_widgets(ui):
    return [ui.freq_label, ui.freq_entry, ui.set_btn, ui.bw_label, ui.bw_box, ui.win_label, ui.win_box,
            ui.spot_label, ui.local, ui.regional, ui.srv_label, ui.srv_box, ui.clear_btn, ui.dot,
            ui.cluster, ui.pota, ui.shown, ui.heading, ui.col_rbn, ui.col_pota]


def inside(ui, root):
    W, H = root.winfo_width(), root.winfo_height()
    bad = []
    for w in panel_widgets(ui):
        x0, y0 = w.winfo_x(), w.winfo_y()
        x1, y1 = x0 + w.winfo_reqwidth() if w.winfo_width() < 2 else x0 + w.winfo_width(), y0 + w.winfo_height()
        if x0 < 0 or y0 < 0 or x1 > W or y1 > H:
            bad.append((str(w), x0, y0, x1, y1, W, H))
    return bad


def scale_ticks(im, x_line):
    """y of the first and last tick on the RBN scale in a capture (rows where the pixel left of the line is dark)."""
    rows = [y for y in range(HEADER_H, im.height) if im.getpixel((x_line - 3, y))[0] < 140]
    return min(rows), max(rows)


@pytest.mark.parametrize("w,h", [(400, 700), (492, 1150), (700, 900), (900, 1300)])
def test_layout_follows_and_stays_visible(w, h):
    root = new_root()
    q, app, ui = mk(root)
    res = {}

    def act():
        root.geometry(f"{w}x{h}+40+40"); root.update(); ui.redraw()
        res["size"] = (root.winfo_width(), root.winfo_height())
        res["bad"] = inside(ui, root)
        res["canvas"] = (ui.canvas.winfo_x(), ui.canvas.winfo_y(), ui.canvas.winfo_width(), ui.canvas.winfo_height())
        res["panel_x"] = ui.freq_entry.winfo_x()
        res["texts_in_canvas"] = all(b[2] <= ui.canvas.winfo_width() and b[0] >= 0 for b in ui.hits)
        res["img"] = capture(root)
        res["rbn_x"] = ui._rbn_x(ui.canvas.winfo_width())

    run_loop(root, [(500, act)], 1500)
    root.destroy()
    assert res["size"] == (w, h)
    assert res["bad"] == [], res["bad"]
    cx, cy, cw, ch = res["canvas"]
    assert (cx, cy, cw, ch) == (0, HEADER_H, w - PANEL_W, h - HEADER_H)      # canvas takes the extra size
    assert res["panel_x"] >= cw                                              # panel right of the canvas, not clipped
    assert res["texts_in_canvas"]
    top, bottom = scale_ticks(res["img"], res["rbn_x"])
    assert abs(top - (HEADER_H + MARGIN)) <= 2                               # scales stretch to the canvas height
    assert abs(bottom - (h - MARGIN)) <= 2


def test_minimum_size_is_enforced():
    root = new_root()
    q, app, ui = mk(root)
    res = {}

    def act():
        root.geometry("300x400+40+40"); root.update()
        res["size"] = (root.winfo_width(), root.winfo_height())

    run_loop(root, [(500, act)], 1000)
    root.destroy()
    assert res["size"][0] >= 400 and res["size"][1] >= 700

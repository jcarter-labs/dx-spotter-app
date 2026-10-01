"""Step 1.3: measure screenshot.png and write measurements.json.

Separate tool, not part of the app. Run from the repo root inside the venv:
    python tools/measure_screenshot.py
All y values in the file are content-area coordinates (title bar excluded, y=0 is the
first content row); x values are screenshot pixels. Boxes are [x0, y0, x1, y1] inclusive.
"""
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
px = None  # set by measure()
PANEL = (217, 217, 217)
WHITE = (255, 255, 255)



def _setup(im):
    global px
    px = im.load()
    return im.size


def differs(c, bg, tol=12):
    return max(abs(c[i] - bg[i]) for i in range(3)) > tol


def groups(idx, is_ink, gap):
    out, s, last = [], None, None
    for i in idx:
        if is_ink(i):
            if s is None:
                s = i
            last = i
        elif s is not None and i - last > gap:
            out.append((s, last))
            s = None
    if s is not None:
        out.append((s, last))
    return out


def bbox(x0, y0, x1, y1, bg, tol=12):
    xs, ys = [], []
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if differs(px[x, y], bg, tol):
                xs.append(x)
                ys.append(y)
    return (min(xs), min(ys), max(xs), max(ys)) if xs else None


def measure(im):
    """Measure a screenshot-like image (title bar included) into the measurements dict."""
    W, H = _setup(im)
    # --- title bar: first row of the panel/content colour
    col = 5
    TITLE_END = next(y for y in range(H) if px[col, y] == (221, 221, 221))  # border row under title bar
    CONTENT_TOP = TITLE_END + 1
    # canvas: white block at left
    CANVAS_TOP = next(y for y in range(H) if px[2, y] == WHITE)
    CANVAS_RIGHT = max(x for x in range(W) if px[x, 600] == WHITE)
    PANEL_LEFT = CANVAS_RIGHT + 1


    def c(box):  # to content-area y
        return [box[0], box[1] - CONTENT_TOP, box[2], box[3] - CONTENT_TOP]


    m = {}
    m["_reference"] = {
        "screenshot_size": [W, H],
        "title_bar_height": CONTENT_TOP,
        "content_size": [W, H - CONTENT_TOP],
        "note": "y is content-area y (title bar excluded). Boxes [x0,y0,x1,y1] inclusive.",
    }
    m["1_title_bar"] = {"box": [0, 0, W - 1, TITLE_END], "height_px": CONTENT_TOP,
                        "text_box": (lambda b: list(b) if b else None)(bbox(120, 5, 370, 34, (250, 250, 250), 40)),
                        "excluded_from_content_checks": True}

    # 2 heading, 3 rule
    m["2_heading"] = {"box": c(bbox(10, CONTENT_TOP + 3, W - 10, 90, PANEL))}
    rule_y = next(y for y in range(88, 100) if differs(px[246, y], PANEL))
    rx = [x for x in range(W) if differs(px[x, rule_y], PANEL, 40)]
    m["3_rule"] = {"box": c((min(rx), rule_y, max(rx), rule_y))}

    # canvas
    m["canvas"] = {"box": c((0, CANVAS_TOP, CANVAS_RIGHT, H - 1))}

    # 4, 5 column labels (panel colour above canvas)
    m["4_label_RBN"] = {"box": c(bbox(20, 100, 150, CANVAS_TOP - 1, PANEL))}
    m["5_label_POTA"] = {"box": c(bbox(160, 100, 260, CANVAS_TOP - 1, PANEL))}

    # 6 RBN scale: black vertical line
    def black_col(y0, y1):
        best = None
        for x in range(60, 200):
            n = sum(1 for y in range(y0, y1) if px[x, y][0] < 60)
            if best is None or n > best[1]:
                best = (x, n)
        return best[0]


    rbn_x = black_col(CANVAS_TOP, H)
    ys = [y for y in range(CANVAS_TOP, H) if px[rbn_x, y][0] < 60]
    rbn_y0, rbn_y1 = min(ys), max(ys)
    # ticks: rows where the pixel just left of the line is dark
    tick_rows = groups(range(rbn_y0, rbn_y1 + 1), lambda y: px[rbn_x - 3, y][0] < 100, 0)
    ticks_rbn = [(a + b) / 2 for a, b in tick_rows]
    tick_len_left = max(x for x in range(rbn_x - 15, rbn_x) if px[x, ticks_rbn and int(ticks_rbn[0])][0] < 100)
    tick_x0 = min(x for x in range(rbn_x - 15, rbn_x) if px[x, int(ticks_rbn[0])][0] < 100)
    labels = []
    for a, b in groups(range(CANVAS_TOP, H), lambda y: any(differs(px[x, y], WHITE, 60) for x in range(40, tick_x0 - 2)), 1):
        bb = bbox(40, a, tick_x0 - 2, b, WHITE, 60)
        labels.append(c(bb))
    m["6_rbn_scale"] = {
        "line_x": rbn_x, "line_y_range": [rbn_y0 - CONTENT_TOP, rbn_y1 - CONTENT_TOP],
        "tick_x_range": [tick_x0, rbn_x - 1],
        "tick_y_centres": [t - CONTENT_TOP for t in ticks_rbn],
        "tick_label_boxes": labels,
        "tick_label_centres_y": [(l[1] + l[3]) / 2 for l in labels],
        "tick_label_right_edge_x": [l[2] for l in labels],
        "ticks_expected": 6,
    }

    # 8 POTA scale
    pota_x = black_col(CANVAS_TOP, H) if False else None
    best = max(range(260, CANVAS_RIGHT), key=lambda x: sum(1 for y in range(CANVAS_TOP, H) if px[x, y][0] < 60))
    pota_x = best
    pys = [y for y in range(CANVAS_TOP, H) if px[pota_x, y][0] < 60]
    ptick = groups(range(min(pys), max(pys) + 1), lambda y: px[pota_x + 3, y][0] < 100 or px[pota_x - 3, y][0] < 100, 0)
    # ticks only: those that stick out to the right (pota ticks) -- leader lines come from the left
    ptick_right = groups(range(min(pys), max(pys) + 1), lambda y: px[pota_x + 3, y][0] < 100, 0)
    m["8_pota_scale"] = {
        "line_x": pota_x, "line_y_range": [min(pys) - CONTENT_TOP, max(pys) - CONTENT_TOP],
        "tick_y_centres": [(a + b) / 2 - CONTENT_TOP for a, b in ptick_right],
        "tick_x_range_right": [pota_x + 1, max(x for x in range(pota_x + 1, pota_x + 15) if any(px[x, int((a + b) / 2)][0] < 100 for a, b in ptick_right[:1]))],
    }

    # 7 RBN spot text and 9 POTA spot text (text starts right of the leader-line fan)
    def text_region(x0, x1, bgc=WHITE):
        return bbox(x0, CANVAS_TOP, x1, H - 1, bgc, 25)

    m["7_rbn_spots"] = {
        "text_left_x": min(bb[0] for bb in [bbox(rbn_x + 8, y0, 200, y1, WHITE, 25)
                           for y0, y1 in groups(range(CANVAS_TOP, H), lambda y: any(differs(px[x, y], WHITE, 25) for x in range(rbn_x + 8, 200)), 0)] if bb),
        "box": c(bbox(rbn_x + 2, CANVAS_TOP, 200, H - 1, WHITE, 25)),
        "note": "box includes leader lines; text_left_x is the left edge of the call-sign text",
    }
    text_cols = [x for x in range(205, pota_x - 1) if any(differs(px[x, y], WHITE, 25) for y in range(CANVAS_TOP, H))]
    m["9_pota_spots"] = {
        "box": c(bbox(205, CANVAS_TOP, pota_x - 1, H - 1, WHITE, 25)),
        "text_right_x": None,
    }
    # right edge of POTA call text: rightmost x of dark text, before the leader fan (take the 75th percentile of row-right-edges)
    edges = []
    for y0, y1 in groups(range(CANVAS_TOP, H), lambda y: any(differs(px[x, y], WHITE, 25) for x in range(205, pota_x - 1)), 0):
        bb = bbox(205, y0, pota_x - 1, y1, WHITE, 25)
        if bb and (bb[3] - bb[1]) >= 8:
            edges.append(bb[2])
    # right edge of call text: the leader line runs at mid-height, so look at the top 3 rows of each text band only
    rights = []
    for y0, y1 in groups(range(CANVAS_TOP, H), lambda y: any(differs(px[x, y], WHITE, 25) for x in range(205, pota_x - 1)), 0):
        if y1 - y0 >= 8:
            bb = bbox(205, y0, pota_x - 1, y0 + 2, WHITE, 25)
            if bb:
                rights.append(bb[2])
    from collections import Counter
    m["9_pota_spots"]["text_right_x"] = Counter(rights).most_common(1)[0][0] if rights else None
    m["9_pota_spots"]["text_right_x_all_rows"] = sorted(Counter(rights).items())

    # panel elements
    rows = groups(range(CONTENT_TOP + 70, 560), lambda y: any(differs(px[x, y], PANEL) for x in range(PANEL_LEFT + 4, W - 4)), 1)
    blocks = []
    for r in rows:
        for cx in groups(range(PANEL_LEFT, W - 3), lambda x: any(differs(px[x, y], PANEL) for y in range(r[0], r[1] + 1)), 8):
            blocks.append(c((cx[0], r[0], cx[1], r[1])))
    panel = {}
    named = ["10_label_frequency", None, "12_label_bandwidth", "12_bandwidth_dropdown", "13_label_window",
             "13_window_dropdown", "14_label_spotter", "14_radio_local", "14_radio_regional", "15_label_server",
             "15_server_dropdown", "16_clear_button", None, "17_cluster_text", "18_pota_status", "19_shown_status"]
    for n, b in zip(named, blocks):
        if n:
            panel[n] = {"box": b}
    # frequency row: textbox and Set button
    fr = blocks[1]
    fcols = groups(range(fr[0], fr[2] + 1), lambda x: any(differs(px[x, y], PANEL) for y in range(fr[1] + CONTENT_TOP, fr[3] + CONTENT_TOP + 1)), 2)
    panel["11_frequency_textbox"] = {"box": [fcols[0][0], fr[1], fcols[0][1], fr[3]]}
    panel["11_set_button"] = {"box": [fcols[-1][0], fr[1], fcols[-1][1], fr[3]]}
    db = bbox(310, CONTENT_TOP + blocks[12][1], 326, CONTENT_TOP + blocks[12][3], PANEL, 25)
    panel["17_status_dot"] = {"box": c(db)}
    m.update(panel)
    m["_check_note"] = "layout checks pass when a measured box edge is within +/-4 px of these values (content-area y)"
    return m


if __name__ == "__main__":
    m = measure(Image.open(ROOT / "screenshot.png").convert("RGB"))
    Path(ROOT / "measurements.json").write_text(json.dumps(m, indent=1))
    print("elements:", sorted(k for k in m if k[0].isdigit()))

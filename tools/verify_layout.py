"""G2: compare a window capture to the step 1.3 measurements (content area, +/-4 px).

    python tools/verify_layout.py capture.png

The capture is the content area only (see capture_window.py), at the reference size 492 x 1150.
It is padded with a reference-style title bar so tools/measure_screenshot.py's measuring code
runs unchanged, then each measured number is compared with measurements.json. Prints a
pass/fail table; exit status 1 if any row fails. Elements 7 and 9 (spots) compare only their
text alignment edge, since their box depends on the spots drawn.
"""
import json
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from measure_screenshot import measure  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TOL = 4
SKIP = {"_reference", "1_title_bar", "_check_note", "panel_block_count"}
ONLY = {"7_rbn_spots": ["text_left_x"], "9_pota_spots": ["text_right_x"]}


def pad_with_title_bar(content: Image.Image, title_h: int) -> Image.Image:
    im = Image.new("RGB", (content.width, content.height + title_h), (250, 250, 250))
    for x in range(content.width):
        im.putpixel((x, title_h - 1), (221, 221, 221))
    im.paste(content, (0, title_h))
    return im


def flatten(v, path=""):
    if isinstance(v, bool) or v is None or isinstance(v, str):
        return
    if isinstance(v, (int, float)):
        yield path, float(v)
    elif isinstance(v, (list, tuple)):
        for i, x in enumerate(v):
            yield from flatten(x, f"{path}[{i}]")
    elif isinstance(v, dict):
        for k, x in v.items():
            yield from flatten(x, f"{path}.{k}" if path else k)


def compare(expected: dict, got: dict, tol=TOL):
    rows = []
    for elem, ev in expected.items():
        if elem in SKIP:
            continue
        fields = ONLY.get(elem)
        for fpath, e in flatten(ev):
            top = fpath.split("[")[0].split(".")[0]
            if fields is not None and top not in fields:
                continue
            if top in ("height_px", "ticks_expected") or top.endswith("_all_rows") or top == "note":
                continue
            gv = dict(flatten(got.get(elem, {}))).get(fpath)
            if gv is None:
                rows.append((elem, fpath, e, None, None, False))
            else:
                rows.append((elem, fpath, e, gv, gv - e, abs(gv - e) <= tol))
    return rows


def main(path):
    ref = json.loads((ROOT / "measurements.json").read_text())
    content = Image.open(path).convert("RGB")
    want = tuple(ref["_reference"]["content_size"])
    size_ok = content.size == want
    got = measure(pad_with_title_bar(content, ref["_reference"]["title_bar_height"]))
    rows = compare(ref, got)
    fails = [r for r in rows if not r[5]]
    print(f"content size {content.size}, reference {want}: {'PASS' if size_ok else 'FAIL'}")
    print(f"{'element':<24}{'field':<28}{'expected':>9}{'got':>9}{'delta':>7}  result")
    for elem, f, e, g, d, ok in rows:
        print(f"{elem:<24}{f:<28}{e:>9.1f}{('-' if g is None else format(g, '.1f')):>9}"
              f"{('-' if d is None else format(d, '+.1f')):>7}  {'PASS' if ok else 'FAIL'}")
    elems = sorted({r[0] for r in rows}, key=lambda s: (int(''.join(ch for ch in s.split('_')[0] if ch.isdigit()) or 99), s))
    bad = sorted({r[0] for r in fails})
    print(f"\n{len(rows) - len(fails)}/{len(rows)} numbers within +/-{TOL} px; "
          f"{len(elems) - len(bad)}/{len(elems)} elements pass" + (f"; FAILED: {', '.join(bad)}" if bad else ""))
    return 0 if size_ok and not fails else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))

"""G1: capture a Tk window's content area by screen region. Not part of the app.

capture(root, path) -> PIL image scaled to Tk points (Retina 2x screenshots are halved).
"""
import subprocess
import tempfile
from pathlib import Path

from PIL import Image


def capture(root, path=None):
    root.update_idletasks()
    root.update()
    x, y, w, h = root.winfo_rootx(), root.winfo_rooty(), root.winfo_width(), root.winfo_height()
    with tempfile.TemporaryDirectory() as d:
        raw = Path(d) / "raw.png"
        subprocess.run(["screencapture", "-x", "-R", f"{x},{y},{w},{h}", str(raw)], check=True)
        im = Image.open(raw).convert("RGB")
    if im.size != (w, h):  # Retina: pixels are an integer multiple of points
        im = im.resize((w, h), Image.LANCZOS)
    if path:
        im.save(path)
    return im


def run_and_capture(root, path=None, delay_ms=1500, before=None):
    """Run the Tk main loop, capture after delay_ms, then close the window; returns the image.

    Tk must be inside mainloop() to paint (an update() loop leaves a white canvas on macOS).
    `before(root)` runs just before the capture. Screen colours are colour-managed by macOS, so
    compare positions and rough hue, not exact RGB.
    """
    out = {}

    def go():
        if before:
            before(root)
            root.update()
        out["im"] = capture(root, path)
        root.destroy()

    root.after(delay_ms, go)
    root.mainloop()
    return out["im"]

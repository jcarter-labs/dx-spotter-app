"""Tkinter window: canvas bandmap and side panel. The only module that imports Tk.

Draws what `app.view()` says and passes operator input to `app`; it never waits on data. One
loop: an `after()` tick that calls `app.drain()` then redraws. Layout numbers are the step 1.3
measurements of the reference screenshot (492 x 1150 content area), scaled with the window.
"""
import subprocess
import time
import tkinter as tk
from tkinter import ttk

from . import layout
from .app import App, DrawSpot
from .settings import BANDWIDTHS, FADE_TIMES

REF_W = 492
PANEL_W = 193           # reference: panel spans x 299..491
REF_CANVAS_W = REF_W - PANEL_W
HEADER_H = 88           # canvas top (content y)
MARGIN = 21             # scale line starts/ends this far inside the canvas
LABEL_GAP = 16          # at least one text height between call signs
MIN_SIZE = (400, 700)

GREY, WHITE = "#d9d9d9", "#ffffff"
RBN_RGB, POTA_RGB = (31, 79, 216), (26, 143, 60)
DOT = {"green": "#1a7a1a", "amber": "#e0a000", "red": "#cc2222"}
FONT = "Arial"
F_LABEL, F_TICK = ("Lucida Grande", 10), (FONT, 9, "bold")
F_STATUS = (FONT, 10)
F_COL, F_HEAD, F_SPOT = (FONT, 10, "bold"), ("Lucida Grande", 16, "bold"), (FONT, 10)

# panel widgets: reference x, y(content), width, height (screen-list elements 10-19)
PANEL = {
    "freq_label": (312, 76), "freq_entry": (311, 94, 78, 30), "set_btn": (395, 94, 83, 30),
    "bw_label": (312, 137), "bw_box": (311, 155, 65, 29),
    "win_label": (312, 197), "win_box": (311, 215, 65, 29),
    "spot_label": (312, 258), "local": (312, 279), "regional": (312, 302),
    "srv_label": (312, 330), "srv_box": (311, 348, 155, 29),
    "clear": (311, 389, 167, 30),
    "dot": (313, 441), "cluster": (356, 438), "pota": (312, 459), "shown": (312, 480),
    "msg": (312, 505),
}


def blend(rgb, opacity):
    """Text colour toward the white background; Tk has no text transparency."""
    return "#%02x%02x%02x" % tuple(round(255 - (255 - c) * opacity) for c in rgb)


class Radio(tk.Canvas):
    """Small diamond radio button (the reference's look); the native indicator is too large."""

    def __init__(self, master, text, value, variable, command):
        super().__init__(master, width=76, height=14, bg=GREY, highlightthickness=0, bd=0)
        self.value, self.variable, self.command = value, variable, command
        self.diamond = self.create_polygon(5, 1, 10, 6, 5, 11, 0, 6, fill=WHITE, outline="#555555")
        self.create_text(17, 6, text=text, anchor="w", font=F_LABEL, fill="black")
        self.bind("<Button-1>", lambda e: self.select())
        variable.trace_add("write", lambda *a: self.refresh())
        self.refresh()

    def select(self):
        self.variable.set(self.value)
        self.command()

    def refresh(self):
        self.itemconfigure(self.diamond, fill="#4a6078" if self.variable.get() == self.value else WHITE)


class SpotterUI:
    def __init__(self, root: tk.Tk, app: App, tick_ms: int = 250, on_close=None):
        self.root, self.app, self.tick_ms, self._on_close = root, app, tick_ms, on_close
        self.hits = []              # (x0, y0, x1, y1, call) of the labels as drawn
        self.max_late_ms = 0.0
        self._next_tick = None
        root.title("DX Spotter")
        root.configure(bg=GREY)
        root.minsize(*MIN_SIZE)
        root.geometry(f"{REF_W}x1150")
        self._style()
        self._build()
        root.bind("<Configure>", lambda e: self._place() if e.widget is root else None)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self._place()
        self._schedule()

    # --- construction
    def _style(self):
        st = ttk.Style(self.root)
        st.theme_use("clam")  # fixed light look whatever the macOS appearance
        st.configure("TCombobox", fieldbackground=WHITE, background="#e8e8e8", foreground="black",
                     arrowsize=12, padding=2)
        st.map("TCombobox", fieldbackground=[("readonly", WHITE)], foreground=[("readonly", "black")])
        st.configure("TButton", background="#e8e8e8", foreground="black", font=F_LABEL, padding=2)
        self.root.option_add("*TCombobox*Listbox.font", F_LABEL)

    def _label(self, text, font=F_LABEL, **kw):
        return tk.Label(self.root, text=text, font=font, bg=GREY, fg="black", bd=0, padx=0, pady=0, **kw)

    def _build(self):
        r, a = self.root, self.app
        self.heading = self._label("RBN & POTA Spotter", F_HEAD)
        self.rule = tk.Frame(r, bg="#828282", height=1)
        self.col_rbn = self._label("RBN", F_COL)
        self.col_pota = self._label("POTA", F_COL)
        self.canvas = tk.Canvas(r, bg=WHITE, highlightthickness=0, bd=0)
        self.canvas.bind("<Button-1>", self._click)
        self.freq_label = self._label("Frequency (MHz)")
        self.freq_var = tk.StringVar(value=f"{a.settings.frequency:g}")
        self.freq_entry = tk.Entry(r, textvariable=self.freq_var, font=F_LABEL, bg=WHITE, fg="black",
                                   highlightthickness=1, highlightbackground="#888", relief="flat",
                                   insertbackground="black")
        self.freq_entry.bind("<Return>", lambda e: self._set_frequency())
        self.set_btn = ttk.Button(r, text="Set", command=self._set_frequency)
        self.bw_label = self._label("Bandwidth (kHz)")
        self.bw_box = ttk.Combobox(r, values=[str(b) for b in BANDWIDTHS], state="readonly", font=F_LABEL)
        self.bw_box.set(str(a.settings.bandwidth))
        self.bw_box.bind("<<ComboboxSelected>>", lambda e: self._pick(a.set_bandwidth, self.bw_box))
        self.win_label = self._label("Window (min)")
        self.win_box = ttk.Combobox(r, values=[str(f) for f in FADE_TIMES], state="readonly", font=F_LABEL)
        self.win_box.set(str(a.settings.fade))
        self.win_box.bind("<<ComboboxSelected>>", lambda e: self._pick(a.set_fade, self.win_box))
        self.spot_label = self._label("Spotter")
        self.spot_var = tk.StringVar(value=a.settings.spotter)
        self.local = Radio(r, "Local", "Local", self.spot_var, self._spotter)
        self.regional = Radio(r, "Regional", "Regional", self.spot_var, self._spotter)
        self.srv_label = self._label("Server")
        self.srv_box = ttk.Combobox(r, values=["NC7J (AR-Cluster)"], state="readonly", font=F_LABEL)
        self.srv_box.set("NC7J (AR-Cluster)")
        self.clear_btn = ttk.Button(r, text="Clear", command=self._clear)
        self.dot = tk.Canvas(r, width=8, height=8, bg=GREY, highlightthickness=0, bd=0)
        self.dot_item = self.dot.create_oval(0, 0, 7, 7, fill=DOT["amber"], outline=DOT["amber"])
        self.cluster = self._label("", F_STATUS, anchor="w")
        self.pota = self._label("", F_STATUS, anchor="w")
        self.shown = self._label("", F_STATUS, anchor="w")
        self.msg = tk.Label(r, text="", font=F_LABEL, bg=GREY, fg="#aa0000", bd=0, anchor="nw",
                            justify="left", wraplength=170)

    def _place(self):
        r = self.root
        W, H = r.winfo_width(), r.winfo_height()
        if W < 2:
            return
        px0 = W - PANEL_W                      # panel left edge (reference 299)
        dx = px0 - (REF_W - PANEL_W)
        self.heading.place(x=W / 2, y=31.5, anchor="center")
        self.rule.place(x=24, y=54, width=W - 51, height=1)
        cw = px0
        self.canvas.place(x=0, y=HEADER_H, width=cw, height=H - HEADER_H)
        self.col_rbn.place(x=self._rbn_x(cw) - 33.5, y=76.5, anchor="center")
        self.col_pota.place(x=self._pota_x(cw) - 62, y=76.5, anchor="center")
        for name, w in (("freq_label", self.freq_label), ("bw_label", self.bw_label), ("win_label", self.win_label),
                        ("spot_label", self.spot_label), ("srv_label", self.srv_label)):
            x, y = PANEL[name]
            w.place(x=x + dx, y=y, anchor="nw")
        for name, w in (("freq_entry", self.freq_entry), ("set_btn", self.set_btn), ("bw_box", self.bw_box),
                        ("win_box", self.win_box), ("srv_box", self.srv_box), ("clear", self.clear_btn)):
            x, y, ww, hh = PANEL[name]
            w.place(x=x + dx, y=y, width=ww, height=hh)
        for name, w in (("local", self.local), ("regional", self.regional), ("dot", self.dot),
                        ("cluster", self.cluster), ("pota", self.pota), ("shown", self.shown), ("msg", self.msg)):
            x, y = PANEL[name]
            w.place(x=x + dx, y=y, anchor="nw")
        self.redraw()

    # --- operator input
    def _set_frequency(self):
        ok, msg = self.app.set_frequency(self.freq_var.get())
        self.freq_var.set(f"{self.app.settings.frequency:g}")  # the accepted value, or the old one
        self.msg.config(text="" if ok else msg)
        self.redraw()

    def _clear(self):
        self.app.clear()
        self.msg.config(text="")
        self.redraw()

    def _pick(self, fn, box):
        ok, msg = fn(box.get())
        self.msg.config(text="" if ok else msg)
        self.root.focus_set()
        self.redraw()

    def _spotter(self):
        self.app.set_spotter(self.spot_var.get())
        self.redraw()

    def _click(self, e):
        for x0, y0, x1, y1, call in reversed(self.hits):
            if x0 - 1 <= e.x <= x1 + 1 and y0 - 1 <= e.y <= y1 + 1:
                self.copy(call)
                return

    def copy(self, call: str):
        """Exactly the call sign as spotted. pbcopy keeps it on the clipboard after the app quits."""
        try:
            subprocess.run(["pbcopy"], input=call.encode(), check=True, timeout=2)
        except (OSError, subprocess.SubprocessError):
            pass
        self.root.clipboard_clear()
        self.root.clipboard_append(call)

    # --- drawing
    @staticmethod
    def _rbn_x(cw):
        return round(104 / REF_CANVAS_W * cw)

    @staticmethod
    def _pota_x(cw):
        return round(284 / REF_CANVAS_W * cw)

    def redraw(self):
        c, a = self.canvas, self.app
        v = a.view()
        c.delete("all")
        self.hits = []
        cw, ch = c.winfo_width(), c.winfo_height()
        if cw < 2 or ch < 2:
            return
        top, bottom = MARGIN, ch - MARGIN
        rx, px = self._rbn_x(cw), self._pota_x(cw)
        c.create_line(rx, top, rx, bottom, fill="black")
        c.create_line(px, top, px, bottom, fill="black")
        for f in layout.ticks(v.lo, v.hi):
            y = layout.freq_to_y(f, v.lo, v.hi, top, bottom)
            c.create_line(rx - 4, y, rx, y, fill="black")
            c.create_line(px, y, px + 4, y, fill="black")
            c.create_text(rx - 11, y, text=f"{f:.3f}", anchor="e", font=F_TICK, fill="black")
        self._draw_spots(v.rbn, rx, +1, RBN_RGB, top, bottom, v)
        self._draw_spots(v.pota, px, -1, POTA_RGB, top, bottom, v)
        self.dot.itemconfigure(self.dot_item, fill=DOT[v.dot], outline=DOT[v.dot])
        self.cluster.config(text=v.cluster_text)
        self.pota.config(text=v.pota_text)
        self.shown.config(text=v.shown_text)
        if v.warning:
            self.msg.config(text=v.warning)
        elif self.msg.cget("text").startswith(self.app.warning_prefix):
            self.msg.config(text="")

    def _draw_spots(self, spots: list[DrawSpot], x, side, rgb, top, bottom, v):
        if not spots:
            return
        ys = [layout.freq_to_y(s.freq_mhz, v.lo, v.hi, top, bottom) for s in spots]
        ly = layout.spread_labels(ys, LABEL_GAP, top - MARGIN + 8, bottom + MARGIN - 8)
        c = self.canvas
        for s, y, yl in sorted(zip(spots, ys, ly), key=lambda t: t[2]):
            col = blend(rgb, s.opacity)
            c.create_line(x, y, x + 8 * side, yl, fill=col)
            t = c.create_text(x + 9 * side, yl, text=s.call, anchor="w" if side > 0 else "e",
                              font=F_SPOT, fill=col)
            b = c.bbox(t)
            self.hits.append((b[0], b[1], b[2], b[3], s.call))

    # --- the one loop
    def _schedule(self):
        self._next_tick = time.monotonic() + self.tick_ms / 1000.0
        self.root.after(self.tick_ms, self._tick)

    def _tick(self):
        late = (time.monotonic() - self._next_tick) * 1000.0
        self.max_late_ms = max(self.max_late_ms, late)
        self.app.drain()
        self.redraw()
        self._schedule()

    def close(self):
        if self._on_close:
            self._on_close()
        self.root.destroy()

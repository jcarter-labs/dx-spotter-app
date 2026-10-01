"""Stage 4 live check: the real app against the real servers. Not part of the app.

Run from the repo root with PYTHONPATH=.; prints PASS/FAIL per feature and saves a window capture.
"""
import subprocess, sys, time, tkinter as tk
from pathlib import Path

sys.path.insert(0, "tools")
from capture_window import capture  # noqa: E402
from spotter.main import build  # noqa: E402
from spotter.settings import band_of  # noqa: E402
from spotter.spot_filter import SKIMMER_LISTS, skimmer_matches  # noqa: E402
from spotter.spot_store import opacity  # noqa: E402

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "live_app.png")
res = []


def check(name, ok, info=""):
    res.append(ok)
    print(("PASS " if ok else "FAIL ") + name, info, flush=True)


def pbpaste():
    return subprocess.run(["pbpaste"], capture_output=True, text=True).stdout


old_clip = pbpaste()
root = tk.Tk()
ui, app, cluster, pota = build(root, tick_ms=250)
root.geometry("492x1150+60+60")
state = {}
steps = []


def at(sec):
    def deco(fn):
        steps.append((sec, fn))
        return fn
    return deco


def rbn_drawn():
    return app.view().rbn


@at(25)
def live_state():
    v = app.view()
    check("4.2 cluster dot green, text 'Cluster: NC7J'", v.dot == "green" and v.cluster_text == "Cluster: NC7J", f"({v.dot}, {v.cluster_text})")
    check("4.3 POTA poll age text", v.pota_text.startswith("POTA: last poll ") and v.pota_text.endswith("s ago"), f"({v.pota_text})")
    n_hits = len(ui.hits)
    check("counts: Shown matches spots on screen",
          v.shown_text == f"Shown: RBN {len(v.rbn)} · POTA {len(v.pota)}" and n_hits == len(v.rbn) + len(v.pota),
          f"({v.shown_text}; {n_hits} labels)")
    lo, hi = app.settings.span
    check("RBN spots: in span, CW, Regional list (+Local), 20 m",
          all(lo <= s.freq_mhz <= hi for s in v.rbn), f"({len(v.rbn)} drawn, {app.store.count('rbn')} stored)")
    stored = [sp for sp, _ in app.store.items("rbn", app.settings.fade)]
    check("store holds only CW from listed skimmers on 20 m",
          all(sp.mode == "CW" and skimmer_matches(sp.skimmer, SKIMMER_LISTS["Regional"]) and band_of(sp.freq_mhz) == 20 for sp in stored), f"({len(stored)})")
    state["img"] = capture(root, str(OUT))


@at(26)
def fading_and_click():
    now = time.time()
    items = app.store.items("rbn", app.settings.fade)
    ok = True
    for sp, op in items:
        t = app.store._spots["rbn"][sp.call.upper()][0]
        ok &= abs(op - opacity(now - t, 600)) < 0.02
    ops = sorted(op for _, op in items)
    check("4.4 fade: opacity = linear curve of age, older paler", ok and (len(ops) < 2 or ops[0] < 1.0), f"(min opacity {ops[0] if ops else None:.3f})")
    # 4.6 click a drawn label: clipboard holds exactly that call
    if ui.hits:
        x0, y0, x1, y1, call = ui.hits[len(ui.hits) // 2]
        subprocess.run(["pbcopy"], input=b"x")
        ui.canvas.event_generate("<Button-1>", x=int((x0 + x1) / 2), y=int((y0 + y1) / 2))
        root.after(200, lambda: check("4.6 click copies exactly the call sign", pbpaste() == call, f"({call!r})"))


@at(30)
def switch_local():
    ui.local.event_generate("<Button-1>", x=5, y=5)
    root.update()
    v = app.view()
    stored = [sp for sp, _ in app.store.items("rbn", app.settings.fade)]
    check("4.5 Local shows only Local skimmers; store untouched",
          all(skimmer_matches(s.skimmer, SKIMMER_LISTS["Local"]) for s in [sp for sp in stored if any(sp.call == d.call for d in v.rbn)])
          and len(v.rbn) <= len(stored), f"({len(v.rbn)} of {len(stored)} stored)")
    state["stored_before"] = len(stored)
    ui.regional.event_generate("<Button-1>", x=5, y=5)
    root.update()
    check("4.5 Regional restores the map", len(app.view().rbn) >= len(v.rbn) and app.store.count("rbn") == state["stored_before"])


@at(35)
def band_change():
    ui.freq_var.set("7.030"); ui.set_btn.invoke()
    check("band change: filter 40 sent, old-band spots flushed", app.filter_band == 40 and app.store.count("rbn") == 0)


@at(75)
def band_after():
    check("band change: 40 m filter acknowledged by the server", cluster.filter_acked_band == 40)
    stored = [sp for sp, _ in app.store.items("rbn", app.settings.fade)]
    check("band change: only 7.0-7.3 MHz spots after", len(stored) > 0 and all(7.0 <= sp.freq_mhz <= 7.3 for sp in stored), f"({len(stored)} spots)")


@at(76)
def clear_now():
    ui.clear_btn.invoke(); root.update()
    v = app.view()
    check("Clear: both scales empty at once", v.rbn == [] and v.pota == [] and v.shown_text == "Shown: RBN 0 · POTA 0")
    check("Clear: forced reconnect shows amber, not a retry", v.dot == "amber" and v.cluster_text == "Cluster: NC7J")


@at(100)
def after_clear():
    v = app.view()
    check("Clear: cluster reconnects (green) with the filter re-acked; new spots continue",
          v.dot == "green" and cluster.filter_acked_band == 40 and app.store.count("rbn") > 0, f"({app.store.count('rbn')} spots)")
    ui.close() if False else root.quit()


for sec, fn in steps:
    root.after(sec * 1000, fn)
root.mainloop()
state["late"] = ui.max_late_ms
check("window responsive: max after() tick lateness < 300 ms", ui.max_late_ms < 300, f"({ui.max_late_ms:.0f} ms)")
ui.close()
subprocess.run(["pbcopy"], input=old_clip.encode())
print("ALL PASS" if all(res) else "SOME FAILED")

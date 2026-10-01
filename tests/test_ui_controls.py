"""4.1 controls wired to settings, driven through the real widgets (needs a display)."""
import queue
import tkinter as tk

import pytest

from spotter.app import App
from spotter.models import RawLine, Status
from spotter.settings import Settings
from spotter.ui import SpotterUI
from tests.test_ui_guards import line, new_root, run_loop


def mk(root):
    q = queue.Queue()
    calls = {"band": [], "reconnect": 0}
    app = App(q, Settings(), send_band=calls["band"].append,
              reconnect=lambda: calls.__setitem__("reconnect", calls["reconnect"] + 1))
    ui = SpotterUI(root, app, tick_ms=100)
    root.geometry("492x1150+80+80")
    return q, app, ui, calls


def test_controls_drive_settings_and_redraw():
    root = new_root()
    q, app, ui, calls = mk(root)
    res = {}

    def act():
        # frequency: valid, within band
        ui.freq_var.set("14.060"); ui.set_btn.invoke()
        res["f_ok"] = (app.settings.frequency, ui.msg.cget("text"))
        # bad entries rejected, old value kept and shown again in the box
        for bad in ("abc", "31", "1.0"):
            ui.freq_var.set(bad); ui.set_btn.invoke()
        res["f_bad"] = (app.settings.frequency, ui.freq_var.get(), ui.msg.cget("text"))
        # bandwidth and window menus
        ui.bw_box.set("100"); ui.bw_box.event_generate("<<ComboboxSelected>>")
        ui.win_box.set("15"); ui.win_box.event_generate("<<ComboboxSelected>>")
        res["menus"] = (app.settings.bandwidth, app.settings.fade, ui.bw_box.cget("values"), ui.win_box.cget("values"))
        # spotter radio
        ui.local.event_generate("<Button-1>", x=5, y=5)
        res["radio"] = (app.settings.spotter, ui.spot_var.get())
        # Return key in the entry acts as Set; a different band changes the server filter
        ui.freq_var.set("7.030"); ui.freq_entry.focus_force(); root.update(); ui.freq_entry.event_generate("<Return>")
        res["band"] = (app.settings.frequency, list(calls["band"]))
        # outside any amateur band: warning shown, last filter kept
        ui.freq_var.set("5.35"); ui.set_btn.invoke(); root.update()
        res["warn"] = (ui.msg.cget("text"), list(calls["band"]))
        # Clear forces a reconnect
        ui.clear_btn.invoke()
        res["clear"] = calls["reconnect"]

    run_loop(root, [(500, act)], 800)
    root.destroy()
    assert res["f_ok"] == (14.06, "")
    assert res["f_bad"][0] == 14.06 and res["f_bad"][1] == "14.06" and res["f_bad"][2]
    assert res["menus"][:2] == (100, 15)
    assert tuple(res["menus"][2]) == ("10", "20", "40", "50", "80", "100") and tuple(res["menus"][3]) == ("5", "10", "15")
    assert res["radio"] == ("Local", "Local")
    assert res["band"] == (7.03, [40])
    assert "outside" in res["warn"][0] and res["warn"][1] == [40]
    assert res["clear"] == 1


def test_clear_empties_canvas_and_status_lines_follow():
    root = new_root()
    q, app, ui, calls = mk(root)
    res = {}
    q.put(line("K1AAA", 14030.0)); q.put(line("K1BBB", 14040.0)); q.put(Status("cluster", "connected", 0))

    def before():
        res["before"] = (len(ui.hits), ui.shown.cget("text"), ui.cluster.cget("text"))
        ui.clear_btn.invoke(); root.update()
        res["after"] = (len(ui.hits), ui.shown.cget("text"))
        q.put(line("K1CCC", 14050.0))

    def later():
        res["later"] = (len(ui.hits), ui.shown.cget("text"))

    run_loop(root, [(500, before), (900, later)], 1100)
    root.destroy()
    assert res["before"] == (2, "Shown: RBN 2 · POTA 0", "Cluster: NC7J")
    assert res["after"] == (0, "Shown: RBN 0 · POTA 0")
    assert res["later"] == (1, "Shown: RBN 1 · POTA 0")        # new spots continue

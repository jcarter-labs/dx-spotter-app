import json
import queue
from pathlib import Path

from spotter.app import App
from spotter.models import RawLine, RawRecords, Status

CAP = Path(__file__).resolve().parent / "captures"
POTA = json.loads((CAP / "pota_spots_raw.json").read_text())
LINES = [l for l in (CAP / "cluster_session.txt").read_text(errors="replace").splitlines() if l.startswith("DX de ")]


class Clock:
    t = 5000.0
    def __call__(self): return self.t


def mk(**kw):
    q, c = queue.Queue(), Clock()
    calls = {"band": [], "reconnect": 0}
    app = App(q, clock=c, send_band=calls["band"].append, reconnect=lambda: calls.__setitem__("reconnect", calls["reconnect"] + 1), **kw)
    return app, q, c, calls


def line(skim, f, call, mode="CW"):
    return RawLine(f"DX de {skim}:  {f}  {call}  {mode} 13 dB 28 WPM CQ  0007Z")


def test_rbn_filtering_and_one_label_per_call():
    app, q, c, _ = mk()
    for it in [line("WA7LNW-#", 14030.0, "K1AAA"),            # kept (Regional)
               line("W6YX-#", 14031.0, "K1BBB"),               # Local only: dropped
               line("WA7LNW-#", 14032.0, "K1CCC", "RTTY"),     # non-CW: dropped
               line("WA7LNW-#", 14090.0, "K1DDD"),             # stored, outside span: not drawn
               line("WA7LNW-#", 7030.0, "K1EEE"),              # other band: dropped
               RawLine("DX de garbage"),                       # bad line: skipped, no crash
               line("ND7K-#", 14040.0, "K1AAA")]:              # same call: newer frequency wins
        q.put(it)
    app.drain()
    v = app.view()
    assert {(d.call, round(d.freq_mhz, 3)) for d in v.rbn} == {("K1AAA", 14.040)}
    assert app.store.count("rbn") == 2 and app.rejected == 1
    assert v.shown_text == "Shown: RBN 1 · POTA 0"


def test_local_regional_switching():
    app, q, c, _ = mk()
    app.set_spotter("Local")
    q.put(line("W6YX-#", 14031.0, "K1BBB")); q.put(line("WA7LNW-#", 14032.0, "K1CCC")); app.drain()
    assert [d.call for d in app.view().rbn] == ["K1BBB"]
    app.set_spotter("Regional")
    q.put(line("W6YX-#", 14031.0, "K1BBB")); q.put(line("WA7LNW-#", 14032.0, "K1CCC")); app.drain()
    assert [d.call for d in app.view().rbn] == ["K1CCC"]


def test_pota_records_filter_and_counts_and_poll_age():
    app, q, c, _ = mk()
    assert app.view().pota_text == "POTA: not polled yet"
    q.put(RawRecords(POTA, c.t)); app.drain()
    cw_in_span = [r for r in POTA if r["mode"] == "CW" and 14.020 <= float(r["frequency"]) / 1000 <= 14.070]
    v = app.view()
    assert app.store.count("pota") == sum(1 for r in POTA if r["mode"] == "CW")
    assert len(v.pota) == len({r["activator"].upper() for r in cw_in_span})
    c.t += 57
    assert app.view().pota_text == "POTA: last poll 57s ago"
    # a failure keeps spots and the age keeps counting
    q.put(Status("pota", "error", 0, "timeout")); app.drain(); c.t += 3
    assert app.view().pota_text == "POTA: last poll 60s ago" and app.store.count("pota") > 0
    # repeated poll of the same reports does not reset their age
    q.put(RawRecords(POTA, c.t)); app.drain()
    assert all(d.opacity < 1.0 for d in app.view().pota) or not app.view().pota


def test_cluster_status_dot_and_retry_text():
    app, q, c, _ = mk()
    for st, dot, text in [(Status("cluster", "connected", 0), "green", "Cluster: NC7J"),
                          (Status("cluster", "disconnected", 0), "red", "Cluster: NC7J"),
                          (Status("cluster", "connecting", 2), "amber", "Cluster: NC7J (retry 2)"),
                          (Status("cluster", "connected", 0), "green", "Cluster: NC7J")]:
        q.put(st); app.drain(); v = app.view()
        assert (v.dot, v.cluster_text) == (dot, text)
    q.put(Status("pota", "error")); app.drain()
    assert app.view().dot == "green"                    # POTA failure does not touch the dot


def test_fade_drop_and_setting_applies_to_all():
    app, q, c, _ = mk()
    q.put(line("WA7LNW-#", 14030.0, "K1AAA")); q.put(RawRecords([POTA[i] for i in range(len(POTA)) if POTA[i]["mode"] == "CW" and 14.02 <= float(POTA[i]["frequency"]) / 1000 <= 14.07][:1], c.t)); app.drain()
    n = len(app.view().rbn) + len(app.view().pota); assert n >= 1
    c.t += 400
    assert app.view().rbn[0].opacity < 1
    app.set_fade(5)
    v = app.view(); assert v.rbn == [] and v.pota == [] and v.shown_text == "Shown: RBN 0 · POTA 0"


def test_frequency_band_rules():
    app, q, c, calls = mk()
    q.put(line("WA7LNW-#", 14030.0, "K1AAA")); app.drain()
    assert app.set_frequency("14.060")[0] and app.store.count("rbn") == 1 and calls["band"] == []   # same band: no flush
    assert app.set_bandwidth(100)[0] and calls["band"] == []
    assert app.set_frequency("5.35")[0] and app.view().warning and calls["band"] == []             # outside bands: warn, keep filter
    assert app.set_frequency("14.1")[0] and not app.view().warning and calls["band"] == []         # back in the filtered band
    assert app.set_frequency("7.03")[0] and calls["band"] == [40] and app.store.count("rbn") == 0  # new band: filter + flush
    assert not app.set_frequency("abc")[0] and app.settings.frequency == 7.03                       # rejected, old kept
    q.put(line("WA7LNW-#", 14030.0, "K1ZZZ")); q.put(line("WA7LNW-#", 7030.0, "K1YYY")); app.drain()
    assert app.store.count("rbn") == 1                                                             # late old-band spot dropped


def test_clear_empties_both_and_reconnects():
    app, q, c, calls = mk()
    q.put(line("WA7LNW-#", 14030.0, "K1AAA")); q.put(RawRecords(POTA, c.t)); app.drain()
    q.put(Status("cluster", "connected", 0)); app.drain()
    app.clear()
    v = app.view()
    assert app.store.count("rbn") == app.store.count("pota") == 0 and calls["reconnect"] == 1
    assert v.dot == "amber" and v.cluster_text == "Cluster: NC7J"       # amber, not a retry
    q.put(line("WA7LNW-#", 14031.0, "K1BBB")); app.drain()
    assert len(app.view().rbn) == 1                                       # new spots continue


def test_saved_captures_through_the_app():
    app, q, c, _ = mk()
    for l in LINES: q.put(RawLine(l))
    q.put(RawLine("truncated DX de")); q.put(RawLine("DX de W6"))
    q.put(RawRecords(POTA, c.t)); app.drain()
    assert app.rejected == 2                                              # both bad lines skipped
    assert app.store.count("rbn") > 0 and app.store.count("pota") == 10

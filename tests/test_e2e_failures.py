"""5.3 failure tests through the whole app (fake cluster, faked HTTP, real window)."""
import time

import requests

from spotter.main import build
from tests.fake_cluster import FakeCluster
from tests.test_pota_client import RAW, Resp
from tests.test_ui_guards import new_root


def test_cluster_drop_and_pota_failure_keep_app_alive():
    root = new_root()
    fake = FakeCluster()
    pota_ok = {"v": True}

    def get(url, timeout):
        if not pota_ok["v"]:
            raise requests.Timeout("down")
        return Resp(RAW)

    ui, app, cluster, pota = build(
        root, cluster_kw=dict(host="127.0.0.1", port=fake.port, backoff=(0.3, 0.3, 0.3), login_timeout=2.0),
        pota_kw=dict(interval=0.4, get=get), tick_ms=50)
    root.geometry("492x1150+80+80")
    seen, res, states = [], {}, []
    orig = app._status
    app._status = lambda st: (states.append((st.state, st.retry)) if st.source == "cluster" else None, orig(st))   # every status the app applied

    def sample():
        v = app.view()
        seen.append((v.dot, v.cluster_text))
        root.after(40, sample)

    def drop():
        res["before"] = (app.view().dot, app.store.count("pota"))
        pota_ok["v"] = False
        fake.drop_all()

    def after_drop():
        v = app.view()
        res["pota_kept"] = app.store.count("pota") == res["before"][1] > 0
        res["poll_age_grows"] = v.pota_text
        pota_ok["v"] = True

    def end():
        res["end"] = app.view()
        root.quit()

    root.after(50, sample)
    root.after(1500, drop)
    root.after(2400, after_drop)
    root.after(4500, end)
    root.mainloop()
    try:
        assert res["before"][0] == "green"
        assert ("disconnected", 0) in states and ("connecting", 1) in states   # red, then amber with retry 1
        assert states.index(("disconnected", 0)) < states.index(("connecting", 1))
        assert [d for d, _ in seen].count("red") > 0                  # the red dot was really on screen
        assert states[-1] == ("connected", 0)
        assert res["pota_kept"]                                       # a POTA failure keeps old spots
        assert res["poll_age_grows"].startswith("POTA: last poll ") and "not polled" not in res["poll_age_grows"]
        assert res["end"].dot == "green" and res["end"].cluster_text == "Cluster: NC7J"   # back to green, retry reset
        assert fake.logins >= 2
    finally:
        ui.close()
        fake.close()

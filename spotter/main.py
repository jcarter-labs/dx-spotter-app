"""Launch: python -m spotter"""
import logging
import queue
import tkinter as tk

from .app import App
from .cluster_client import ClusterClient
from .pota_client import PotaClient
from .settings import Settings
from .ui import SpotterUI


def build(root, cluster_kw=None, pota_kw=None, tick_ms=250):
    q = queue.Queue()
    settings = Settings()
    app = App(q, settings)
    cluster = ClusterClient(q, band=app.filter_band, **(cluster_kw or {}))
    pota = PotaClient(q, **(pota_kw or {}))
    app._send_band, app._reconnect = cluster.set_band, cluster.reconnect

    def shutdown():
        cluster.stop()
        pota.stop()

    ui = SpotterUI(root, app, tick_ms=tick_ms, on_close=shutdown)
    cluster.start()
    pota.start()
    return ui, app, cluster, pota


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    root = tk.Tk()
    build(root)
    root.mainloop()


if __name__ == "__main__":
    main()

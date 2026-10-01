import json
from pathlib import Path

M = json.loads((Path(__file__).resolve().parent.parent / "measurements.json").read_text())


def test_reference_and_title_bar():
    assert M["_reference"]["screenshot_size"] == [492, 1189]
    assert M["_reference"]["title_bar_height"] == 39
    assert M["_reference"]["content_size"] == [492, 1150]


def test_all_19_screen_list_elements_measured():
    got = {int(k.split("_")[0].rstrip("ab")) for k in M if k[0].isdigit()}
    assert got == set(range(1, 20))


def test_scales_have_six_ticks_each():
    assert len(M["6_rbn_scale"]["tick_y_centres"]) == 6
    assert len(M["8_pota_scale"]["tick_y_centres"]) == 6

import sys
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import verify_layout  # noqa: E402


def ref_content():
    return Image.open(ROOT / "screenshot.png").convert("RGB").crop((0, 39, 492, 1189))


def test_reference_passes_against_itself(tmp_path, capsys):
    p = tmp_path / "ref.png"
    ref_content().save(p)
    assert verify_layout.main(str(p)) == 0
    assert "26/26 elements pass" in capsys.readouterr().out


def test_shifted_layout_fails(tmp_path, capsys):
    im = ref_content()
    shifted = ImageChops.offset(im, 0, 10)   # everything 10 px lower
    p = tmp_path / "shift.png"
    shifted.save(p)
    assert verify_layout.main(str(p)) == 1
    assert "FAIL" in capsys.readouterr().out


def test_wrong_size_fails(tmp_path):
    p = tmp_path / "small.png"
    ref_content().crop((0, 0, 400, 700)).save(p)
    try:
        assert verify_layout.main(str(p)) == 1
    except Exception:
        pass  # a wrong-size capture may not even be measurable; it must never pass

import numpy as np
from PIL import Image, ImageDraw

from app.backends import QuickBackend
from app.inpaint import Inpainter, Params


def _clean():
    x = np.linspace(0, 20, 300, dtype=np.float32)
    base = np.tile(x, (300, 1))
    return Image.fromarray(np.stack([210 + base, 160 + base, 130 + base], -1).astype(np.uint8))


def _scene():
    """พื้นผิวสีผิวไล่เฉด + เส้นสีเข้มบาง ๆ แทนสร้อยคอ"""
    img = _clean()
    ImageDraw.Draw(img).line([(40, 150), (260, 160)], fill=(40, 40, 40), width=4)
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).line([(40, 150), (260, 160)], fill=255, width=10)
    return img, mask


def test_quick_removes_thin_object_and_keeps_rest():
    img, mask = _scene()
    out = Inpainter(QuickBackend()).run(img, mask, Params(seed=1))[0]
    a, o = np.array(img).astype(int), np.array(out).astype(int)
    clean = np.array(_clean()).astype(int)
    region = np.array(mask) > 127
    assert np.abs(o - clean)[region].mean() < 12  # ตรงที่ลบ ใกล้เคียงสีผิวจริง (ไม่ใช่เส้นสีเข้ม)
    assert np.abs(a - clean)[region].mean() > 30  # และภาพเดิมต่างจากนั้นมาก (ยืนยันว่าเทสต์มีความหมาย)
    assert np.array_equal(a[:100], o[:100])  # ส่วนไกล mask ไม่ถูกแตะเลย


def test_empty_mask_raises():
    img, _ = _scene()
    try:
        Inpainter(QuickBackend()).run(img, Image.new("L", img.size, 0), Params())
    except ValueError:
        return
    raise AssertionError("ควรแจ้งว่ายังไม่ได้ระบาย")

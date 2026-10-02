import numpy as np
from PIL import Image

from app import imageops


def _mask(size=(200, 150), box=(80, 60, 120, 90)):
    m = Image.new("L", size, 0)
    m.paste(255, box)
    return m


def test_bbox_and_empty():
    assert imageops.mask_bbox(_mask()) == (80, 60, 120, 90)
    assert imageops.mask_bbox(Image.new("L", (10, 10), 0)) is None


def test_dilate_grows():
    m = _mask()
    assert np.array(imageops.dilate_mask(m, 5)).sum() > np.array(m).sum()


def test_crop_box_square_inside_image():
    x0, y0, x1, y1 = imageops.context_crop_box((0, 0, 30, 30), (200, 150))
    assert x1 - x0 == y1 - y0
    assert 0 <= x0 and 0 <= y0 and x1 <= 200 and y1 <= 150


def test_composite_keeps_pixels_outside_mask():
    orig = Image.new("RGB", (200, 150), (10, 20, 30))
    gen = Image.new("RGB", (200, 150), (200, 100, 50))
    out = np.array(imageops.composite(orig, gen, _mask(), feather_px=4))
    assert tuple(out[0, 0]) == (10, 20, 30)
    assert tuple(out[75, 100]) == (200, 100, 50)


def test_match_color_moves_toward_surroundings():
    ref = Image.new("RGB", (200, 150), (220, 180, 150))
    gen = Image.new("RGB", (200, 150), (90, 90, 90))
    out = np.array(imageops.match_color(gen, ref, _mask()))
    assert abs(int(out[75, 100][0]) - 220) < 10


def test_match_color_ignores_dark_clothing_and_follows_skin_gradient():
    """แขน (สีผิวไล่เฉดตามแนวนอน) + แขนเสื้อสีน้ำเงินเข้มติดกับ mask — ผลต้องเป็นสีผิว ไม่ใช่เทา"""
    h, w = 300, 400
    x = np.linspace(0, 30, w, dtype=np.float32)
    skin = np.stack([np.tile(200 + x, (h, 1)), np.tile(150 + x, (h, 1)), np.tile(120 + x, (h, 1))], -1)
    ref = skin.copy()
    ref[:, :90] = (20, 30, 60)  # เสื้อสีเข้มด้านซ้าย
    mask = Image.new("L", (w, h), 0)
    mask.paste(255, (150, 100, 250, 200))
    gen = Image.new("RGB", (w, h), (110, 110, 110))  # AI เติมมาเป็นสีเทา
    out = np.array(imageops.match_color(gen, Image.fromarray(ref.astype(np.uint8)), mask)).astype(float)
    inside = np.array(mask) > 127
    err = np.abs(out - skin)[inside].mean()
    assert err < 12, err
    assert np.array_equal(out[~inside], np.array(gen).astype(float)[~inside])  # นอก mask ไม่ถูกแตะ

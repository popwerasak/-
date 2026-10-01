"""งานภาพล้วน ๆ (ไม่พึ่ง GPU/โมเดล) เพื่อให้ทดสอบได้"""
from __future__ import annotations

import cv2
import numpy as np
from PIL import Image


def dilate_mask(mask: Image.Image, px: int) -> Image.Image:
    """ขยาย mask เพื่อครอบเงา/ขอบที่ตกค้าง"""
    if px <= 0:
        return mask
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * px + 1, 2 * px + 1))
    return Image.fromarray(cv2.dilate(np.array(mask.convert("L")), k))


def mask_bbox(mask: Image.Image) -> tuple[int, int, int, int] | None:
    """(left, top, right, bottom) ของส่วนที่ระบายไว้ หรือ None ถ้าว่าง"""
    return mask.convert("L").point(lambda v: 255 if v > 127 else 0).getbbox()


def context_crop_box(
    bbox: tuple[int, int, int, int], size: tuple[int, int], context: float = 0.6, min_side: int = 256
) -> tuple[int, int, int, int]:
    """กรอบสี่เหลี่ยมจัตุรัสรอบ mask + บริบท (ให้โมเดลเห็นข้อมือ/ขา/แสงรอบ ๆ) ไม่เกินขอบภาพ"""
    w, h = size
    l, t, r, b = bbox
    side = int(max(r - l, b - t) * (1 + 2 * context))
    side = min(max(side, min_side), min(w, h))
    cx, cy = (l + r) // 2, (t + b) // 2
    x0 = int(np.clip(cx - side // 2, 0, w - side))
    y0 = int(np.clip(cy - side // 2, 0, h - side))
    return x0, y0, x0 + side, y0 + side


def feather(mask: Image.Image, radius: int) -> Image.Image:
    if radius <= 0:
        return mask.convert("L")
    r = radius * 2 + 1
    return Image.fromarray(cv2.GaussianBlur(np.array(mask.convert("L")), (r, r), 0))


def composite(original: Image.Image, generated: Image.Image, mask: Image.Image, feather_px: int = 6) -> Image.Image:
    """วางผลลัพธ์ทับภาพเดิมเฉพาะในพื้นที่ mask (ขอบนุ่ม) ส่วนที่เหลือคงพิกเซลเดิม 100%"""
    soft = feather(mask, feather_px)
    return Image.composite(generated.convert("RGB"), original.convert("RGB"), soft)


def match_color(generated: Image.Image, reference: Image.Image, mask: Image.Image) -> Image.Image:
    """ปรับค่าเฉลี่ย/ส่วนเบี่ยงเบนสีของผลลัพธ์ให้ใกล้ผิวรอบ ๆ mask (วงแหวนนอก mask)"""
    g = np.asarray(generated.convert("RGB"), dtype=np.float32)
    ref = np.asarray(reference.convert("RGB"), dtype=np.float32)
    m = np.array(mask.convert("L")) > 127
    ring = cv2.dilate(m.astype(np.uint8), np.ones((31, 31), np.uint8)).astype(bool) & ~m
    if m.sum() < 16 or ring.sum() < 16:
        return generated
    out = g.copy()
    for c in range(3):
        gm, gs = g[..., c][m].mean(), g[..., c][m].std() + 1e-6
        rm, rs = ref[..., c][ring].mean(), ref[..., c][ring].std() + 1e-6
        out[..., c][m] = (g[..., c][m] - gm) * min(rs / gs, 1.5) + rm
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))

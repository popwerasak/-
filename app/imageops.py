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


def _skin_pixels(rgb: np.ndarray) -> np.ndarray:
    """ตัวกรองสีผิวแบบง่าย (YCrCb) — ไม่เอาเสื้อผ้า/พื้นหลัง/คราบดำมาปนเป็นสีอ้างอิง"""
    ycc = cv2.cvtColor(rgb, cv2.COLOR_RGB2YCrCb)
    y, cr, cb = ycc[..., 0], ycc[..., 1], ycc[..., 2]
    return (y > 50) & (cr >= 133) & (cr <= 180) & (cb >= 77) & (cb <= 135)


def _smooth_field(img: np.ndarray, weight: np.ndarray, sigma: float) -> np.ndarray:
    """ค่าเฉลี่ยแบบถ่วงน้ำหนักเฉพาะพิกเซลอ้างอิง ไล่เฉดต่อเนื่องเข้าไปในพื้นที่ที่ไม่มีอ้างอิง"""
    out = None
    for k in (1, 3, 9):  # ขยาย sigma จนครอบคลุมทั้ง mask
        num = cv2.GaussianBlur(img * weight[..., None], (0, 0), sigma * k)
        den = cv2.GaussianBlur(weight, (0, 0), sigma * k)[..., None]
        field = num / np.maximum(den, 1e-6)
        out = field if out is None else np.where(den > 0.03, out, field)
        if (den > 0.03).all():
            break
    return out


def match_color(generated: Image.Image, reference: Image.Image, mask: Image.Image) -> Image.Image:
    """ปรับสี/แสงต่ำความถี่ของส่วนที่เติม ให้ต่อเนื่องกับสีผิวรอบ ๆ (เก็บรายละเอียดผิวที่ AI สร้างไว้)

    out = generated − blur(generated) + ค่าสีผิวรอบ ๆ ที่ไล่เฉดเข้ามา  (เฉพาะใน mask)
    """
    g = np.asarray(generated.convert("RGB"), dtype=np.float32)
    ref8 = np.asarray(reference.convert("RGB"), dtype=np.uint8)
    m = np.array(mask.convert("L")) > 127
    if m.sum() < 16:
        return generated

    near = cv2.dilate(m.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0  # เว้นขอบ mask กันเงา/คราบ
    usable = ~near
    w = (usable & _skin_pixels(ref8)).astype(np.float32)
    if w.sum() < 200:  # ไม่มีสีผิวรอบ ๆ (เช่น ลบของบนพื้นหลัง) → ใช้ทุกพิกเซลที่ไม่มืดจัด
        w = (usable & (ref8.mean(-1) > 40)).astype(np.float32)
    if w.sum() < 50:
        return generated

    sigma = max(min(g.shape[:2]) / 8, 8.0)
    target = _smooth_field(ref8.astype(np.float32), w, sigma)
    low = cv2.GaussianBlur(g, (0, 0), sigma)
    fixed = np.clip(g - low + target, 0, 255)
    out = g.copy()
    out[m] = fixed[m]
    return Image.fromarray(out.astype(np.uint8))

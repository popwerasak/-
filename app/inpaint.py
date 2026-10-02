"""ลำดับงาน: dilate mask → ครอปรอบ mask + บริบท → ให้ backend เติม → ปรับสี → วางกลับ"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PIL import Image

from . import imageops
from .backends import Backend

AUTO_PROMPT = "natural seamless continuation of the surrounding area, photorealistic, same lighting and texture"
AUTO_NEGATIVE = "object, text, watermark, deformed, blurry, artifacts, duplicate"

# ชื่อ → (prompt, negative) ว่าง = ใช้ค่าอัตโนมัติ (เติมสิ่งที่ควรอยู่ตรงนั้นตามบริเวณรอบ ๆ)
PRESETS = {
    "ลบอัตโนมัติ (เติมตามรอบ ๆ)": ("", ""),
    "สร้อยคอ → ผิวคอ": ("bare neck, natural skin, photorealistic, same lighting", "necklace, chain, pendant, jewelry, collar, deformed"),
    "นาฬิกา → ข้อมือเปล่า": ("bare wrist, natural skin, photorealistic, same lighting", "watch, bracelet, jewelry, strap, band, deformed"),
    "รองเท้า → เท้าเปล่า": ("bare foot, barefoot, natural skin, toes, photorealistic, same lighting", "shoes, socks, sandals, boots, extra toes, deformed foot, fused toes"),
    "กำหนดเอง": ("", ""),
}


@dataclass
class Params:
    prompt: str = ""
    negative: str = ""
    mask_grow: int = 14
    steps: int = 20
    guidance: float = 7.5
    strength: float = 1.0
    seed: int | None = None
    variants: int = 1
    res: int = 512  # ความละเอียดภายในของโมเดล AI (เล็กลง = เร็วขึ้น)


class Inpainter:
    def __init__(self, backend: Backend):
        self.backend = backend

    def run(self, image: Image.Image, mask: Image.Image, p: Params, progress: Callable[[str], None] = lambda s: None) -> list[Image.Image]:
        p = Params(**{**p.__dict__, "prompt": p.prompt.strip() or AUTO_PROMPT, "negative": p.negative.strip() or AUTO_NEGATIVE})
        image = image.convert("RGB")
        mask = imageops.dilate_mask(mask.convert("L"), p.mask_grow)
        bbox = imageops.mask_bbox(mask)
        if bbox is None:
            raise ValueError("ยังไม่ได้ระบายส่วนที่ต้องการลบ")

        box = imageops.context_crop_box(bbox, image.size)
        crop, crop_mask = image.crop(box), mask.crop(box)

        results = []
        for out in self.backend.generate(crop, crop_mask, p, progress):
            if self.backend.needs_color_match:
                out = imageops.match_color(out, crop, crop_mask)
            patched = imageops.composite(crop, out, crop_mask)
            full = image.copy()
            full.paste(patched, box[:2])
            results.append(full)
        return results

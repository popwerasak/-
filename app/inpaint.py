"""ตัวเติมภาพ (inpaint) ทำงานในเครื่อง 100% — โหลดโมเดลจากโฟลเดอร์/แคชในเครื่อง"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PIL import Image

from . import imageops
from .device import detect_device

PRESETS = {
    "นาฬิกา → ข้อมือเปล่า": ("bare wrist, natural skin, photorealistic, same lighting", "watch, bracelet, jewelry, strap, band, tattoo"),
    "รองเท้า → เท้าเปล่า": ("bare foot, barefoot, natural skin, toes, photorealistic, same lighting", "shoes, socks, sandals, boots, extra toes, deformed foot, fused toes"),
    "กำหนดเอง": ("", ""),
}

MODELS = {
    # SD1.5: เบา (4–6GB) เหมาะ AMD ทุกรุ่น / SDXL: คุณภาพดีกว่า ใช้ VRAM 8GB+
    "SD 1.5 Inpainting (เบา)": ("stable-diffusion-v1-5/stable-diffusion-inpainting", 512, False),
    "SDXL Inpainting (คุณภาพสูง)": ("diffusers/stable-diffusion-xl-1.0-inpainting-0.1", 1024, True),
}


@dataclass
class Params:
    prompt: str
    negative: str
    mask_grow: int = 12
    steps: int = 30
    guidance: float = 7.5
    strength: float = 0.99
    seed: int | None = None
    variants: int = 1


class Inpainter:
    def __init__(self, model_key: str, model_path: str | None = None, offline: bool = False, device_pref: str = "auto"):
        self.repo, self.res, self.is_xl = MODELS[model_key]
        self.model_path = model_path or self.repo
        self.offline = offline
        self.dev = detect_device(device_pref)
        self.pipe = None

    def load(self, progress: Callable[[str], None] = lambda s: None):
        import torch
        from diffusers import AutoPipelineForInpainting

        progress(f"กำลังโหลดโมเดลบน {self.dev.label} ...")
        dtype = getattr(torch, self.dev.dtype_name)
        self.pipe = AutoPipelineForInpainting.from_pretrained(
            self.model_path, torch_dtype=dtype, local_files_only=self.offline
        )
        self.pipe.to(self.dev.device)
        if self.dev.device == "cuda":
            self.pipe.enable_attention_slicing()  # ลด VRAM
            if hasattr(self.pipe, "enable_vae_tiling"):
                self.pipe.enable_vae_tiling()
        progress("โมเดลพร้อมใช้งาน")

    def run(self, image: Image.Image, mask: Image.Image, p: Params, progress: Callable[[str], None] = lambda s: None) -> list[Image.Image]:
        import torch

        if self.pipe is None:
            self.load(progress)
        image = image.convert("RGB")
        mask = imageops.dilate_mask(mask.convert("L"), p.mask_grow)
        bbox = imageops.mask_bbox(mask)
        if bbox is None:
            raise ValueError("ยังไม่ได้ระบายส่วนที่ต้องการลบ")

        box = imageops.context_crop_box(bbox, image.size)
        crop, crop_mask = image.crop(box), mask.crop(box)
        side = crop.size[0]
        inp = crop.resize((self.res, self.res), Image.LANCZOS)
        inp_mask = crop_mask.resize((self.res, self.res), Image.NEAREST)

        results = []
        for i in range(p.variants):
            progress(f"กำลังสร้างผลลัพธ์ {i + 1}/{p.variants} ...")
            gen = torch.Generator("cpu")
            if p.seed is not None:
                gen.manual_seed(p.seed + i)
            out = self.pipe(
                prompt=p.prompt, negative_prompt=p.negative, image=inp, mask_image=inp_mask,
                height=self.res, width=self.res, num_inference_steps=p.steps,
                guidance_scale=p.guidance, strength=p.strength, generator=gen,
            ).images[0].resize((side, side), Image.LANCZOS)
            out = imageops.match_color(out, crop, crop_mask)
            patched = imageops.composite(crop, out, crop_mask)
            full = image.copy()
            full.paste(patched, box[:2])
            results.append(full)
        return results

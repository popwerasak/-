"""ตัวเติมภาพแบบเปลี่ยนได้: Quick (OpenCV ไม่ใช้ AI) และ Diffusers (AI ในเครื่อง)"""
from __future__ import annotations

import os
from typing import Callable

import cv2
import numpy as np
from PIL import Image

Progress = Callable[[str], None]


class Backend:
    needs_color_match = False

    def load(self, progress: Progress) -> None:
        pass

    def generate(self, image: Image.Image, mask: Image.Image, p, progress: Progress) -> list[Image.Image]:
        """image/mask คือส่วนที่ครอปมาแล้ว (ขนาดเท่ากัน) คืนภาพเติมแล้วขนาดเดิม"""
        raise NotImplementedError


class QuickBackend(Backend):
    """เร็ว ไม่ใช้โมเดล เหมาะกับของเล็ก/บาง (สร้อย ข้อความ รอยเปื้อน) บนพื้นเรียบ"""

    def generate(self, image, mask, p, progress):
        progress("กำลังเติมภาพแบบเร็ว ...")
        rgb = np.array(image.convert("RGB"))
        m = (np.array(mask.convert("L")) > 127).astype(np.uint8) * 255
        radius = max(3, int(round(min(image.size) / 60)))
        out = cv2.inpaint(rgb, m, radius, cv2.INPAINT_TELEA).astype(np.float32)

        # เติมเกรนให้เท่าพื้นผิวรอบ ๆ ไม่ให้ดูเป็นพลาสติกเรียบ
        ring = cv2.dilate(m, np.ones((31, 31), np.uint8)) > 0
        ring &= m == 0
        if ring.sum() > 16:
            gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
            noise_std = float(np.std(gray[ring] - cv2.GaussianBlur(gray, (0, 0), 2)[ring]))
            rng = np.random.default_rng(p.seed if p.seed is not None else 0)
            out[m > 0] += rng.normal(0, noise_std, (int((m > 0).sum()), 1))
        return [Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))]


class DiffusersBackend(Backend):
    needs_color_match = True

    def __init__(self, model_path: str, offline: bool, device_pref: str = "auto"):
        self.model_path, self.offline, self.device_pref = model_path, offline, device_pref
        self.pipe = None
        self.dev = None

    def load(self, progress: Progress) -> None:
        import torch
        from diffusers import AutoPipelineForInpainting

        from .device import detect_device

        self.dev = detect_device(self.device_pref)
        progress(f"กำลังโหลดโมเดลบน {self.dev.label} (ครั้งแรกอาจใช้เวลาสักครู่) ...")
        dtype = getattr(torch, self.dev.dtype_name)
        kw = dict(torch_dtype=dtype, local_files_only=self.offline, safety_checker=None, requires_safety_checker=False)
        try:
            self.pipe = AutoPipelineForInpainting.from_pretrained(self.model_path, variant="fp16", **kw)
        except (OSError, ValueError):
            self.pipe = AutoPipelineForInpainting.from_pretrained(self.model_path, **kw)
        self.pipe.to(self.dev.device)
        self.pipe.enable_attention_slicing()  # ลดการใช้ RAM
        if hasattr(self.pipe, "enable_vae_tiling"):
            self.pipe.enable_vae_tiling()
        if self.dev.device == "cpu":
            torch.set_num_threads(os.cpu_count() or 4)
        progress("โหลดโมเดลเสร็จแล้ว")

    def generate(self, image, mask, p, progress):
        import torch

        if self.pipe is None:
            self.load(progress)
        side = image.size[0]
        inp = image.resize((p.res, p.res), Image.LANCZOS)
        inp_mask = mask.resize((p.res, p.res), Image.NEAREST)
        results = []
        for i in range(p.variants):
            progress(f"กำลังสร้างผลลัพธ์ {i + 1}/{p.variants} (อาจใช้เวลาหลายนาทีบนเครื่องที่ไม่มีการ์ดจอแยก) ...")
            gen = torch.Generator("cpu")
            if p.seed is not None:
                gen.manual_seed(p.seed + i)
            out = self.pipe(
                prompt=p.prompt, negative_prompt=p.negative, image=inp, mask_image=inp_mask,
                height=p.res, width=p.res, num_inference_steps=p.steps,
                guidance_scale=p.guidance, strength=p.strength, generator=gen,
            ).images[0]
            results.append(out.resize((side, side), Image.LANCZOS))
        return results

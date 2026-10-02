"""ดาวน์โหลดโมเดล inpainting มาเก็บในเครื่องครั้งเดียว (ต้องใช้อินเทอร์เน็ตแค่ตอนนี้)

    python tools/download_model.py                 # -> models/sd15-inpaint
    python tools/download_model.py --repo ชื่อ/repo --out models/ชื่อโฟลเดอร์
"""
import argparse
from pathlib import Path

from huggingface_hub import snapshot_download

CONFIG = ["*.json", "*.txt", "tokenizer/*"]
FP16 = CONFIG + ["*.fp16.safetensors"]
FULL = CONFIG + ["*.safetensors"]
SKIP = ["safety_checker/*", "*.ckpt", "*.bin", "*.msgpack", "*.onnx*", "*.pt"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="stable-diffusion-v1-5/stable-diffusion-inpainting")
    ap.add_argument("--out", default="models/sd15-inpaint")
    a = ap.parse_args()
    out = Path(a.out)
    snapshot_download(a.repo, local_dir=out, allow_patterns=FP16, ignore_patterns=SKIP)
    if not list(out.glob("unet/*.safetensors")):  # repo นี้ไม่มีไฟล์ fp16 → โหลดไฟล์เต็ม
        snapshot_download(a.repo, local_dir=out, allow_patterns=FULL, ignore_patterns=SKIP)
    print(f"เสร็จแล้ว: {out.resolve()}  (ใส่โฟลเดอร์นี้ในช่อง 'โฟลเดอร์โมเดล' ของโปรแกรม)")


if __name__ == "__main__":
    main()

"""เลือกอุปกรณ์คำนวณ: AMD ROCm (torch.cuda API), DirectML (Windows), หรือ CPU"""
from dataclasses import dataclass


@dataclass
class DeviceInfo:
    device: object  # str หรือ torch.device
    dtype_name: str  # "float16" | "float32"
    label: str


def detect_device(prefer: str = "auto") -> DeviceInfo:
    import torch

    if prefer in ("auto", "gpu") and torch.cuda.is_available():
        # PyTorch ROCm (Linux) แสดงตัวเองผ่าน API ของ cuda
        kind = "AMD ROCm" if getattr(torch.version, "hip", None) else "CUDA"
        return DeviceInfo("cuda", "float16", f"{kind}: {torch.cuda.get_device_name(0)}")

    if prefer in ("auto", "gpu"):
        try:
            import torch_directml  # Windows + การ์ด AMD

            return DeviceInfo(torch_directml.device(), "float32", "DirectML (AMD/Windows)")
        except ImportError:
            pass

    return DeviceInfo("cpu", "float32", "CPU (ช้า)")

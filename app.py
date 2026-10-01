"""แอพสร้างภาพด้วย AI ที่รันในเครื่องเราเองทั้งหมด (Stable Diffusion ผ่าน diffusers + Gradio)

ดาวน์โหลดโมเดลครั้งแรกครั้งเดียว หลังจากนั้นใช้งานออฟไลน์ได้ ไม่ส่งข้อมูลไปที่ AI ภายนอก
"""
import os
import time
from datetime import datetime

import gradio as gr
import torch
from diffusers import AutoPipelineForText2Image

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ชื่อที่แสดง -> (repo โมเดล, steps แนะนำ, guidance แนะนำ)
MODELS = {
    "SD-Turbo (เร็ว เหมาะกับเครื่องทั่วไป/CPU)": ("stabilityai/sd-turbo", 2, 0.0),
    "SD 1.5 (คุณภาพดีขึ้น ช้ากว่า)": ("stable-diffusion-v1-5/stable-diffusion-v1-5", 25, 7.5),
}

if torch.cuda.is_available():
    DEVICE, DTYPE = "cuda", torch.float16
elif torch.backends.mps.is_available():
    DEVICE, DTYPE = "mps", torch.float16
else:
    DEVICE, DTYPE = "cpu", torch.float32

_pipe_cache = {}


def get_pipe(model_label):
    repo = MODELS[model_label][0]
    if repo not in _pipe_cache:
        _pipe_cache.clear()  # เก็บโมเดลในหน่วยความจำทีละตัวเพื่อประหยัด RAM/VRAM
        pipe = AutoPipelineForText2Image.from_pretrained(repo, torch_dtype=DTYPE)
        pipe = pipe.to(DEVICE)
        pipe.enable_attention_slicing()
        _pipe_cache[repo] = pipe
    return _pipe_cache[repo]


def generate(prompt, negative, model_label, steps, guidance, width, height, seed, count):
    if not prompt.strip():
        raise gr.Error("กรุณาใส่ prompt (แนะนำเป็นภาษาอังกฤษ)")
    pipe = get_pipe(model_label)
    seed = int(seed)
    if seed < 0:
        seed = int(torch.randint(0, 2**31 - 1, (1,)).item())

    images = []
    start = time.time()
    for i in range(int(count)):
        gen = torch.Generator(device="cpu").manual_seed(seed + i)
        kwargs = dict(
            prompt=prompt,
            num_inference_steps=int(steps),
            guidance_scale=float(guidance),
            width=int(width),
            height=int(height),
            generator=gen,
        )
        if float(guidance) > 1.0 and negative.strip():
            kwargs["negative_prompt"] = negative
        img = pipe(**kwargs).images[0]
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        img.save(os.path.join(OUTPUT_DIR, f"{stamp}-seed{seed + i}.png"))
        images.append(img)
    info = f"อุปกรณ์: {DEVICE} | seed เริ่มต้น: {seed} | ใช้เวลา {time.time() - start:.1f} วินาที | บันทึกที่ ./{OUTPUT_DIR}"
    return images, info


def on_model_change(label):
    _, steps, guidance = MODELS[label]
    return steps, guidance


with gr.Blocks(title="Local Image Generator") as demo:
    gr.Markdown(f"# สร้างภาพด้วย AI ในเครื่องเรา\nรันบน **{DEVICE.upper()}** · ไม่ใช้ AI ภายนอก")
    with gr.Row():
        with gr.Column():
            prompt = gr.Textbox(label="Prompt (ภาษาอังกฤษให้ผลดีที่สุด)", lines=3,
                                placeholder="a cozy wooden cabin in snowy mountains, sunrise, detailed")
            negative = gr.Textbox(label="Negative prompt (ใช้กับ SD 1.5)", value="blurry, low quality, deformed")
            model = gr.Dropdown(list(MODELS), value=list(MODELS)[0], label="โมเดล")
            with gr.Row():
                steps = gr.Slider(1, 50, value=2, step=1, label="Steps")
                guidance = gr.Slider(0, 15, value=0.0, step=0.5, label="Guidance")
            with gr.Row():
                width = gr.Dropdown([256, 384, 512, 640, 768], value=512, label="กว้าง")
                height = gr.Dropdown([256, 384, 512, 640, 768], value=512, label="สูง")
            with gr.Row():
                seed = gr.Number(value=-1, precision=0, label="Seed (-1 = สุ่ม)")
                count = gr.Slider(1, 4, value=1, step=1, label="จำนวนภาพ")
            btn = gr.Button("สร้างภาพ", variant="primary")
        with gr.Column():
            gallery = gr.Gallery(label="ผลลัพธ์", columns=2)
            info = gr.Markdown()
    model.change(on_model_change, model, [steps, guidance])
    btn.click(generate, [prompt, negative, model, steps, guidance, width, height, seed, count], [gallery, info])

if __name__ == "__main__":
    # 127.0.0.1 = เข้าได้จากเครื่องนี้เท่านั้น
    demo.launch(server_name="127.0.0.1")

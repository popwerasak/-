# Local Image Generator

แอพสร้างภาพจากข้อความ รันบนเครื่องเราเองทั้งหมด (Stable Diffusion + Gradio) ไม่เรียก AI ภายนอก

## ติดตั้ง
```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
- มี GPU NVIDIA: ติดตั้ง PyTorch รุ่น CUDA ตามคำแนะนำที่ https://pytorch.org ก่อน แล้วค่อย `pip install -r requirements.txt`

## รัน
```bash
python app.py
```
เปิดเบราว์เซอร์ที่ http://127.0.0.1:7860 ภาพที่สร้างจะถูกบันทึกในโฟลเดอร์ `outputs/`

## หมายเหตุ
- ครั้งแรกต้องมีอินเทอร์เน็ตเพื่อดาวน์โหลดไฟล์โมเดล (SD-Turbo ~2-5 GB) หลังจากนั้นออฟไลน์ได้ (ตั้ง `HF_HUB_OFFLINE=1` เพื่อบังคับ)
- ความเร็วโดยประมาณ (512x512, SD-Turbo): GPU ไม่กี่วินาที / CPU ราว 10-60 วินาทีต่อภาพ
- Prompt ภาษาอังกฤษให้ผลดีที่สุด

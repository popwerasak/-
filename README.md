# Local Object Remover (AMD / ออฟไลน์)

โปรแกรม Desktop ลบวัตถุในภาพ (เช่น นาฬิกาข้อมือ, รองเท้า) แล้วให้ AI **ในเครื่อง** เติมเป็นผิวหนังเปล่าเหมือนไม่เคยใส่
ใช้ Stable Diffusion Inpainting ผ่าน 🤗 Diffusers — ไม่ส่งภาพออกนอกเครื่อง (ติ๊ก "ออฟไลน์เต็มรูปแบบ" หลังดาวน์โหลดโมเดลครั้งแรก)

## วิธีใช้
1. เปิดภาพ (Ctrl+O) → **คลิกซ้ายระบาย** ทับนาฬิกา/รองเท้า (คลิกขวา = ลบรอยระบาย)
2. เลือกงาน (นาฬิกา→ข้อมือ / รองเท้า→เท้า) → กด **ลบ / เติมภาพ**
3. จะได้หลายตัวเลือก คลิกเลือกตัวที่ดีที่สุด (มือ/เท้าเป็นจุดอ่อนของ AI ลองหลายตัว/เปลี่ยน Seed) → Ctrl+S บันทึก

โปรแกรมจะครอป เฉพาะบริเวณรอบ mask + บริบท ส่งให้โมเดลแล้ววางกลับ พิกเซลนอก mask จึงคงเดิม 100%
และปรับสีให้เข้ากับผิวรอบ ๆ อัตโนมัติ

## ติดตั้งสำหรับการ์ด AMD

### Linux (แนะนำ — เร็วและเสถียรที่สุด) : ROCm
```bash
python -m venv .venv && source .venv/bin/activate
# เลือกเวอร์ชัน ROCm ให้ตรงกับที่ pytorch.org แนะนำ
pip install torch torchvision --index-url https://download.pytorch.org/whl/rocm6.2
pip install -r requirements.txt
python main.py
```
การ์ดรุ่นใหม่ที่ ROCm ไม่รองรับอย่างเป็นทางการ (เช่น RDNA2 บางรุ่น) อาจต้องตั้ง `HSA_OVERRIDE_GFX_VERSION` (เช่น `10.3.0` สำหรับ RX 6000, `11.0.0` สำหรับ RX 7000)

### Windows : DirectML
ROCm บน Windows ยังจำกัดรุ่นการ์ด จึงมีทางเลือก DirectML (ใช้ได้กับการ์ด AMD เกือบทุกรุ่น แต่ช้ากว่าและบางครั้งไม่เสถียร):
```bash
pip install torch torch-directml
pip install -r requirements.txt
python main.py
```
โปรแกรมตรวจหาอุปกรณ์เอง ลำดับ: ROCm/CUDA → DirectML → CPU (CPU ใช้ได้แต่ช้ามาก)

## โมเดล
| ตัวเลือก | VRAM โดยประมาณ | หมายเหตุ |
|---|---|---|
| SD 1.5 Inpainting | 4–6 GB | เริ่มจากตัวนี้ |
| SDXL Inpainting | 8 GB+ | คุณภาพดีกว่า |

ใช้โมเดลที่ดาวน์โหลดไว้แล้วได้โดยใส่โฟลเดอร์ในช่อง "โฟลเดอร์โมเดล" (เช่น `huggingface-cli download ... --local-dir models/sd15-inpaint`)
การ fine-tune แนวภาพคนจริง (checkpoint แบบ realistic ที่เป็น inpainting) จะให้ผิวคนดีขึ้น

## ทดสอบ
```bash
pytest   # ทดสอบส่วนประมวลผลภาพ (ไม่ต้องใช้ GPU)
```

## สถานะ
- ส่วนประมวลผลภาพ (`app/imageops.py`) มี unit test ผ่านแล้ว
- ส่วน UI และ pipeline AI **ยังไม่เคยรันกับการ์ด AMD จริง** ผู้พัฒนาทดสอบในสภาพแวดล้อมที่ไม่มี GPU/จอภาพ — หากเจอ error แจ้งข้อความมาเพื่อแก้ต่อได้
- แผนต่อไป: คลิกเลือกวัตถุอัตโนมัติด้วย SAM 2, ControlNet ช่วยโครงเท้า/มือ

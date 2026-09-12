# โปรแกรมแตกไฟล์ ZIP / RAR

โปรแกรม GUI สำหรับแตกไฟล์ `.zip` และ `.rar` ใช้งานได้บน Windows, macOS และ Linux
เขียนด้วย Python + Tkinter (มีมาพร้อม Python อยู่แล้ว ไม่ต้องติดตั้งเพิ่ม)

## คุณสมบัติ

- เลือกไฟล์ได้หลายไฟล์พร้อมกัน (ทั้ง .zip และ .rar)
- เลือกโฟลเดอร์ปลายทางที่จะแตกไฟล์
- สร้างโฟลเดอร์แยกตามชื่อไฟล์อัตโนมัติ (ป้องกันไฟล์ปนกัน)
- รองรับไฟล์ที่มีรหัสผ่าน (จะมีกล่องข้อความให้กรอกรหัสผ่าน)
- แสดงความคืบหน้าและสถานะการแตกไฟล์แบบเรียลไทม์
- ยกเลิกการทำงานระหว่างแตกไฟล์ได้
- ปุ่มเปิดโฟลเดอร์ปลายทางหลังแตกไฟล์เสร็จ

## การติดตั้ง

ต้องมี Python 3.10 ขึ้นไป (ดาวน์โหลดได้ที่ https://www.python.org/downloads/
ตอนติดตั้งบน Windows ให้ติ๊ก "Add python.exe to PATH")

1. ติดตั้งไลบรารีที่จำเป็น:

   ```bash
   pip install -r requirements.txt
   ```

2. **สำหรับการแตกไฟล์ RAR** ต้องมีโปรแกรมช่วยแตกไฟล์ติดตั้งในเครื่องด้วย (ไลบรารี `rarfile`
   ไม่สามารถแตกไฟล์ RAR เองได้ ต้องเรียกใช้โปรแกรมภายนอก) เลือกติดตั้งอย่างใดอย่างหนึ่ง:

   - **Windows**: ติดตั้ง [7-Zip](https://www.7-zip.org/) แล้วเพิ่มโฟลเดอร์ที่ติดตั้ง
     (เช่น `C:\Program Files\7-Zip`) เข้า PATH หรือดาวน์โหลด `UnRAR.exe` จาก
     https://www.rarlab.com/rar_add.htm แล้ววางไว้ในโฟลเดอร์ที่ PATH มองเห็น
   - **macOS**: `brew install unrar` หรือ `brew install unar`
   - **Linux (Debian/Ubuntu)**: `sudo apt install unrar` หรือ `sudo apt install unar`

   ไฟล์ .zip ไม่ต้องติดตั้งอะไรเพิ่ม เพราะ Python มี `zipfile` มาให้ในตัวอยู่แล้ว

## วิธีใช้งาน

```bash
python extractor_gui.py
```

1. กด "เพิ่มไฟล์..." เพื่อเลือกไฟล์ .zip หรือ .rar ที่ต้องการแตก (เลือกได้หลายไฟล์)
2. กด "เลือกโฟลเดอร์..." เพื่อกำหนดปลายทาง
3. กด "เริ่มแตกไฟล์"
4. ถ้าไฟล์มีรหัสผ่าน โปรแกรมจะเด้งกล่องข้อความให้กรอก
5. เมื่อเสร็จแล้ว กด "เปิดโฟลเดอร์ปลายทาง" เพื่อดูไฟล์ที่แตกออกมา

## ตัวติดตั้งสำหรับ Windows (Setup.exe)

โปรเจกต์นี้มี GitHub Actions workflow (`.github/workflows/build-windows-installer.yml`)
ที่ build ตัวติดตั้ง Windows (`ExtractZipRarSetup.exe`) ให้อัตโนมัติ โดยใช้ PyInstaller
รวมโปรแกรมเป็นไฟล์เดียว แล้วใช้ [Inno Setup](https://jrsoftware.org/isinfo.php) ห่อเป็นตัวติดตั้ง
พร้อมสร้างไอคอน Start Menu / Desktop และมีตัวถอนการติดตั้งให้ในตัว

### วิธีดาวน์โหลดตัวติดตั้ง

1. ไปที่แท็บ **Actions** ของ repository บน GitHub
2. เลือก workflow **"Build Windows Installer"**
3. กด **"Run workflow"** (เลือก branch แล้วกดรัน) แล้วรอสักครู่ (build บน Windows runner)
4. เมื่อ build เสร็จ เปิดหน้าผลลัพธ์ของ run แล้วดาวน์โหลดไฟล์แนบชื่อ **ExtractZipRarSetup**
   (เป็น .zip ที่มี `ExtractZipRarSetup.exe` อยู่ข้างใน) แตกไฟล์แล้วรันได้เลย

หรือถ้า push tag ที่ขึ้นต้นด้วย `v` (เช่น `v1.0.0`) workflow จะสร้าง GitHub Release
พร้อมแนบไฟล์ `ExtractZipRarSetup.exe` ให้อัตโนมัติ ดาวน์โหลดจากหน้า Releases ได้ทันที

### วิธี build ตัวติดตั้งเองบนเครื่อง Windows (ถ้าไม่อยากใช้ GitHub Actions)

ต้องมี Windows พร้อม Python และ [Inno Setup 6](https://jrsoftware.org/isdl.php) ติดตั้งไว้:

```powershell
pip install pyinstaller
pip install -r requirements.txt
pyinstaller --onefile --windowed --name "ExtractZipRar" extractor_gui.py
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\setup.iss
```

ไฟล์ตัวติดตั้งที่ได้จะอยู่ที่ `dist_installer\ExtractZipRarSetup.exe`

(ถ้าต้องการแค่ไฟล์ .exe เดี่ยว ไม่ต้องมีตัวติดตั้ง ก็ใช้ไฟล์ที่ได้จากขั้นตอน PyInstaller
ในโฟลเดอร์ `dist\ExtractZipRar.exe` ได้เลยโดยไม่ต้องรันขั้นตอน Inno Setup)

from __future__ import annotations

from PIL import Image
from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, Qt, QThread, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QSlider, QSpinBox,
    QVBoxLayout, QWidget,
)

import re
from pathlib import Path

from .backends import DiffusersBackend, QuickBackend
from .inpaint import PRESETS, Inpainter, Params

DEFAULT_MODEL_DIR = Path(__file__).resolve().parent.parent / "models" / "sd15-inpaint"
COMMAND_WORDS = re.compile(r"\b(remove|delete|erase|get rid|take off|without)\b|ลบ|เอา.{0,12}ออก", re.I)
MODE_QUICK, MODE_AI = "เร็ว (ไม่ใช้ AI) — ของเล็ก/บาง เช่น สร้อย", "AI (ช้ากว่า แต่เติมได้เนียนกว่า)"


def pil_to_qimage(im: Image.Image) -> QImage:
    im = im.convert("RGBA")
    return QImage(im.tobytes("raw", "RGBA"), im.width, im.height, QImage.Format_RGBA8888).copy()


class Canvas(QWidget):
    """แสดงภาพ + ระบายหน้ากาก (mask) ด้วยเมาส์; คลิกขวาลาก = ลบรอยระบาย"""

    def __init__(self):
        super().__init__()
        self.setMinimumSize(640, 480)
        self.setCursor(Qt.CrossCursor)
        self.setMouseTracking(True)
        self._hover: QPoint | None = None
        self.image: Image.Image | None = None
        self.mask = QImage()
        self.overlay = QImage()
        self.brush = 30
        self.show_mask = True
        self._last: QPoint | None = None

    def set_image(self, im: Image.Image):
        self.image = im.convert("RGB")
        self.pix = QPixmap.fromImage(pil_to_qimage(self.image))
        if self.mask.size() != self.pix.size():
            self.clear_mask()
        self.update()

    def clear_mask(self):
        if self.image is None:
            return
        w, h = self.image.size
        self.mask = QImage(w, h, QImage.Format_Grayscale8)
        self.mask.fill(0)
        self.overlay = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
        self.overlay.fill(Qt.transparent)
        self.update()

    def mask_pil(self) -> Image.Image:
        w, h = self.mask.width(), self.mask.height()
        img = self.mask.convertToFormat(QImage.Format_Grayscale8)
        ptr = img.constBits()
        buf = bytes(ptr)[: img.bytesPerLine() * h]
        return Image.frombuffer("L", (w, h), buf, "raw", "L", img.bytesPerLine(), 1)

    def _scale_off(self):
        s = min(self.width() / self.pix.width(), self.height() / self.pix.height())
        ox = (self.width() - self.pix.width() * s) / 2
        oy = (self.height() - self.pix.height() * s) / 2
        return s, ox, oy

    def _to_img(self, pos) -> QPoint:
        s, ox, oy = self._scale_off()
        return QPoint(int((pos.x() - ox) / s), int((pos.y() - oy) / s))

    def _stroke(self, a: QPoint, b: QPoint, erase: bool):
        # mask (ขาว = ลบ) ใช้ส่งให้โปรแกรมประมวลผล / overlay (แดงโปร่ง) ใช้แสดงบนจอ
        for img, color, mode in (
            (self.mask, QColor(0, 0, 0) if erase else QColor(255, 255, 255), QPainter.CompositionMode_Source),
            (self.overlay, QColor(255, 0, 0, 120), QPainter.CompositionMode_Clear if erase else QPainter.CompositionMode_Source),
        ):
            p = QPainter(img)
            p.setCompositionMode(mode)
            p.setPen(QPen(color, self.brush, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawLine(a, b)
            p.end()
        self.update()

    def mousePressEvent(self, e):
        if self.image is None:
            return
        self._last = self._to_img(e.position())
        self._stroke(self._last, self._last, e.button() == Qt.RightButton)

    def mouseMoveEvent(self, e):
        self._hover = e.position().toPoint()
        self.update()
        if self.image is None or self._last is None:
            return
        cur = self._to_img(e.position())
        self._stroke(self._last, cur, bool(e.buttons() & Qt.RightButton))
        self._last = cur

    def mouseReleaseEvent(self, e):
        self._last = None

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(30, 30, 30))
        if self.image is None:
            p.setPen(Qt.gray)
            p.drawText(self.rect(), Qt.AlignCenter, "เปิดภาพ (Ctrl+O) แล้วระบายทับสิ่งที่ต้องการลบ")
            return
        s, ox, oy = self._scale_off()
        target = QRectF(ox, oy, self.pix.width() * s, self.pix.height() * s)
        p.drawPixmap(target, self.pix, QRectF(self.pix.rect()))
        if self.show_mask and not self.overlay.isNull():
            p.drawImage(target, self.overlay)
        if self._hover is not None:  # วงกลมแสดงขนาดแปรง
            r = self.brush * s / 2
            p.setPen(QPen(QColor(255, 255, 255), 1.5))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(self._hover), r, r)


class Worker(QThread):
    status = Signal(str)
    done = Signal(list)
    failed = Signal(str)

    def __init__(self, job):
        super().__init__()
        self.job = job

    def run(self):
        try:
            self.done.emit(self.job(self.status.emit))
        except Exception as ex:  # noqa: BLE001 — แสดงให้ผู้ใช้เห็นทุกข้อผิดพลาด
            self.failed.emit(f"{type(ex).__name__}: {ex}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Local Object Remover (AMD / ออฟไลน์)")
        self.engine: Inpainter | None = None
        self.engine_key = None
        self.results: list[Image.Image] = []
        self.original: Image.Image | None = None
        self.worker: Worker | None = None

        self.canvas = Canvas()
        side = QWidget()
        form = QFormLayout(side)

        self.model_box = QComboBox(); self.model_box.addItems([MODE_QUICK, MODE_AI])
        self.model_dir = QLineEdit(str(DEFAULT_MODEL_DIR) if DEFAULT_MODEL_DIR.exists() else "")
        self.model_dir.setPlaceholderText("โฟลเดอร์โมเดล AI (ดาวน์โหลดด้วย tools/download_model.py)")
        self.offline = QCheckBox("ออฟไลน์เต็มรูปแบบ (ห้ามเชื่อมต่ออินเทอร์เน็ต)"); self.offline.setChecked(True)
        self.res = QComboBox(); self.res.addItems(["384", "448", "512"]); self.res.setCurrentText("448")
        self.preset = QComboBox(); self.preset.addItems(PRESETS)
        self.prompt = QPlainTextEdit(); self.prompt.setMaximumHeight(60)
        self.negative = QPlainTextEdit(); self.negative.setMaximumHeight(60)
        self.prompt.setPlaceholderText("ว่าง = อัตโนมัติ  หรือเขียน 'สิ่งที่อยากให้เห็น' เช่น bare wrist, natural skin (อย่าสั่งว่า remove/ลบ)")
        self.negative.setPlaceholderText("สิ่งที่ไม่อยากให้โผล่ เช่น watch, bracelet")
        self.preset.currentTextChanged.connect(self._apply_preset); self._apply_preset(self.preset.currentText())

        self.brush = QSlider(Qt.Horizontal); self.brush.setRange(4, 200); self.brush.setValue(30)
        self.brush_label = QLabel("ขนาดแปรง: 30 px")
        self.brush.valueChanged.connect(lambda v: (setattr(self.canvas, "brush", v), self.brush_label.setText(f"ขนาดแปรง: {v} px")))
        self.grow = QSpinBox(); self.grow.setRange(0, 60); self.grow.setValue(8)
        self.steps = QSpinBox(); self.steps.setRange(10, 80); self.steps.setValue(20)
        self.variants = QSpinBox(); self.variants.setRange(1, 6); self.variants.setValue(1)
        self.seed = QSpinBox(); self.seed.setRange(-1, 2**31 - 1); self.seed.setValue(-1)
        self.seed.setSpecialValueText("สุ่ม")

        for label, w in [("โหมด", self.model_box), ("โฟลเดอร์โมเดล", self.model_dir), ("", self.offline),
                         ("ความละเอียด AI (เล็ก=เร็ว)", self.res), ("งาน", self.preset), ("Prompt", self.prompt), ("Negative", self.negative),
                         (self.brush_label, self.brush), ("ขยาย mask (px)", self.grow), ("Steps", self.steps),
                         ("จำนวนตัวเลือก", self.variants), ("Seed", self.seed)]:
            form.addRow(label, w)

        self.go = QPushButton("ลบ / เติมภาพ"); self.go.clicked.connect(self.generate)
        clear = QPushButton("ล้างรอยระบาย"); clear.clicked.connect(self.canvas.clear_mask)
        self.thumbs = QHBoxLayout()
        self.status = QLabel("พร้อม")
        form.addRow(self.go); form.addRow(clear)
        form.addRow(QLabel("ผลลัพธ์ (คลิกเพื่อเลือก):")); form.addRow(self.thumbs)
        form.addRow(self.status)
        side.setFixedWidth(340)

        root = QWidget(); lay = QHBoxLayout(root)
        lay.addWidget(self.canvas, 1); lay.addWidget(side)
        self.setCentralWidget(root)

        m = self.menuBar().addMenu("ไฟล์")
        for text, key, fn in [("เปิดภาพ...", "Ctrl+O", self.open_image), ("บันทึกผลลัพธ์...", "Ctrl+S", self.save_image),
                              ("กลับไปภาพต้นฉบับ", "Ctrl+Z", self.revert)]:
            a = QAction(text, self); a.setShortcut(key); a.triggered.connect(fn); m.addAction(a)
        v = self.menuBar().addMenu("มุมมอง")
        a = QAction("แสดง/ซ่อน mask", self, checkable=True, checked=True)
        a.toggled.connect(lambda c: (setattr(self.canvas, "show_mask", c), self.canvas.update()))
        v.addAction(a)

    def _apply_preset(self, name):
        pos, neg = PRESETS[name]
        self.prompt.setPlainText(pos); self.negative.setPlainText(neg)

    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "เปิดภาพ", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if path:
            self.original = Image.open(path).convert("RGB")
            self.canvas.image = None
            self.canvas.set_image(self.original)
            self._clear_thumbs()

    def revert(self):
        if self.original:
            self.canvas.set_image(self.original)

    def save_image(self):
        if self.canvas.image is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "บันทึก", "result.png", "PNG (*.png);;JPEG (*.jpg)")
        if path:
            self.canvas.image.save(path)

    def _clear_thumbs(self):
        while self.thumbs.count():
            w = self.thumbs.takeAt(0).widget()
            if w:
                w.deleteLater()

    def generate(self):
        if self.canvas.image is None or self.worker is not None:
            return
        if COMMAND_WORDS.search(self.prompt.toPlainText()):
            ans = QMessageBox.question(
                self, "Prompt ดูเป็นคำสั่ง",
                "โมเดลไม่เข้าใจคำสั่งอย่าง remove/ลบ — มันจะวาดสิ่งที่เขียนไว้ใน Prompt ออกมาแทน\n"
                "ควรเขียนสิ่งที่อยากให้เห็น เช่น 'bare wrist, natural skin' และใส่สิ่งที่ไม่ต้องการในช่อง Negative\n\n"
                "ใช้ Prompt นี้ต่อไปหรือไม่?")
            if ans != QMessageBox.Yes:
                return
        mode = self.model_box.currentText()
        key = (mode, self.model_dir.text().strip(), self.offline.isChecked())
        if mode == MODE_AI and not key[1]:
            QMessageBox.warning(self, "ยังไม่มีโมเดล", "โหมด AI ต้องมีโฟลเดอร์โมเดล\nรัน: python tools/download_model.py (ใช้เน็ตครั้งเดียว)")
            return
        if self.engine is None or self.engine_key != key:
            backend = QuickBackend() if mode == MODE_QUICK else DiffusersBackend(key[1], key[2])
            self.engine = Inpainter(backend); self.engine_key = key
        params = Params(
            prompt=self.prompt.toPlainText(), negative=self.negative.toPlainText(), mask_grow=self.grow.value(),
            steps=self.steps.value(), variants=self.variants.value(), res=int(self.res.currentText()),
            seed=None if self.seed.value() < 0 else self.seed.value(),
        )
        image, mask, engine = self.canvas.image, self.canvas.mask_pil(), self.engine
        self.go.setEnabled(False)
        self.worker = Worker(lambda cb: engine.run(image, mask, params, cb))
        self.worker.status.connect(self.status.setText)
        self.worker.done.connect(self._on_done)
        self.worker.failed.connect(self._on_failed)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_done(self, results):
        self.results = results
        self._clear_thumbs()
        for r in results:
            b = QPushButton()
            t = r.copy(); t.thumbnail((90, 90))
            b.setIcon(QIcon(QPixmap.fromImage(pil_to_qimage(t)))); b.setIconSize(QSize(*t.size)); b.setFixedSize(96, 96)
            b.clicked.connect(lambda _=False, im=r: self.canvas.set_image(im))
            self.thumbs.addWidget(b)
        if results:
            self.canvas.set_image(results[0]); self.canvas.clear_mask()
        self.status.setText(f"เสร็จแล้ว ({len(results)} ตัวเลือก)")

    def _on_failed(self, msg):
        self.status.setText("ผิดพลาด")
        QMessageBox.critical(self, "ผิดพลาด", msg)

    def _on_finished(self):
        self.worker = None
        self.go.setEnabled(True)


def run():
    import sys
    app = QApplication(sys.argv)
    w = MainWindow(); w.resize(1180, 760); w.show()
    sys.exit(app.exec())

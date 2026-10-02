"""ทดสอบหน้าต่างจริงแบบไม่มีจอ (ข้ามอัตโนมัติถ้าไม่มี PySide6 / ไลบรารีกราฟิก)"""
import os

import numpy as np
import pytest
from PIL import Image, ImageDraw

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtWidgets")
try:
    from PySide6.QtCore import QEventLoop, QPoint, Qt, QTimer
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from app.ui import MainWindow
except ImportError as e:  # เช่น ขาด libEGL
    pytest.skip(str(e), allow_module_level=True)


def _clean():
    x = np.linspace(0, 20, 400, dtype=np.float32)
    base = np.tile(x, (300, 1))
    return np.stack([210 + base, 160 + base, 130 + base], -1).astype(np.uint8)


def test_paint_then_remove_flow():
    app = QApplication.instance() or QApplication([])
    w = MainWindow(); w.resize(1100, 700); w.show()
    img = Image.fromarray(_clean())
    ImageDraw.Draw(img).line([(60, 150), (340, 160)], fill=(40, 40, 40), width=4)
    w.original = img
    w.canvas.set_image(img)

    c = w.canvas
    s, ox, oy = c._scale_off()
    pt = lambda X, Y: QPoint(int(ox + X * s), int(oy + Y * s))
    QTest.mousePress(c, Qt.LeftButton, Qt.NoModifier, pt(60, 150))
    for t in range(1, 11):
        QTest.mouseMove(c, pt(60 + 28 * t, 150 + t))
    QTest.mouseRelease(c, Qt.LeftButton, Qt.NoModifier, pt(340, 160))
    assert c.mask_pil().getbbox() is not None  # ระบายแล้วต้องมี mask
    assert c.grab().toImage().pixelColor(int(ox + 150 * s), int(oy + 153 * s)).red() > 200  # เห็นรอยแดงบนจอ

    w.generate()
    loop = QEventLoop(); w.worker.finished.connect(loop.quit); QTimer.singleShot(60000, loop.quit); loop.exec()
    assert w.status.text().startswith("เสร็จแล้ว"), w.status.text()
    err = np.abs(np.array(c.image).astype(int) - _clean().astype(int))[150:160, 100:300].mean()
    assert err < 12

    w.revert()
    assert np.array_equal(np.array(c.image), np.array(img))

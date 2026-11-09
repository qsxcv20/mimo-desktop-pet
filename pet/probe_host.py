#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""probe_host.py — 探查 MiMo 窗口结构，并实测 SetParent 是否可见。"""
import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QApplication, QWidget

import mimo_host as H

app = QApplication(sys.argv)

print("=== 找 MiMo 主窗口 ===")
hwnd = H.find_mimo_window(timeout=10)
print("hwnd =", hex(hwnd) if hwnd else None)
if not hwnd:
    sys.exit(1)

info = H.describe(hwnd)
for k, v in info.items():
    print("  %-10s %s" % (k, v))
print("  dpi        ", H.dpi_for(hwnd), "scale", H.scale_for(hwnd))

print("\n=== 子窗口树 ===")
for c in H.child_tree(hwnd):
    print("  %-12s %-32s vis=%-5s child=%-5s rect=%s ex=%s"
          % (c["hwnd"], c["class"], c["visible"], c["child"], c["rect"], c["ex"]))


class Marker(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MiMoPetProbe")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(180, 180)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(255, 0, 255, 255))
        p.setPen(QColor(0, 0, 0))
        p.drawEllipse(10, 10, 160, 160)
        p.setPen(QColor(255, 255, 255))
        p.drawText(40, 100, "PET")


m = Marker()
m.show()
app.processEvents()
h = int(m.winId())
print("\nQt winId =", hex(h), " parent(前) =", hex(H.user32.GetParent(h) or 0))

H.make_child(h, hwnd)
cw, ch = H.client_size(hwnd)
print("client size =", cw, ch)
H.move_child(h, cw - 200, ch - 200, 180, 180)
H.raise_child(h)
H.force_redraw(hwnd)
app.processEvents()
time.sleep(0.8)
H.raise_child(h)
H.force_redraw(hwnd)
app.processEvents()
time.sleep(0.8)

print("\nGetParent(后) =", hex(H.user32.GetParent(h) or 0))

# 截取 MiMo 窗口区域
from PySide6.QtGui import QGuiApplication
shot = QGuiApplication.primaryScreen().grabWindow(0)
r = H._rect(hwnd)
img = shot.copy(r[0], r[1], r[2] - r[0], r[3] - r[1])
out = r"D:\桌面宠物\_mimo\host-probe.png"
img.save(out)
print("截图 ->", out, img.width(), "x", img.height())

# 判断洋红色是否出现在截图里（只看标记应该出现的区域）
qim = img.toImage()
mx, my = cw - 200, ch - 200
found = []
for y in range(max(0, my - 10), min(qim.height(), my + 200)):
    for x in range(max(0, mx - 10), min(qim.width(), mx + 200)):
        c = qim.pixelColor(x, y)
        if c.red() > 190 and c.blue() > 190 and c.green() < 90:
            found.append((x, y))
if found:
    xs = [p[0] for p in found]
    ys = [p[1] for p in found]
    print("!! 找到洋红像素 %d 个，范围 x[%d..%d] y[%d..%d]（期望约 x[%d..%d] y[%d..%d]）-> SetParent 可见！"
          % (len(found), min(xs), max(xs), min(ys), max(ys), mx, mx + 180, my, my + 180))
else:
    print("!! 没找到洋红像素 -> 被 Chromium 的 D3D 渲染层盖住了")

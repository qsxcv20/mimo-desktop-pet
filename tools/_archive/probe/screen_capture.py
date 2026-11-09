#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
screen_capture.py — 截取桌面（用于验证桌宠是否真的显示在屏幕上）

    python screen_capture.py out.png            全屏
    python screen_capture.py out.png 1200 800   裁剪右下角区域（桌宠位置）
"""
import sys
import os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QGuiApplication

out = sys.argv[1] if len(sys.argv) > 1 else "screen.png"
app = QApplication(sys.argv)
scr = QGuiApplication.primaryScreen()
pm = scr.grabWindow(0)

if len(sys.argv) > 3:
    w, h = int(sys.argv[2]), int(sys.argv[3])
    x = max(0, pm.width() - w)
    y = max(0, pm.height() - h)
    pm = pm.copy(x, y, w, h)

pm.save(out)
print("saved", out, pm.width(), "x", pm.height(), os.path.getsize(out), "bytes")

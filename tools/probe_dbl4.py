#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe_dbl4.py - 最小复现：Qt 在真实鼠标双击下会不会发 mouseDoubleClickEvent。

如果这个最小用例都收不到 dblclick，说明问题在 Qt/Windows 层
（跟桌宠无关）；如果收得到，说明问题在桌宠的窗口属性上。

分别测两种窗口：
  A) 普通顶层窗口（有标题栏）
  B) 和桌宠一样的：Frameless | Tool | WindowDoesNotAcceptFocus
     + WA_TranslucentBackground + WA_ShowWithoutActivating

用法:
    python tools/probe_dbl4.py
"""

import ctypes
import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QWidget

user32 = ctypes.windll.user32
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

LOG = []


class Probe(QWidget):
    def mousePressEvent(self, e):
        LOG.append(("press", time.time()))
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        LOG.append(("release", time.time()))
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):
        LOG.append(("dblclick", time.time()))
        super().mouseDoubleClickEvent(e)


def real_click(x, y):
    user32.SetCursorPos(int(x), int(y))
    time.sleep(0.06)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.04)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def run_case(app, title, flags, translucent, show_without_activating):
    global LOG
    LOG = []
    w = Probe()
    w.setWindowTitle(title)
    if flags is not None:
        w.setWindowFlags(flags)
    w.setAttribute(Qt.WA_TranslucentBackground, translucent)
    w.setAttribute(Qt.WA_ShowWithoutActivating, show_without_activating)
    w.setFixedSize(220, 220)
    w.move(300, 300)
    w.show()
    app.processEvents()
    hwnd = int(w.winId())

    def do():
        r = w.geometry()
        cx = r.x() + 110
        cy = r.y() + 60
        user32.SetCursorPos(cx, cy)
        time.sleep(0.08)
        for _ in range(2):
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.04)
            user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.09)
        time.sleep(0.5)
        names = [n for n, _ in LOG]
        print("  %-28s 事件 = %s" % (title, names))
        print("     dblclick 收到 = %s"
              % ("是" if "dblclick" in names else "否"))
        w.close()
        w.deleteLater()
        app.processEvents()

    QTimer.singleShot(300, do)
    return w


def main():
    app = QApplication(sys.argv)

    print("== A. 普通顶层窗口 ==")
    w1 = run_case(app, "probe_plain", None, False, False)
    app.processEvents()
    end1 = time.time() + 3
    while time.time() < end1:
        app.processEvents()
        time.sleep(0.02)

    print("== B. 桌宠同款窗口（Frameless|Tool|Translucent|NoActivate）==")
    w2 = run_case(app, "probe_petlike",
                  Qt.FramelessWindowHint | Qt.Tool |
                  Qt.WindowDoesNotAcceptFocus,
                  True, True)
    end2 = time.time() + 3
    while time.time() < end2:
        app.processEvents()
        time.sleep(0.02)

    return 0


if __name__ == "__main__":
    sys.exit(main())

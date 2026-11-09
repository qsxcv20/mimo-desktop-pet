#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""probe_owner.py — 定位 Qt 窗口的 owner 关系是在哪一步被清掉的。"""
import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None
sys.path.insert(0, r"D:\桌面宠物\pet")

from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt

import mimo_host as H

app = QApplication(sys.argv)
host = H.find_mimo_window(timeout=6, include_hidden=True)
print("host =", hex(host) if host else None)
if not host:
    sys.exit(1)


def owner(hwnd):
    return hex(H.user32.GetWindowLongPtrW(hwnd, H.GWLP_HWNDPARENT) or 0)


w = QWidget()
w.setWindowTitle("probe-owner")
w.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowDoesNotAcceptFocus)
w.setAttribute(Qt.WA_TranslucentBackground, True)
w.setAttribute(Qt.WA_ShowWithoutActivating, True)
w.resize(120, 120)

hwnd = int(w.winId())
print("1 winId (未 show)      :", hex(hwnd))
H.user32.SetWindowLongPtrW(hwnd, H.GWLP_HWNDPARENT, host)
print("2 set owner 后          :", owner(hwnd))

w.show()
app.processEvents()
print("3 show 后 winId         :", hex(int(w.winId())), " owner:", owner(hwnd),
      " owner(new):", owner(int(w.winId())))

w.raise_()
app.processEvents()
print("4 raise_ 后 owner       :", owner(int(w.winId())))

w.hide()
app.processEvents()
print("5 hide 后 winId         :", hex(int(w.winId())), " owner:", owner(int(w.winId())))

w.show()
app.processEvents()
print("6 再 show 后 winId      :", hex(int(w.winId())), " owner:", owner(int(w.winId())))

w.setFixedSize(150, 150)
app.processEvents()
print("7 setFixedSize 后 owner :", owner(int(w.winId())))

w2 = QWidget()
w2.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowDoesNotAcceptFocus)
w2.setAttribute(Qt.WA_TranslucentBackground, True)
h2 = int(w2.winId())
H.user32.SetWindowLongPtrW(h2, H.GWLP_HWNDPARENT, host)
w2.show()
app.processEvents()
print("8 新窗口 show 后 owner  :", owner(h2), " winId:", hex(int(w2.winId())))
print("   style=%s ex=%s" % (hex(H._style(h2)), hex(H._exstyle(h2))))
print("   host  style=%s ex=%s" % (hex(H._style(host)), hex(H._exstyle(host))))

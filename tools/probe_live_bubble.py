#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
probe_live_bubble.py — 读取实机桌宠气泡窗口的真实几何与内容模式。

不驱动任何东西，只看现状：窗口 rect、气泡到底是贴纸还是额度模式。

用法：
    python tools/probe_live_bubble.py
"""

import ctypes
import os
import sys
import time
from ctypes import wintypes as wt

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "pet"))

import mimo_host as H                          # noqa: E402
from PySide6.QtGui import QPainter, QPixmap   # noqa: E402
from PySide6.QtCore import Qt, QRect          # noqa: E402


def grab(hwnd):
    """用 PrintWindow 抓一个窗口位图。"""
    u = ctypes.windll.user32
    u.SetProcessDPIAware()
    rect = H._rect(hwnd)
    w, h = rect[2] - rect[0], rect[3] - rect[1]
    hdc = u.GetWindowDC(hwnd)
    mdc = ctypes.windll.gdi32.CreateCompatibleDC(hdc)
    bmp = ctypes.windll.gdi32.CreateCompatibleBitmap(hdc, w, h)
    ctypes.windll.gdi32.SelectObject(mdc, bmp)
    u.PrintWindow(hwnd, mdc, 2)
    class BMI(ctypes.Structure):
        _fields_ = [("biSize", wt.DWORD), ("biWidth", ctypes.c_long),
                    ("biHeight", ctypes.c_long), ("biPlanes", wt.WORD),
                    ("biBitCount", wt.WORD), ("biCompression", wt.DWORD),
                    ("biSizeImage", wt.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                    ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wt.DWORD),
                    ("biClrImportant", wt.DWORD)]
    bi = BMI()
    bi.biSize = ctypes.sizeof(BMI)
    bi.biWidth = w
    bi.biHeight = -h
    bi.biPlanes = 1
    bi.biBitCount = 32
    bi.biCompression = 0
    buf = ctypes.create_string_buffer(w * h * 4)
    ctypes.windll.gdi32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bi), 0)
    from PySide6.QtGui import QImage
    img = QImage(buf, w, h, QImage.Format_ARGB32).copy()
    ctypes.windll.gdi32.DeleteObject(bmp)
    ctypes.windll.gdi32.DeleteDC(mdc)
    u.ReleaseDC(hwnd, hdc)
    return img


def main():
    host = H.find_mimo_window(timeout=3)
    if not host:
        print("找不到 MiMo 窗口")
        return 1
    print("MiMo hwnd=0x%x" % host)

    # 找桌宠气泡窗口
    found = []
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)

    def cb(hwnd, _):
        buf = ctypes.create_unicode_buffer(256)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, 256)
        t = buf.value
        if "MiMo 桌宠气泡" in t or "MiMo 桌宠" in t:
            found.append((hwnd, t))
        return True

    ctypes.windll.user32.EnumWindows(EnumWindowsProc(cb), 0)
    for hwnd, t in found:
        r = H._rect(hwnd)
        print("  0x%x  %-16s rect=%s  size=%dx%d" %
              (hwnd, t, r, r[2] - r[0], r[3] - r[1]))

    out = os.path.join(ROOT, "_mimo", "live-bubble.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    for hwnd, t in found:
        if "气泡" in t:
            img = grab(hwnd)
            img.save(out)
            print("气泡截图 -> %s (%dx%d)" % (out, img.width(), img.height()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
probe_bubble_mode.py — 读实机气泡到底处于哪种模式。

做法：给桌宠发一条「egg sticker」指令，然后在同一进程里
用 PrintWindow 连续抓几帧气泡，看尺寸和内容怎么变。

用法：
    python tools/probe_bubble_mode.py
"""

import ctypes
import json
import os
import sys
import time
from ctypes import wintypes as wt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "pet"))

import mimo_host as H                          # noqa: E402

CMD = r"D:\桌面宠物\pet\pet_cmd.json"
STATUS = r"D:\桌面宠物\pet\pet_status.json"


def find_win(title):
    out = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p,
                                     ctypes.c_void_p)

    def cb(h, _l):
        if H._text(h) == title:
            out.append(int(h))
        return True

    H.user32.EnumWindows(WNDENUMPROC(cb), 0)
    return out[0] if out else None


def grab(hwnd, out):
    u = ctypes.windll.user32
    u.SetProcessDPIAware()
    r = H._rect(hwnd)
    w, h = r[2] - r[0], r[3] - r[1]
    if w <= 0 or h <= 0:
        return None
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
    img.save(out)
    return (w, h)


def main():
    with open(CMD, "w", encoding="utf-8") as f:
        json.dump({"action": "egg", "what": "sticker",
                   "ts": int(time.time() * 1000)}, f, ensure_ascii=False)

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "_mimo")
    os.makedirs(out_dir, exist_ok=True)
    for i in range(6):
        time.sleep(0.35)
        b = find_win("MiMo 桌宠气泡")
        if not b:
            print("  t=%.2fs 没有气泡窗口" % (i * 0.35))
            continue
        vis = H.user32.IsWindowVisible(b)
        r = H._rect(b)
        p = os.path.join(out_dir, "bm-%d.png" % i)
        size = grab(b, p) if vis else None
        print("  t=%.2fs visible=%s rect=%s size=%s -> %s"
              % (i * 0.35, vis, r, size, p))

    try:
        with open(STATUS, "r", encoding="utf-8") as f:
            print("\n状态 egg:", json.dumps(
                (json.load(f) or {}).get("egg"), ensure_ascii=False))
    except Exception as e:
        print(e)
    return 0


if __name__ == "__main__":
    sys.exit(main())

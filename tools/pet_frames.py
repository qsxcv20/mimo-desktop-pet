#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""pet_frames.py — 连拍桌宠窗口若干帧，拼成网格，用来实机检查动画。

用法: python pet_frames.py <count> <interval_ms> <out.png>
"""
import ctypes
import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pet"))

import mimo_host as H  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


def find_pet():
    out = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def cb(h, _l):
        if H._text(h) == "MiMo 桌宠":
            out.append(int(h))
        return True

    H.user32.EnumWindows(WNDENUMPROC(cb), 0)
    return out[0] if out else None


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    gap = int(sys.argv[2]) if len(sys.argv) > 2 else 120
    out = sys.argv[3] if len(sys.argv) > 3 else r"D:\桌面宠物\_mimo\pet-frames.png"

    app = QApplication(sys.argv)
    hwnd = find_pet()
    if not hwnd:
        print("找不到桌宠窗口")
        return 1
    print("桌宠 hwnd=0x%x rect=%s" % (hwnd, H._rect(hwnd)))

    from PIL import Image
    tmpdir = r"D:\桌面宠物\_mimo\_petframes"
    os.makedirs(tmpdir, exist_ok=True)
    paths = []
    for i in range(count):
        shot = QGuiApplication.primaryScreen().grabWindow(0)
        r = H._rect(hwnd)
        if r[2] - r[0] < 10:
            print("桌宠窗口尺寸异常")
            return 2
        p = os.path.join(tmpdir, "f%02d.png" % i)
        shot.copy(r[0], r[1], r[2] - r[0], r[3] - r[1]).save(p)
        paths.append(p)
        time.sleep(gap / 1000.0)

    frames = [Image.open(p).convert("RGB") for p in paths]
    w, h = frames[0].size
    cols = min(4, count)
    rows = (count + cols - 1) // cols
    pad = 4
    sheet = Image.new("RGB", (cols * (w + pad) + pad, rows * (h + pad) + pad),
                      (235, 235, 238))
    for i, f in enumerate(frames):
        r, c = divmod(i, cols)
        sheet.paste(f, (pad + c * (w + pad), pad + r * (h + pad)))
    sheet.save(out)
    print("-> %s  %dx%d  (%d 帧, 间隔 %dms)" % (out, sheet.width, sheet.height,
                                                count, gap))
    return 0


if __name__ == "__main__":
    sys.exit(main())
